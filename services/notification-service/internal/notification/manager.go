package notification

import (
	"context"
	"fmt"
	"log"
	"net"
	"net/http"
	"net/smtp"
	"strings"

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
func (nm *Manager) SendNotification(ctx context.Context, userID int, message, notificationType string, bookingID *int) error {
	// Сохранение в БД
	notificationID, err := database.SaveNotification(ctx, userID, bookingID, message, notificationType, "")
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

	// Отправка через Email
	if nm.cfg.EmailEnabled && nm.cfg.SMTPHost != "" {
		if err := nm.sendEmail(ctx, userID, message, notificationType); err != nil {
			log.Printf("⚠️ Ошибка отправки Email: %v", err)
			failReason := "email_error: " + err.Error()
			_ = database.UpdateNotificationStatus(ctx, notificationID, "failed", &failReason)
		} else {
			log.Printf("✅ Email отправлен пользователю %d", userID)
		}
	}

	// Обновление статуса на успешно отправлено
	_ = database.UpdateNotificationStatus(ctx, notificationID, "sent", nil)

	return nil
}

// sendTelegram отправляет сообщение в Telegram
func (nm *Manager) sendTelegram(ctx context.Context, userID int, message string) error {
	if nm.cfg.TelegramBotToken == "" {
		return fmt.Errorf("Telegram token не установлен")
	}

	// Получение Telegram ID пользователя
	telegramID, err := database.GetUserTelegramID(ctx, userID)
	if err != nil {
		log.Printf("⚠️ Не найден Telegram ID для пользователя %d", userID)
		// Используем глобальный chat_id если не найден ID пользователя
		if nm.cfg.TelegramChatID == "" {
			return fmt.Errorf("Telegram chat ID не найден для пользователя")
		}
		telegramID = nm.cfg.TelegramChatID
	}

	// Отправка через Telegram Bot API
	url := fmt.Sprintf(
		"https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s",
		nm.cfg.TelegramBotToken,
		telegramID,
		strings.ReplaceAll(message, " ", "%20"),
	)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
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

// sendEmail отправляет Email уведомление через SMTP
func (nm *Manager) sendEmail(ctx context.Context, userID int, message, notificationType string) error {
	// Получение email пользователя
	userEmail, err := database.GetUserEmail(ctx, userID)
	if err != nil {
		log.Printf("⚠️ Не найден email для пользователя %d", userID)
		return err
	}

	if nm.cfg.SMTPHost == "" || nm.cfg.SMTPFromEmail == "" {
		return fmt.Errorf("SMTP конфигурация не полная")
	}

	// Формирование SMTP адреса
	addr := net.JoinHostPort(nm.cfg.SMTPHost, fmt.Sprintf("%d", nm.cfg.SMTPPort))

	// Формирование письма
	subject := fmt.Sprintf("Уведомление: %s", notificationType)
	body := fmt.Sprintf("<p>%s</p>", message)

	headers := fmt.Sprintf(
		"From: %s\r\nTo: %s\r\nSubject: %s\r\nMIME-Version: 1.0\r\nContent-Type: text/html; charset=\"UTF-8\"\r\n\r\n",
		nm.cfg.SMTPFromEmail,
		userEmail,
		subject,
	)

	fullMessage := headers + body

	// Подключение к SMTP серверу
	client, err := smtp.Dial(addr)
	if err != nil {
		return fmt.Errorf("ошибка подключения к SMTP: %w", err)
	}
	defer client.Close()

	// Аутентификация
	if nm.cfg.SMTPUser != "" && nm.cfg.SMTPPassword != "" {
		auth := smtp.PlainAuth("", nm.cfg.SMTPUser, nm.cfg.SMTPPassword, nm.cfg.SMTPHost)
		if err := client.Auth(auth); err != nil {
			return fmt.Errorf("ошибка аутентификации SMTP: %w", err)
		}
	}

	// Отправка письма
	if err := client.Mail(nm.cfg.SMTPFromEmail); err != nil {
		return fmt.Errorf("ошибка установки адреса отправителя: %w", err)
	}

	if err := client.Rcpt(userEmail); err != nil {
		return fmt.Errorf("ошибка установки адреса получателя: %w", err)
	}

	writer, err := client.Data()
	if err != nil {
		return fmt.Errorf("ошибка получения writer: %w", err)
	}

	if _, err := fmt.Fprint(writer, fullMessage); err != nil {
		return fmt.Errorf("ошибка отправки данных письма: %w", err)
	}

	if err := writer.Close(); err != nil {
		return fmt.Errorf("ошибка закрытия writer: %w", err)
	}

	if err := client.Quit(); err != nil {
		return fmt.Errorf("ошибка отключения от SMTP: %w", err)
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
