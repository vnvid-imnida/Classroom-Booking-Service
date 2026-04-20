package models

import "time"

type Config struct {
	// Сервис
	ServiceName string `envconfig:"SERVICE_NAME"`
	ServicePort int    `envconfig:"SERVICE_PORT"`
	Debug       bool   `envconfig:"DEBUG"`

	// База данных
	DatabaseURL string `envconfig:"DATABASE_URL"`

	// Kafka
	KafkaBootstrapServers string `envconfig:"KAFKA_BOOTSTRAP_SERVERS"`
	KafkaGroupID          string `envconfig:"KAFKA_GROUP_ID"`
	KafkaTopics           string `envconfig:"KAFKA_TOPICS"`
	KafkaAutoOffsetReset  string `envconfig:"KAFKA_AUTO_OFFSET_RESET"`

	// Redis (новое поле)
	RedisURL string `envconfig:"REDIS_URL"`

	// Telegram
	TelegramBotToken string `envconfig:"TELEGRAM_BOT_TOKEN"`
	TelegramChatID   string `envconfig:"TELEGRAM_CHAT_ID"`
	TelegramEnabled  bool   `envconfig:"TELEGRAM_ENABLED"`

	// Обработка сообщений
	MessageProcessingTimeout int `envconfig:"MESSAGE_PROCESSING_TIMEOUT"`
	MaxRetries               int `envconfig:"MAX_RETRIES"`
}

// Notification структура для уведомления в БД
type Notification struct {
	ID               int
	UserID           int64
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
