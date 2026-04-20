package models

import (
	"testing"
	"time"
)

func TestNotificationStruct(t *testing.T) {
	now := time.Now()
	userID := 1
	notif := &Notification{
		ID:               1,
		UserID:           userID,
		Message:          "Test message",
		NotificationType: "booking.created",
		Status:           "sent",
		CreatedAt:        now,
	}

	if notif.ID != 1 {
		t.Errorf("Notification.ID = %v, want 1", notif.ID)
	}

	if notif.UserID != userID {
		t.Errorf("Notification.UserID = %v, want %v", notif.UserID, userID)
	}

	if notif.Message != "Test message" {
		t.Errorf("Notification.Message = %v, want 'Test message'", notif.Message)
	}

	if notif.Status != "sent" {
		t.Errorf("Notification.Status = %v, want 'sent'", notif.Status)
	}
}

func TestKafkaMessageStruct(t *testing.T) {
	kafkaMsg := &KafkaMessage{
		EventID:   "event-123",
		EventType: "booking.created",
		Timestamp: time.Now(),
		Data: map[string]interface{}{
			"booking_id": 1,
			"user_id":    2,
			"room_id":    3,
		},
	}

	if kafkaMsg.EventID != "event-123" {
		t.Errorf("KafkaMessage.EventID = %v, want 'event-123'", kafkaMsg.EventID)
	}

	if kafkaMsg.EventType != "booking.created" {
		t.Errorf("KafkaMessage.EventType = %v, want 'booking.created'", kafkaMsg.EventType)
	}

	if kafkaMsg.Data["booking_id"] != 1 {
		t.Errorf("KafkaMessage.Data['booking_id'] = %v, want 1", kafkaMsg.Data["booking_id"])
	}
}

func TestUserStruct(t *testing.T) {
	telegramID := "123456789"
	user := &User{
		ID:         1,
		Email:      "test@example.com",
		Role:       "user",
		TelegramID: &telegramID,
	}

	if user.Email != "test@example.com" {
		t.Errorf("User.Email = %v, want 'test@example.com'", user.Email)
	}

	if user.Role != "user" {
		t.Errorf("User.Role = %v, want 'user'", user.Role)
	}

	if *user.TelegramID != "123456789" {
		t.Errorf("User.TelegramID = %v, want '123456789'", *user.TelegramID)
	}
}

func TestBookingStruct(t *testing.T) {
	start := time.Now()
	end := start.Add(2 * time.Hour)

	booking := &Booking{
		ID:        1,
		UserID:    1,
		RoomID:    1,
		TimeStart: start,
		TimeEnd:   end,
		Status:    "confirmed",
	}

	if booking.ID != 1 {
		t.Errorf("Booking.ID = %v, want 1", booking.ID)
	}

	if booking.Status != "confirmed" {
		t.Errorf("Booking.Status = %v, want 'confirmed'", booking.Status)
	}

	if booking.TimeEnd.Before(booking.TimeStart) {
		t.Errorf("Booking.TimeEnd is before TimeStart")
	}
}
