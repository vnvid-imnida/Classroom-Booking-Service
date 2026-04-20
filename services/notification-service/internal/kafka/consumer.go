package kafka

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"notification-service/internal/database"
	"notification-service/internal/models"
	"notification-service/internal/notification"

	"github.com/segmentio/kafka-go"
)

// ConsumerManager управляет Kafka консьюмером
type ConsumerManager struct {
	reader          *kafka.Reader
	cfg             models.Config
	notificationMgr *notification.Manager
	isRunning       atomic.Bool
	wg              sync.WaitGroup
	ctx             context.Context
	cancel          context.CancelFunc
	processedCount  atomic.Int64
	failedCount     atomic.Int64
}

// NewConsumerManager создает новый менеджер консьюмера
func NewConsumerManager(cfg models.Config, notificationMgr *notification.Manager) *ConsumerManager {
	ctx, cancel := context.WithCancel(context.Background())

	topics := parseTopics(cfg.KafkaTopics)
	log.Printf("Подписка на топики: %v", topics)

	startOffset := kafka.FirstOffset
	if strings.EqualFold(cfg.KafkaAutoOffsetReset, "latest") {
		startOffset = kafka.LastOffset
	}

	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers:        []string{cfg.KafkaBootstrapServers},
		GroupID:        cfg.KafkaGroupID,
		GroupTopics:    topics,
		StartOffset:    startOffset,
		CommitInterval: time.Second,
		MaxBytes:       10e6,
	})

	return &ConsumerManager{
		reader:          reader,
		cfg:             cfg,
		notificationMgr: notificationMgr,
		ctx:             ctx,
		cancel:          cancel,
	}
}

// Start запускает консьюмер
func (kcm *ConsumerManager) Start() {
	kcm.isRunning.Store(true)
	kcm.wg.Add(1)
	go kcm.consume()
	log.Println("Kafka консьюмер запущен")
}

// Stop останавливает консьюмер
func (kcm *ConsumerManager) Stop() {
	log.Println("Остановка Kafka консьюмера...")
	kcm.isRunning.Store(false)
	kcm.cancel()
	if err := kcm.reader.Close(); err != nil {
		log.Printf("Ошибка закрытия reader: %v", err)
	}
	kcm.wg.Wait()
	log.Println("Kafka консьюмер остановлен")
}

// consume обрабатывает сообщения из Kafka
func (kcm *ConsumerManager) consume() {
	defer kcm.wg.Done()

	for {
		select {
		case <-kcm.ctx.Done():
			return
		default:
		}

		ctx, cancel := context.WithTimeout(kcm.ctx, 30*time.Second)
		msg, err := kcm.reader.FetchMessage(ctx)
		cancel()

		if err != nil {
			if err == context.Canceled {
				return
			}
			if isNoMessageError(err) {
				continue
			}
			log.Printf("Ошибка при чтении из Kafka: %v", err)
			time.Sleep(2 * time.Second)
			continue
		}

		go kcm.handleMessage(msg)
	}
}

// handleMessage обрабатывает одно сообщение
func (kcm *ConsumerManager) handleMessage(msg kafka.Message) {
	ctx, cancel := context.WithTimeout(kcm.ctx, time.Duration(kcm.cfg.MessageProcessingTimeout)*time.Second)
	defer cancel()

	var kafkaMsg models.KafkaMessage
	if err := json.Unmarshal(msg.Value, &kafkaMsg); err != nil {
		log.Printf("Ошибка десериализации сообщения: %v", err)
		kcm.failedCount.Add(1)
		return
	}

	log.Printf("Получено сообщение: EventType=%s, EventID=%s", kafkaMsg.EventType, kafkaMsg.EventID)

	if err := kcm.processEvent(ctx, kafkaMsg); err != nil {
		log.Printf("Ошибка обработки события: %v", err)
		kcm.failedCount.Add(1)
		return
	}

	if err := kcm.reader.CommitMessages(ctx, msg); err != nil {
		log.Printf("Ошибка коммита смещения: %v", err)
	}

	kcm.processedCount.Add(1)
	log.Printf("Сообщение обработано (всего: %d)", kcm.processedCount.Load())
}

