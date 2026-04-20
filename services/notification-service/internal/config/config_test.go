package config

import (
	"os"
	"testing"
)

func TestLoadConfig(t *testing.T) {
	// Установка переменных окружения
	os.Setenv("SERVICE_NAME", "test-service")
	os.Setenv("SERVICE_PORT", "9000")
	os.Setenv("TELEGRAM_ENABLED", "false")

	if err := LoadConfig(); err != nil {
		t.Fatalf("LoadConfig() error = %v, want nil", err)
	}

	cfg := GetConfig()

	tests := []struct {
		name     string
		got      interface{}
		expected interface{}
	}{
		{"ServiceName", cfg.ServiceName, "test-service"},
		{"ServicePort", cfg.ServicePort, 9000},
		{"TelegramEnabled", cfg.TelegramEnabled, false},
	}

	for _, tt := range tests {
		if tt.got != tt.expected {
			t.Errorf("%s = %v, want %v", tt.name, tt.got, tt.expected)
		}
	}

	// Очистка переменных окружения
	os.Unsetenv("SERVICE_NAME")
	os.Unsetenv("SERVICE_PORT")
	os.Unsetenv("TELEGRAM_ENABLED")
}

func TestGetConfig(t *testing.T) {
	// LoadConfig должен быть вызван перед этим
	os.Setenv("SERVICE_NAME", "test-service-2")

	if err := LoadConfig(); err != nil {
		t.Fatalf("LoadConfig() error = %v, want nil", err)
	}

	cfg := GetConfig()

	if cfg.ServiceName != "test-service-2" {
		t.Errorf("GetConfig().ServiceName = %v, want test-service-2", cfg.ServiceName)
	}

	os.Unsetenv("SERVICE_NAME")
}

func TestConfigDefaults(t *testing.T) {
	// Очистка всех переменных окружения
	os.Clearenv()

	if err := LoadConfig(); err != nil {
		t.Fatalf("LoadConfig() error = %v, want nil", err)
	}

	cfg := GetConfig()

	tests := []struct {
		name     string
		got      interface{}
		expected interface{}
	}{
		{"DefaultServiceName", cfg.ServiceName, "notification-service"},
		{"DefaultServicePort", cfg.ServicePort, 8084},
		{"DefaultKafkaBootstrapServers", cfg.KafkaBootstrapServers, "kafka:9092"},
	}

	for _, tt := range tests {
		if tt.got != tt.expected {
			t.Errorf("%s = %v, want %v", tt.name, tt.got, tt.expected)
		}
	}
}
