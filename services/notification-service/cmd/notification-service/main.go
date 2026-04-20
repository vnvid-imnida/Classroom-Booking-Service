package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"notification-service/internal/config"
	"notification-service/internal/database"
	"notification-service/internal/kafka"
	"notification-service/internal/models"
	"notification-service/internal/notification"
)

var (
	kafkaConsumer   *kafka.ConsumerManager
	notificationMgr *notification.Manager
	cfg             models.Config
)

func main() {
	// Загрузка конфигурации
	if err := config.LoadConfig(); err != nil {
		log.Fatalf("❌ Ошибка загрузки конфигурации: %v", err)
	}
	cfg = config.GetConfig()

	// Инициализация БД
	if err := database.Init(cfg); err != nil {
		log.Fatalf("❌ Ошибка инициализации БД: %v", err)
	}
	defer database.Close()

	// Инициализация менеджера уведомлений
	notificationMgr = notification.NewManager(cfg)
	log.Println("✅ Менеджер уведомлений инициализирован")

	// Инициализация Kafka консьюмера
	kafkaConsumer = kafka.NewConsumerManager(cfg, notificationMgr)
	kafkaConsumer.Start()
	defer kafkaConsumer.Stop()

	// Запуск HTTP сервера
	setupHTTPServer()

	// Graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	log.Printf("🚀 Notification Service запущен на порту %d", cfg.ServicePort)
	<-sigChan
	log.Println("⛔ Получен сигнал завершения")
}

// setupHTTPServer устанавливает HTTP сервер с маршрутами
func setupHTTPServer() {
	mux := http.NewServeMux()

	// Маршруты
	mux.HandleFunc("/health", handleHealth)
	mux.HandleFunc("/metrics", handleMetrics)
	mux.HandleFunc("/status", handleStatus)

	// Запуск сервера в горутине
	go func() {
		addr := fmt.Sprintf(":%d", cfg.ServicePort)
		log.Printf("📡 HTTP сервер слушает на %s", addr)
		if err := http.ListenAndServe(addr, mux); err != nil && err != http.ErrServerClosed {
			log.Fatalf("❌ Ошибка HTTP сервера: %v", err)
		}
	}()
}

// handleHealth обработчик для /health
func handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	response := map[string]interface{}{
		"status":  "healthy",
		"service": cfg.ServiceName,
		"time":    time.Now().Unix(),
	}

	json.NewEncoder(w).Encode(response)
}

// handleMetrics обработчик для /metrics
func handleMetrics(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	if kafkaConsumer == nil {
		w.WriteHeader(http.StatusServiceUnavailable)
		json.NewEncoder(w).Encode(map[string]string{"error": "Service not ready"})
		return
	}

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(kafkaConsumer.GetMetrics())
}

// handleStatus обработчик для /status
func handleStatus(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	// Проверка БД
	var dbStatus string
	err := database.Ping(ctx)
	if err != nil {
		dbStatus = "error: " + err.Error()
	} else {
		dbStatus = "connected"
	}

	response := map[string]interface{}{
		"service": cfg.ServiceName,
		"port":    cfg.ServicePort,
		"kafka": map[string]interface{}{
			"brokers": cfg.KafkaBootstrapServers,
			"group":   cfg.KafkaGroupID,
			"running": kafkaConsumer != nil && kafkaConsumer.IsRunning(),
		},
		"database": map[string]interface{}{
			"status": dbStatus,
			"url":    cfg.DatabaseURL[:40] + "...",
		},
		"notifications": map[string]interface{}{
			"telegram": cfg.TelegramEnabled,
			"email":    cfg.EmailEnabled,
		},
		"timestamp": time.Now().Unix(),
	}

	json.NewEncoder(w).Encode(response)
}
