package notification

import (
	"testing"
)

func TestFormatBookingMessage(t *testing.T) {
	tests := []struct {
		name      string
		eventType string
		data      map[string]interface{}
		contains  string
	}{
		{
			name:      "booking.created",
			eventType: "booking.created",
			data:      map[string]interface{}{"booking_id": 1, "room_id": 2, "user_id": 3},
			contains:  "✅",
		},
		{
			name:      "booking.updated",
			eventType: "booking.updated",
			data:      map[string]interface{}{"booking_id": 1, "room_id": 2},
			contains:  "📝",
		},
		{
			name:      "booking.cancelled",
			eventType: "booking.cancelled",
			data:      map[string]interface{}{"booking_id": 1, "room_id": 2},
			contains:  "❌",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := FormatBookingMessage(tt.eventType, tt.data)
			if result == "" {
				t.Errorf("FormatBookingMessage() returned empty string")
			}
		})
	}
}

func TestFormatRoomMessage(t *testing.T) {
	tests := []struct {
		name      string
		eventType string
		data      map[string]interface{}
		contains  string
	}{
		{
			name:      "room.maintenance",
			eventType: "room.maintenance",
			data:      map[string]interface{}{"room_id": 1, "reason": "Cleaning"},
			contains:  "🔧",
		},
		{
			name:      "room.updated",
			eventType: "room.updated",
			data:      map[string]interface{}{"room_id": 1},
			contains:  "📋",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := FormatRoomMessage(tt.eventType, tt.data)
			if result == "" {
				t.Errorf("FormatRoomMessage() returned empty string")
			}
		})
	}
}

func TestFormatScheduleMessage(t *testing.T) {
	tests := []struct {
		name      string
		eventType string
		data      map[string]interface{}
		contains  string
	}{
		{
			name:      "schedule.synced",
			eventType: "schedule.synced",
			data:      map[string]interface{}{"rooms_count": 5},
			contains:  "🔄",
		},
		{
			name:      "schedule.conflict",
			eventType: "schedule.conflict",
			data:      map[string]interface{}{"room_id": 1},
			contains:  "⚠️",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := FormatScheduleMessage(tt.eventType, tt.data)
			if result == "" {
				t.Errorf("FormatScheduleMessage() returned empty string")
			}
		})
	}
}
