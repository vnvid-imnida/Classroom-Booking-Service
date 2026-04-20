package database

import (
	"context"
	"fmt"
	"log"
	"time"

	"notification-service/internal/models"

	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
)

var dbPool *pgxpool.Pool

// Init инициализирует подключение к БД
func Init(cfg models.Config) error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	config, err := pgxpool.ParseConfig(cfg.DatabaseURL)
	if err != nil {
		return fmt.Errorf("ошибка парсинга DATABASE_URL: %w", err)
	}

	config.MaxConns = 20
	config.MinConns = 5

	pool, err := pgxpool.NewWithConfig(ctx, config)
	if err != nil {
		return fmt.Errorf("ошибка создания пула БД: %w", err)
	}

	// Проверка подключения
	if err := pool.Ping(ctx); err != nil {
		return fmt.Errorf("ошибка подключения к БД: %w", err)
	}

	dbPool = pool
	log.Println("✅ Пул подключений к БД инициализирован")
	return nil
}

// Close закрывает подключение к БД
func Close() {
	if dbPool != nil {
		dbPool.Close()
		log.Println("✅ Пул подключений закрыт")
	}
}

// Ping проверяет подключение к БД
func Ping(ctx context.Context) error {
	if dbPool == nil {
		return fmt.Errorf("БД не инициализирована")
	}
	return dbPool.Ping(ctx)
}

// GetPool возвращает пул подключений
func GetPool() *pgxpool.Pool {
	return dbPool
}

// UpsertUserByTelegramID находит или создает пользователя по Telegram ID
func UpsertUserByTelegramID(ctx context.Context, telegramID string, username *string) (int, error) {
	if dbPool == nil {
		return 0, fmt.Errorf("БД не инициализирована")
	}

	var existingID int
	err := dbPool.QueryRow(
		ctx,
		`SELECT id FROM users WHERE telegram_id = $1 ORDER BY id LIMIT 1`,
		telegramID,
	).Scan(&existingID)
	if err == nil {
		return existingID, nil
	}

	email := fmt.Sprintf("tg_%s_%d@local.invalid", telegramID, time.Now().UnixNano())
	if username != nil {
		email = fmt.Sprintf("%s_%d@local.invalid", *username, time.Now().UnixNano())
	}

	var userID int
	err = dbPool.QueryRow(
		ctx,
		`INSERT INTO users (email, hash, role, telegram_id)
		 VALUES ($1, $2, $3, $4)
		 RETURNING id`,
		email,
		"external_auth",
		"user",
		telegramID,
	).Scan(&userID)
	if err != nil {
		return 0, fmt.Errorf("ошибка upsert пользователя по telegram_id: %w", err)
	}

	return userID, nil
}

// BookingExists проверяет существование бронирования по ID
func BookingExists(ctx context.Context, bookingID int) (bool, error) {
	if dbPool == nil {
		return false, fmt.Errorf("БД не инициализирована")
	}

	var exists bool
	err := dbPool.QueryRow(ctx, `SELECT EXISTS(SELECT 1 FROM bookings WHERE id = $1)`, bookingID).Scan(&exists)
	if err != nil {
		return false, fmt.Errorf("ошибка проверки существования бронирования: %w", err)
	}

	return exists, nil
}

// GetAllUserIDs возвращает всех пользователей для широковещательных уведомлений
func GetAllUserIDs(ctx context.Context) ([]int, error) {
	if dbPool == nil {
		return nil, fmt.Errorf("БД не инициализирована")
	}

	rows, err := dbPool.Query(ctx, `SELECT id FROM users ORDER BY id`)
	if err != nil {
		return nil, fmt.Errorf("ошибка получения списка пользователей: %w", err)
	}
	defer rows.Close()

	userIDs := make([]int, 0)
	for rows.Next() {
		var userID int
		if scanErr := rows.Scan(&userID); scanErr != nil {
			return nil, fmt.Errorf("ошибка чтения user_id: %w", scanErr)
		}
		userIDs = append(userIDs, userID)
	}

	if rows.Err() != nil {
		return nil, fmt.Errorf("ошибка итерации списка пользователей: %w", rows.Err())
	}

	return userIDs, nil
}