// processEvent обрабатывает событие в зависимости от типа
func (kcm *ConsumerManager) processEvent(ctx context.Context, kafkaMsg models.KafkaMessage) error {
	eventType := kafkaMsg.EventType
	data := kafkaMsg.Data
	var message string

	if isUserEvent(eventType) {
		telegramID, ok := getTelegramID(data)
		if !ok {
			return fmt.Errorf("user event без telegram_id/user_id: %s", eventType)
		}

		username := getOptionalStringField(data, "username")
		if username == nil {
			username = getOptionalStringField(data, "telegram_username")
		}

		userID, err := database.UpsertUserByTelegramID(ctx, telegramID, username)
		if err != nil {
			return fmt.Errorf("ошибка upsert пользователя: %w", err)
		}

		log.Printf("Пользователь обработан: id=%d, event=%s", userID, eventType)
		return nil
	}

	switch {
	case isBookingEvent(eventType):
		bookingIDValue, ok := getIntField(data, "booking_id")
		if !ok {
			return fmt.Errorf("booking_id не найден в сообщении")
		}

		userID, ok := getIntField(data, "user_id")
		if !ok {
			return fmt.Errorf("user_id не найден в сообщении для события %s", eventType)
		}

		username := getOptionalStringField(data, "username")
		if username == nil {
			username = getOptionalStringField(data, "telegram_username")
		}

		localUserID, err := database.UpsertUserByTelegramID(ctx, fmt.Sprintf("%d", userID), username)
		if err != nil {
			return fmt.Errorf("ошибка upsert пользователя из booking события: %w", err)
		}

		bookingID := &bookingIDValue
		message = notification.FormatBookingMessage(eventType, data)
		return kcm.notificationMgr.SendNotification(ctx, localUserID, message, eventType, kafkaMsg.EventID, bookingID)

	case isRoomEvent(eventType):
		if telegramID, ok := getTelegramID(data); ok {
			username := getOptionalStringField(data, "username")
			if username == nil {
				username = getOptionalStringField(data, "telegram_username")
			}
			if _, err := database.UpsertUserByTelegramID(ctx, telegramID, username); err != nil {
				log.Printf("Не удалось upsert пользователя по telegram_id=%s: %v", telegramID, err)
			}
		}
		message = notification.FormatRoomMessage(eventType, data)
		return kcm.notificationMgr.SendBroadcastNotification(ctx, message, eventType, kafkaMsg.EventID)

	case isScheduleEvent(eventType):
		message = notification.FormatScheduleMessage(eventType, data)
		return kcm.notificationMgr.SendBroadcastNotification(ctx, message, eventType, kafkaMsg.EventID)

	default:
		return fmt.Errorf("неизвестный тип события: %s", eventType)
	}
}

func isNoMessageError(err error) bool {
	if errors.Is(err, context.DeadlineExceeded) {
		return true
	}

	msg := err.Error()
	if strings.Contains(msg, "Request Timed Out") {
		return true
	}

	return false
}

func isBookingEvent(eventType string) bool {
	return strings.HasPrefix(eventType, "booking.")
}

func isRoomEvent(eventType string) bool {
	return strings.HasPrefix(eventType, "room.")
}

func isScheduleEvent(eventType string) bool {
	return strings.HasPrefix(eventType, "schedule.")
}

func isUserEvent(eventType string) bool {
	return strings.HasPrefix(eventType, "user.")
}

// parseTopics парсит строку топиков в срез
func parseTopics(topicsStr string) []string {
	if topicsStr == "" {
		return []string{
			"booking.created",
			"booking.updated",
			"booking.cancelled",
			"user.created",
			"room.maintenance",
			"room.updated",
			"schedule.synced",
			"schedule.conflict",
		}
	}

	var topics []string
	for _, topic := range strings.Split(topicsStr, ",") {
		if t := strings.TrimSpace(topic); t != "" {
			topics = append(topics, t)
		}
	}
	return topics
}

func getIntField(data map[string]interface{}, key string) (int, bool) {
	v, ok := data[key]
	if !ok {
		return 0, false
	}

	switch value := v.(type) {
	case float64:
		return int(value), true
	case int:
		return value, true
	default:
		return 0, false
	}
}

func getTelegramID(data map[string]interface{}) (string, bool) {
	if value, ok := data["telegram_id"]; ok {
		switch v := value.(type) {
		case string:
			if strings.TrimSpace(v) != "" {
				return v, true
			}
		case float64:
			return fmt.Sprintf("%.0f", v), true
		case int:
			return fmt.Sprintf("%d", v), true
		}
	}

	if value, ok := data["user_id"]; ok {
		switch v := value.(type) {
		case float64:
			return fmt.Sprintf("%.0f", v), true
		case int:
			return fmt.Sprintf("%d", v), true
		}
	}

	return "", false
}

func getOptionalStringField(data map[string]interface{}, key string) *string {
	v, ok := data[key]
	if !ok {
		return nil
	}

	s, ok := v.(string)
	if !ok || strings.TrimSpace(s) == "" {
		return nil
	}

	return &s
}

// GetMetrics возвращает метрики обработки
func (kcm *ConsumerManager) GetMetrics() map[string]interface{} {
	return map[string]interface{}{
		"processed_messages": kcm.processedCount.Load(),
		"failed_messages":    kcm.failedCount.Load(),
		"status":             kcm.isRunning.Load(),
	}
}

// IsRunning возвращает статус работы консьюмера
func (kcm *ConsumerManager) IsRunning() bool {
	return kcm.isRunning.Load()
}
