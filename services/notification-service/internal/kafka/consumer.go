package kafka

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"sync"
	"sync/atomic"
	"time"

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
	log.Printf("📢 Подписка на топики: %v", topics)

	// Используем первый топик для Consumer Group, остальное управляется вручную
	mainTopic := "booking.created" // Default
	if len(topics) > 0 {
		mainTopic = topics[0]
	}

	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers:        []string{cfg.KafkaBootstrapServers},
		GroupID:        cfg.KafkaGroupID,
		Topic:          mainTopic,
		StartOffset:    -1, // Latest offset
		CommitInterval: time.Second,
		MaxBytes:       10e6,
		Logger:         log.Default(),
		ErrorLogger:    log.Default(),
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
	log.Println("✅ Kafka консьюмер запущен")
}

// Stop останавливает консьюмер
func (kcm *ConsumerManager) Stop() {
	log.Println("⛔ Остановка Kafka консьюмера...")
	kcm.isRunning.Store(false)
	kcm.cancel()
	if err := kcm.reader.Close(); err != nil {
		log.Printf("❌ Ошибка закрытия reader: %v", err)
	}
	kcm.wg.Wait()
	log.Println("✅ Kafka консьюмер остановлен")
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

		// Чтение сообщения с таймаутом
		ctx, cancel := context.WithTimeout(kcm.ctx, 30*time.Second)
		msg, err := kcm.reader.FetchMessage(ctx)
		cancel()

		if err != nil {
			if err == context.Canceled {
				return
			}
			log.Printf("❌ Ошибка при чтении из Kafka: %v", err)
			time.Sleep(2 * time.Second)
			continue
		}

		// Обработка сообщения
		go kcm.handleMessage(msg)
	}
}

// handleMessage обрабатывает одно сообщение
func (kcm *ConsumerManager) handleMessage(msg kafka.Message) {
	ctx, cancel := context.WithTimeout(kcm.ctx, time.Duration(kcm.cfg.MessageProcessingTimeout)*time.Second)
	defer cancel()

	var kafkaMsg models.KafkaMessage
	if err := json.Unmarshal(msg.Value, &kafkaMsg); err != nil {
		log.Printf("❌ Ошибка десериализации сообщения: %v", err)
		kcm.failedCount.Add(1)
		return
	}

	log.Printf("📬 Получено сообщение: EventType=%s, EventID=%s", kafkaMsg.EventType, kafkaMsg.EventID)

	// Обработка сообщения
	if err := kcm.processEvent(ctx, kafkaMsg); err != nil {
		log.Printf("❌ Ошибка обработки события: %v", err)
		kcm.failedCount.Add(1)
		return
	}

	// Коммит смещения
	if err := kcm.reader.CommitMessages(ctx, msg); err != nil {
		log.Printf("⚠️ Ошибка коммита смещения: %v", err)
	}

	kcm.processedCount.Add(1)
	log.Printf("✅ Сообщение обработано (всего: %d)", kcm.processedCount.Load())
}

// processEvent обрабатывает событие в зависимости от типа
func (kcm *ConsumerManager) processEvent(ctx context.Context, kafkaMsg models.KafkaMessage) error {
	eventType := kafkaMsg.EventType
	data := kafkaMsg.Data

	var userID int
	var bookingID *int
	var message string

	switch {
	case isBookingEvent(eventType):
		// Обработка события бронирования
		if bid, ok := data["booking_id"].(float64); ok {
			id := int(bid)
			bookingID = &id
			// TODO: получить пользователя по бронированию
			userID = int(data["user_id"].(float64))
		} else {
			return fmt.Errorf("booking_id не найден в сообщении")
		}
		message = notification.FormatBookingMessage(eventType, data)

	case isRoomEvent(eventType):
		// Обработка события комнаты - отправляем администратору
		userID = 1 // TODO: получить из конфига admin_user_id
		message = notification.FormatRoomMessage(eventType, data)

	case isScheduleEvent(eventType):
		// Обработка события расписания - отправляем администратору
		userID = 1 // TODO: получить из конфига admin_user_id
		message = notification.FormatScheduleMessage(eventType, data)

	default:
		return fmt.Errorf("неизвестный тип события: %s", eventType)
	}

	// Отправка уведомления
	return kcm.notificationMgr.SendNotification(ctx, userID, message, eventType, bookingID)
}

// Helper функции для определения типа события
func isBookingEvent(eventType string) bool {
	return strings.HasPrefix(eventType, "booking.")
}

func isRoomEvent(eventType string) bool {
	return strings.HasPrefix(eventType, "room.")
}

func isScheduleEvent(eventType string) bool {
	return strings.HasPrefix(eventType, "schedule.")
}

// parseTopics парсит строку топиков в срез
func parseTopics(topicsStr string) []string {
	if topicsStr == "" {
		return []string{
			"booking.created",
			"booking.updated",
			"booking.cancelled",
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
