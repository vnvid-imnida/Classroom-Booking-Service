package config

import (
	"log"

	"notification-service/internal/models"

	"github.com/kelseyhightower/envconfig"
)

var cfg models.Config

// LoadConfig загружает конфигурацию из переменных окружения
func LoadConfig() error {
	if err := envconfig.Process("", &cfg); err != nil {
		return err
	}

	// Установка значений по умолчанию
	if cfg.ServiceName == "" {
		cfg.ServiceName = "notification-service"
	}
	if cfg.ServicePort == 0 {
		cfg.ServicePort = 8084
	}
	if cfg.DatabaseURL == "" {
		cfg.DatabaseURL = "postgresql://notification_user:notification_password@postgres:5432/notification_db"
	}
	if cfg.KafkaBootstrapServers == "" {
		cfg.KafkaBootstrapServers = "kafka:9092"
	}
	if cfg.KafkaGroupID == "" {
		cfg.KafkaGroupID = "notification-service-group"
	}
	if cfg.KafkaTopics == "" {
		cfg.KafkaTopics = "booking.created,booking.updated,booking.cancelled,room.maintenance,room.updated,schedule.synced,schedule.conflict"
	}
	if cfg.KafkaAutoOffsetReset == "" {
		cfg.KafkaAutoOffsetReset = "earliest"
	}
	if cfg.MessageProcessingTimeout == 0 {
		cfg.MessageProcessingTimeout = 30
	}
	if cfg.MaxRetries == 0 {
		cfg.MaxRetries = 3
	}
	if cfg.SMTPPort == 0 {
		cfg.SMTPPort = 587
	}

	log.Printf("✅ Конфигурация загружена: %s:%d", cfg.ServiceName, cfg.ServicePort)
	return nil
}

// GetConfig возвращает загруженную конфигурацию
func GetConfig() models.Config {
	return cfg
}
