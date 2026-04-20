package notification

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"net/url"

	"notification-service/internal/database"
	"notification-service/internal/models"
)

// Manager управляет отправкой уведомлений
type Manager struct {
	cfg models.Config
}

// NewManager создает новый менеджер уведомлений
func NewManager(cfg models.Config) *Manager {
	return &Manager{cfg: cfg}
}

// SendNotification отправляет уведомление через все доступные каналы
func (nm *Manager) SendNotification(ctx context.Context, userID int64, message, notificationType, eventID string, bookingID *int) error {
	// Сохранение в БД
	notificationID, err := database.SaveNotification(ctx, userID, bookingID, message, notificationType, eventID)
	if err != nil {
		log.Printf("❌ Ошибка сохранения уведомления: %v", err)
		return err
	}

	// Отправка через Telegram
	if nm.cfg.TelegramEnabled && nm.cfg.TelegramBotToken != "" {
		if err := nm.sendTelegram(ctx, userID, message); err != nil {
			log.Printf("⚠️ Ошибка отправки Telegram: %v", err)
			failReason := "telegram_error: " + err.Error()
			_ = database.UpdateNotificationStatus(ctx, notificationID, "failed", &failReason)
		} else {
			log.Printf("✅ Сообщение отправлено в Telegram пользователю %d", userID)
		}
	}

	// Обновление статуса на успешно отправлено
	_ = database.UpdateNotificationStatus(ctx, notificationID, "sent", nil)

	return nil
}

// SendBroadcastNotification отправляет уведомление всем пользователям
func (nm *Manager) SendBroadcastNotification(ctx context.Context, message, notificationType, eventID string) error {
	userIDs, err := database.GetAllUserIDs(ctx)
	if err != nil {
		return fmt.Errorf("ошибка получения пользователей для рассылки: %w", err)
	}

	if len(userIDs) == 0 {
		log.Printf("⚠️ Широковещательное уведомление %s пропущено: нет пользователей", notificationType)
		return nil
	}

	var firstErr error
	for _, userID := range userIDs {
		if sendErr := nm.SendNotification(ctx, userID, message, notificationType, eventID, nil); sendErr != nil {
			log.Printf("⚠️ Ошибка широковещательной отправки пользователю %d: %v", userID, sendErr)
			if firstErr == nil {
				firstErr = sendErr
			}
		}
	}

	return firstErr
}

// sendTelegram отправляет сообщение в Telegram
func (nm *Manager) sendTelegram(ctx context.Context, userID int64, message string) error {
	if nm.cfg.TelegramBotToken == "" {
		return fmt.Errorf("Telegram token не установлен")
	}

	telegramID := fmt.Sprintf("%d", userID)
	if userID <= 0 {
		log.Printf("⚠️ Некорректный Telegram ID пользователя %d", userID)
		if nm.cfg.TelegramChatID == "" {
			return fmt.Errorf("Telegram chat ID не найден для пользователя")
		}
		telegramID = nm.cfg.TelegramChatID
	}

	// Отправка через Telegram Bot API
	apiURL := fmt.Sprintf(
		"https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s",
		nm.cfg.TelegramBotToken,
		telegramID,
		url.QueryEscape(message),
	)

	req, err := http.NewRequestWithContext(ctx, "GET", apiURL, nil)
	if err != nil {
		return fmt.Errorf("ошибка создания запроса: %w", err)
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("ошибка отправки: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("Telegram вернул статус %d", resp.StatusCode)
	}

	return nil
}

// FormatBookingMessage форматирует сообщение о бронировании
func FormatBookingMessage(eventType string, event map[string]interface{}) string {
	bookingID := event["booking_id"]
	roomID := event["room_id"]
	userID := event["user_id"]

	switch eventType {
	case "booking.created":
		return fmt.Sprintf(
			"✅ Бронирование #%v создано\nКомната: #%v\nПользователь: #%v",
			bookingID, roomID, userID,
		)
	case "booking.updated":
		return fmt.Sprintf(
			"📝 Бронирование #%v обновлено\nКомната: #%v",
			bookingID, roomID,
		)
	case "booking.cancelled":
		return fmt.Sprintf(
			"❌ Бронирование #%v отменено\nКомната: #%v",
			bookingID, roomID,
		)
	default:
		return fmt.Sprintf("Уведомление о бронировании: %s", eventType)
	}
}

// FormatRoomMessage форматирует сообщение о комнате
func FormatRoomMessage(eventType string, event map[string]interface{}) string {
	roomID := event["room_id"]

	switch eventType {
	case "room.maintenance":
		return fmt.Sprintf(
			"🔧 Комната #%v требует обслуживания\nПричина: %v",
			roomID, event["reason"],
		)
	case "room.updated":
		return fmt.Sprintf(
			"📋 Информация о комнате #%v обновлена",
			roomID,
		)
	default:
		return fmt.Sprintf("Уведомление о комнате: %s", eventType)
	}
}

// FormatScheduleMessage форматирует сообщение о расписании
func FormatScheduleMessage(eventType string, event map[string]interface{}) string {
	switch eventType {
	case "schedule.synced":
		return fmt.Sprintf(
			"🔄 Расписание синхронизировано\nКоличество комнат: %v",
			event["rooms_count"],
		)
	case "schedule.conflict":
		return fmt.Sprintf(
			"⚠️ Обнаружен конфликт расписания\nКомната: #%v",
			event["room_id"],
		)
	default:
		return fmt.Sprintf("Уведомление о расписании: %s", eventType)
	}
}
