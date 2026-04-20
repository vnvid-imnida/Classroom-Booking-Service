package database

import (
	"context"
	"errors"
	"fmt"
	"log"
	"time"

	"notification-service/internal/models"

	"github.com/jackc/pgx/v5"
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

// UpsertUserByTelegramID находит или создает пользователя по Telegram ID.
func UpsertUserByTelegramID(ctx context.Context, telegramID int64, username *string) error {
	if dbPool == nil {
		return fmt.Errorf("БД не инициализирована")
	}

	var existingID string
	err := dbPool.QueryRow(
		ctx,
		`SELECT id::text FROM users WHERE telegram_id = $1 ORDER BY created_at LIMIT 1`,
		telegramID,
	).Scan(&existingID)
	if err == nil {
		if username != nil {
			_, _ = dbPool.Exec(
				ctx,
				`UPDATE users
				 SET telegram_username = $1, is_active = true
				 WHERE telegram_id = $2`,
				*username,
				telegramID,
			)
		}
		return nil
	}
	if !errors.Is(err, pgx.ErrNoRows) {
		return fmt.Errorf("ошибка поиска пользователя по telegram_id: %w", err)
	}

	telegramUsername := fmt.Sprintf("tg_%d", telegramID)
	if username != nil && *username != "" {
		telegramUsername = *username
	}

	_, err = dbPool.Exec(
		ctx,
		`INSERT INTO users (telegram_id, telegram_username, full_name, role, is_active)
		 VALUES ($1, $2, $3, $4, true)
		 ON CONFLICT (telegram_id) DO UPDATE
		 SET telegram_username = EXCLUDED.telegram_username,
		     is_active = true`,
		telegramID,
		telegramUsername,
		telegramUsername,
		"TEACHER",
	)
	if err != nil {
		return fmt.Errorf("ошибка upsert пользователя по telegram_id: %w", err)
	}

	return nil
}

// BookingExists проверяет существование бронирования по ID
func BookingExists(ctx context.Context, bookingID int) (bool, error) {
	if dbPool == nil {
		return false, fmt.Errorf("БД не инициализирована")
	}

	// В текущей схеме booking.id = UUID, а из событий приходит целочисленный external booking_id.
	return true, nil
}

// GetAllUserIDs возвращает всех пользователей для широковещательных уведомлений
func GetAllUserIDs(ctx context.Context) ([]int64, error) {
	if dbPool == nil {
		return nil, fmt.Errorf("БД не инициализирована")
	}

	rows, err := dbPool.Query(ctx, `SELECT telegram_id FROM users WHERE is_active = true ORDER BY telegram_id`)
	if err != nil {
		return nil, fmt.Errorf("ошибка получения списка пользователей: %w", err)
	}
	defer rows.Close()

	userIDs := make([]int64, 0)
	for rows.Next() {
		var userID int64
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
func SaveNotification(ctx context.Context, userID int64, bookingID *int, message, notificationType, eventID string) (int, error) {
	if dbPool == nil {
		return 0, fmt.Errorf("БД не инициализирована")
	}

	var notificationID int
	now := time.Now()

	query := `
		INSERT INTO notifications 
		(telegram_id, booking_external_id, message, notification_type, event_id, status, created_at, updated_at)
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
func GetUserByBookingID(ctx context.Context, bookingID int) (*int64, error) {
	if dbPool == nil {
		return nil, fmt.Errorf("БД не инициализирована")
	}

	var userID int64
	query := `
		SELECT u.telegram_id
		FROM bookings b
		JOIN users u ON u.id = b.organizer_id
		WHERE b.external_event_id = $1
		LIMIT 1
	`

	err := dbPool.QueryRow(ctx, query, fmt.Sprintf("%d", bookingID)).Scan(&userID)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("ошибка получения пользователя по бронированию: %w", err)
	}

	return &userID, nil
}

// GetUserTelegramID получает Telegram ID пользователя
func GetUserTelegramID(ctx context.Context, userID int64) (string, error) {
	if dbPool == nil {
		return "", fmt.Errorf("БД не инициализирована")
	}

	var telegramID int64
	query := `SELECT telegram_id FROM users WHERE telegram_id = $1 AND is_active = true`

	err := dbPool.QueryRow(ctx, query, userID).Scan(&telegramID)
	if err != nil {
		return "", fmt.Errorf("ошибка получения Telegram ID пользователя: %w", err)
	}

	return fmt.Sprintf("%d", telegramID), nil
}

// GetNotification получает уведомление по ID
func GetNotification(ctx context.Context, notificationID int) (*models.Notification, error) {
	if dbPool == nil {
		return nil, fmt.Errorf("БД не инициализирована")
	}

	var notif models.Notification
	query := `
		SELECT id, telegram_id, booking_external_id, message, notification_type, event_id, status, 
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