// SaveNotification сохраняет уведомление в БД
func SaveNotification(ctx context.Context, userID int, bookingID *int, message, notificationType, eventID string) (int, error) {
	if dbPool == nil {
		return 0, fmt.Errorf("БД не инициализирована")
	}

	var notificationID int
	now := time.Now()

	query := `
		INSERT INTO notifications 
		(user_id, booking_id, message, notification_type, event_id, status, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		RETURNING id
	`

	err := dbPool.QueryRow(ctx, query,
		userID, bookingID, message, notificationType, eventID, "pending", now, now,
	).Scan(&notificationID)

	if err != nil && bookingID != nil {
		if pgErr, ok := err.(*pgconn.PgError); ok && pgErr.Code == "23503" {
			log.Printf("⚠️ booking_id=%d не прошел FK-проверку, сохраняем уведомление без booking_id", *bookingID)
			err = dbPool.QueryRow(ctx, query,
				userID, nil, message, notificationType, eventID, "pending", now, now,
			).Scan(&notificationID)
		}
	}

	if err != nil {
		return 0, fmt.Errorf("ошибка сохранения уведомления: %w", err)
	}

	log.Printf("📝 Уведомление #%d сохранено в БД для пользователя %d", notificationID, userID)
	return notificationID, nil
}

// UpdateNotificationStatus обновляет статус уведомления
func UpdateNotificationStatus(ctx context.Context, notificationID int, status string, failedReason *string) error {
	if dbPool == nil {
		return fmt.Errorf("БД не инициализирована")
	}

	now := time.Now()
	query := `
		UPDATE notifications 
		SET status = $1, sent_at = $2, failed_reason = $3, updated_at = $4
		WHERE id = $5
	`

	var sentAt *time.Time
	if status == "sent" {
		sentAt = &now
	}

	_, err := dbPool.Exec(ctx, query,
		status, sentAt, failedReason, now, notificationID,
	)

	if err != nil {
		return fmt.Errorf("ошибка обновления статуса: %w", err)
	}

	log.Printf("📊 Статус уведомления #%d: %s", notificationID, status)
	return nil
}

// GetUserByBookingID получает ID пользователя по ID бронирования
func GetUserByBookingID(ctx context.Context, bookingID int) (*int, error) {
	if dbPool == nil {
		return nil, fmt.Errorf("БД не инициализирована")
	}

	var userID *int
	query := `SELECT user_id FROM bookings WHERE id = $1`

	err := dbPool.QueryRow(ctx, query, bookingID).Scan(&userID)
	if err != nil {
		return nil, fmt.Errorf("ошибка получения пользователя по бронированию: %w", err)
	}

	return userID, nil
}

// GetUserEmail получает email пользователя по его ID
func GetUserEmail(ctx context.Context, userID int) (string, error) {
	if dbPool == nil {
		return "", fmt.Errorf("БД не инициализирована")
	}

	var email string
	query := `SELECT email FROM users WHERE id = $1`

	err := dbPool.QueryRow(ctx, query, userID).Scan(&email)
	if err != nil {
		return "", fmt.Errorf("ошибка получения email пользователя: %w", err)
	}

	return email, nil
}

// GetUserTelegramID получает Telegram ID пользователя
func GetUserTelegramID(ctx context.Context, userID int) (string, error) {
	if dbPool == nil {
		return "", fmt.Errorf("БД не инициализирована")
	}

	var telegramID string
	query := `SELECT telegram_id FROM users WHERE id = $1 AND telegram_id IS NOT NULL`

	err := dbPool.QueryRow(ctx, query, userID).Scan(&telegramID)
	if err != nil {
		return "", fmt.Errorf("ошибка получения Telegram ID пользователя: %w", err)
	}

	return telegramID, nil
}

// GetNotification получает уведомление по ID
func GetNotification(ctx context.Context, notificationID int) (*models.Notification, error) {
	if dbPool == nil {
		return nil, fmt.Errorf("БД не инициализирована")
	}

	var notif models.Notification
	query := `
		SELECT id, user_id, booking_id, message, notification_type, event_id, status, 
		       sent_at, failed_reason, created_at, updated_at
		FROM notifications WHERE id = $1
	`

	err := dbPool.QueryRow(ctx, query, notificationID).Scan(
		&notif.ID, &notif.UserID, &notif.BookingID, &notif.Message, &notif.NotificationType,
		&notif.EventID, &notif.Status, &notif.SentAt, &notif.FailedReason, &notif.CreatedAt, &notif.UpdatedAt,
	)

	if err != nil {
		return nil, fmt.Errorf("ошибка получения уведомления: %w", err)
	}

	return &notif, nil
}
