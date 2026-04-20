package models

import "time"

// Config структура для конфигурации сервиса
type Config struct {
	// Сервис
	ServiceName string
	ServicePort int
	Debug       bool

	// База данных
	DatabaseURL string

	// Kafka
	KafkaBootstrapServers string
	KafkaGroupID          string
	KafkaTopics           string
	KafkaAutoOffsetReset  string

	// Telegram
	TelegramBotToken string
	TelegramChatID   string
	TelegramEnabled  bool

	// Email
	SMTPHost      string
	SMTPPort      int
	SMTPUser      string
	SMTPPassword  string
	SMTPFromEmail string
	EmailEnabled  bool

	// Обработка сообщений
	MessageProcessingTimeout int
	MaxRetries               int
}

// Notification структура для уведомления в БД
type Notification struct {
	ID               int
	UserID           int
	BookingID        *int
	Message          string
	NotificationType string
	EventID          string
	Status           string
	CreatedAt        time.Time
	UpdatedAt        time.Time
	SentAt           *time.Time
	FailedReason     *string
}

// KafkaMessage структура для сообщения из Kafka
type KafkaMessage struct {
	EventID   string                 `json:"event_id"`
	EventType string                 `json:"event_type"`
	Timestamp time.Time              `json:"timestamp"`
	Data      map[string]interface{} `json:"data"`
}

// User структура для пользователя
type User struct {
	ID         int
	Email      string
	Hash       string
	Role       string
	TelegramID *string
	CreatedAt  time.Time
	UpdatedAt  time.Time
}

// Booking структура для бронирования
type Booking struct {
	ID          int
	UserID      int
	RoomID      int
	TimeStart   time.Time
	TimeEnd     time.Time
	Status      string
	Description string
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

// Room структура для комнаты
type Room struct {
	ID        int
	Name      string
	Capacity  int
	Features  []string
	Status    string
	CreatedAt time.Time
	UpdatedAt time.Time
}
