package kafka

import (
	"strings"
	"testing"
)

func TestIsBookingEvent(t *testing.T) {
	tests := []struct {
		eventType string
		expected  bool
	}{
		{"booking.created", true},
		{"booking.updated", true},
		{"booking.cancelled", true},
		{"room.maintenance", false},
		{"schedule.synced", false},
		{"unknown.event", false},
	}

	for _, tt := range tests {
		result := isBookingEvent(tt.eventType)
		if result != tt.expected {
			t.Errorf("isBookingEvent(%s) = %v, want %v", tt.eventType, result, tt.expected)
		}
	}
}

func TestIsRoomEvent(t *testing.T) {
	tests := []struct {
		eventType string
		expected  bool
	}{
		{"room.maintenance", true},
		{"room.updated", true},
		{"booking.created", false},
		{"schedule.synced", false},
	}

	for _, tt := range tests {
		result := isRoomEvent(tt.eventType)
		if result != tt.expected {
			t.Errorf("isRoomEvent(%s) = %v, want %v", tt.eventType, result, tt.expected)
		}
	}
}

func TestIsScheduleEvent(t *testing.T) {
	tests := []struct {
		eventType string
		expected  bool
	}{
		{"schedule.synced", true},
		{"schedule.conflict", true},
		{"booking.created", false},
		{"room.maintenance", false},
	}

	for _, tt := range tests {
		result := isScheduleEvent(tt.eventType)
		if result != tt.expected {
			t.Errorf("isScheduleEvent(%s) = %v, want %v", tt.eventType, result, tt.expected)
		}
	}
}

func TestParseTopics(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected int
	}{
		{
			name:     "Empty string returns default topics",
			input:    "",
			expected: 7,
		},
		{
			name:     "Single topic",
			input:    "booking.created",
			expected: 1,
		},
		{
			name:     "Multiple topics",
			input:    "booking.created,booking.updated,room.maintenance",
			expected: 3,
		},
		{
			name:     "Topics with spaces",
			input:    "booking.created , booking.updated , room.maintenance",
			expected: 3,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := parseTopics(tt.input)
			if len(result) != tt.expected {
				t.Errorf("parseTopics() returned %d topics, want %d", len(result), tt.expected)
			}

			// Check for empty strings
			for _, topic := range result {
				if strings.TrimSpace(topic) == "" {
					t.Errorf("parseTopics() returned empty topic")
				}
			}
		})
	}
}
