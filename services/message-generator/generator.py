"""
Fake Message Generator для тестирования Notification Service
Генерирует тестовые сообщения в Kafka топики по схеме Messages.md
"""

import json
import logging
import time
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, Any
from kafka import KafkaProducer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

VALID_USER_IDS = [1333800382]
VALID_BOOKING_IDS = [1, 2, 3, 4, 5, 6]
VALID_ROOM_IDS = [1, 2, 3, 4, 5, 6]


class FakeMessageGenerator:
    """Генератор фейковых сообщений"""

    def __init__(self, bootstrap_servers: str = "kafka:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.producer = KafkaProducer(
            bootstrap_servers=[bootstrap_servers],
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )
        logger.info(f"✅ Generator инициализирован (Kafka: {bootstrap_servers})")
        self.counter = 0

    def _pick_academic_slot(self) -> tuple[datetime, datetime]:
        """Возвращает реалистичный слот свободного окна между парами."""
        # Типовые свободные окна между парами в течение учебного дня.
        slot_hours = [(10, 40), (12, 50), (15, 0), (17, 10)]
        days_ahead = random.randint(1, 14)
        base_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
        hour, minute = random.choice(slot_hours)
        start_time = base_day.replace(hour=hour, minute=minute)
        end_time = start_time + timedelta(minutes=random.choice([80, 90]))
        return start_time, end_time

    def generate_booking_created(self, booking_id: int = None, room_id: int = None, user_id: int = None) -> Dict[str, Any]:
        """Генерирует событие создания бронирования"""
        booking_id = booking_id or random.choice(VALID_BOOKING_IDS)
        room_id = room_id or random.choice(VALID_ROOM_IDS)
        user_id = user_id or random.choice(VALID_USER_IDS)
        telegram_id = user_id
        
        now = datetime.utcnow()
        start_time, end_time = self._pick_academic_slot()
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "booking.created",
            "timestamp": now.isoformat() + "Z",
            "version": 1,
            "data": {
                "booking_id": booking_id,
                "user_id": user_id,
                "telegram_id": telegram_id,
                "room_id": room_id,
                "time_start": start_time.isoformat() + "Z",
                "time_end": end_time.isoformat() + "Z",
                "status": random.choice(["pending", "confirmed"]),
                "source": "schedule_gap_recommendation"
            },
            "metadata": {
                "source_service": "booking-api",
                "correlation_id": f"req-{uuid.uuid4()}"
            }
        }
        return event

    def generate_user_created(self, user_id: int = None) -> Dict[str, Any]:
        """Генерирует событие создания пользователя"""
        user_id = user_id or random.choice(VALID_USER_IDS)
        now = datetime.utcnow()

        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "user.created",
            "timestamp": now.isoformat() + "Z",
            "version": 1,
            "data": {
                "user_id": user_id,
                "telegram_id": user_id,
                "username": f"user_{user_id}"
            },
            "metadata": {
                "source_service": "auth-service",
                "correlation_id": f"req-{uuid.uuid4()}"
            }
        }
        return event

    def generate_booking_updated(self, booking_id: int = None) -> Dict[str, Any]:
        """Генерирует событие обновления бронирования"""
        booking_id = booking_id or random.choice(VALID_BOOKING_IDS)
        user_id = random.choice(VALID_USER_IDS)
        now = datetime.utcnow()
        old_start, old_end = self._pick_academic_slot()
        new_start = old_start + timedelta(minutes=random.choice([0, 30, 90]))
        new_end = old_end + timedelta(minutes=random.choice([0, 30, 90]))
        new_status = random.choice(["confirmed", "rescheduled"])
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "booking.updated",
            "timestamp": now.isoformat() + "Z",
            "version": 1,
            "data": {
                "booking_id": booking_id,
                "user_id": user_id,
                "telegram_id": user_id,
                "changed_fields": {
                    "time_start": {
                        "old": old_start.isoformat() + "Z",
                        "new": new_start.isoformat() + "Z"
                    },
                    "time_end": {
                        "old": old_end.isoformat() + "Z",
                        "new": new_end.isoformat() + "Z"
                    },
                    "status": {
                        "old": "confirmed",
                        "new": new_status
                    }
                },
                "current_full_state": {
                    "booking_id": booking_id,
                    "user_id": user_id,
                    "room_id": random.choice(VALID_ROOM_IDS),
                    "time_start": new_start.isoformat() + "Z",
                    "time_end": new_end.isoformat() + "Z",
                    "status": new_status
                }
            }
        }
        return event

    def generate_booking_cancelled(self, booking_id: int = None, user_id: int = None, room_id: int = None) -> Dict[str, Any]:
        """Генерирует событие отмены бронирования"""
        booking_id = booking_id or random.choice(VALID_BOOKING_IDS)
        user_id = user_id or random.choice(VALID_USER_IDS)
        room_id = room_id or random.choice(VALID_ROOM_IDS)
        now = datetime.utcnow()
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "booking.cancelled",
            "timestamp": now.isoformat() + "Z",
            "version": 1,
            "data": {
                "booking_id": booking_id,
                "user_id": user_id,
                "telegram_id": user_id,
                "room_id": room_id,
                "cancelled_by": random.choice(["schedule-service", "system"]),
                "cancelled_at": now.isoformat() + "Z",
                "reason": random.choice([
                    "class_schedule_changed",
                    "lesson_overlap_detected",
                    "schedule_sync_conflict",
                ])
            },
            "metadata": {
                "requires_audit": True
            }
        }
        return event

    def generate_room_maintenance(self, room_id: int = None) -> Dict[str, Any]:
        """Legacy: генерация событий обслуживания комнаты (в основном сценарии не используется)."""
        room_id = room_id or random.choice(VALID_ROOM_IDS)
        now = datetime.utcnow()
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "room.maintenance",
            "timestamp": now.isoformat() + "Z",
            "version": 1,
            "data": {
                "user_id": random.choice(VALID_USER_IDS),
                "telegram_id": random.choice(VALID_USER_IDS),
                "room_id": room_id,
                "maintenance_status": "blocked",
                "start_time": now.isoformat() + "Z",
                "expected_end_time": (now + timedelta(hours=random.randint(1, 48))).isoformat() + "Z",
                "reason": random.choice(["hvac_repair", "plumbing", "electrical", "cleaning"]),
                "affected_future_bookings": [random.choice(VALID_BOOKING_IDS) for _ in range(random.randint(0, 3))]
            }
        }
        return event

    def generate_room_updated(self, room_id: int = None) -> Dict[str, Any]:
        """Legacy: генерация событий обновления комнаты (в основном сценарии не используется)."""
        room_id = room_id or random.choice(VALID_ROOM_IDS)
        now = datetime.utcnow()
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "room.updated",
            "timestamp": now.isoformat() + "Z",
            "version": 1,
            "data": {
                "user_id": random.choice(VALID_USER_IDS),
                "telegram_id": random.choice(VALID_USER_IDS),
                "room_id": room_id,
                "changes": {
                    "capacity": {
                        "old": random.randint(20, 100),
                        "new": random.randint(20, 100)
                    },
                    "features": {
                        "old": ["projector", "whiteboard"],
                        "new": ["projector", "whiteboard", "air_conditioning"]
                    }
                }
            }
        }
        return event

    def generate_schedule_synced(self) -> Dict[str, Any]:
        """Генерирует событие синхронизации расписания"""
        now = datetime.utcnow()
        date_from = now.date()
        date_to = (now + timedelta(days=14)).date()
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "schedule.synced",
            "timestamp": now.isoformat() + "Z",
            "version": 1,
            "data": {
                "source": "ruz",
                "sync_batch_id": f"sync_{now.strftime('%Y%m%d_%H%M%S')}",
                "rooms_affected": [random.choice(VALID_ROOM_IDS) for _ in range(random.randint(2, 6))],
                "date_range": {
                    "from": date_from.isoformat(),
                    "to": date_to.isoformat()
                },
                "changes_summary": {
                    "lessons_inserted": random.randint(20, 80),
                    "lessons_updated": random.randint(5, 30),
                    "lessons_deleted": random.randint(0, 8),
                    "booking_conflicts_detected": random.randint(0, 6)
                }
            }
        }
        return event

    def generate_schedule_conflict(self) -> Dict[str, Any]:
        """Генерирует событие конфликта расписания"""
        room_id = random.choice(VALID_ROOM_IDS)
        now = datetime.utcnow()
        booking_start, booking_end = self._pick_academic_slot()
        lesson_start = booking_start + timedelta(minutes=random.choice([0, 15, 30]))
        lesson_end = lesson_start + timedelta(minutes=90)
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "schedule.conflict",
            "timestamp": now.isoformat() + "Z",
            "version": 1,
            "data": {
                "conflict_type": random.choice(["class_overlap", "lesson_time_changed"]),
                "room_id": room_id,
                "involved_booking_ids": [random.choice(VALID_BOOKING_IDS)],
                "booking_time_slot": {
                    "start": booking_start.isoformat() + "Z",
                    "end": booking_end.isoformat() + "Z"
                },
                "lesson_time_slot": {
                    "start": lesson_start.isoformat() + "Z",
                    "end": lesson_end.isoformat() + "Z"
                },
                "resolution": "auto_cancelled"
            }
        }
        return event

    def send_event(self, topic: str, event: Dict[str, Any]):
        """Отправляет событие в Kafka"""
        try:
            self.producer.send(topic, event)
            self.producer.flush()
            self.counter += 1
            logger.info(f"✅ [{self.counter}] {event['event_type']} → {topic}")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки: {e}")

    def close(self):
        """Закрывает producer"""
        if self.producer:
            self.producer.close()
            logger.info("✅ Producer закрыт")


def run_continuous_generation():
    """Бесконечная генерация ~ 5 сообщений в минуту (по одному каждые 12 сек)"""
    gen = FakeMessageGenerator()
    interval_seconds = 12

    # Топики и методы генерации
    event_generators = [
        ("booking.created", gen.generate_booking_created),
        ("booking.updated", gen.generate_booking_updated),
        ("booking.cancelled", gen.generate_booking_cancelled),
        ("user.created", gen.generate_user_created),
        ("schedule.synced", gen.generate_schedule_synced),
        ("schedule.conflict", gen.generate_schedule_conflict),
    ]

    try:
        logger.info("🚀 Начало непрерывной генерации событий (~5 сообщений/мин)")
        message_count = 0
        next_send_ts = time.monotonic() + interval_seconds

        while True:
            now_ts = time.monotonic()
            if now_ts < next_send_ts:
                time.sleep(next_send_ts - now_ts)

            # Выбираем случайное событие
            topic, generator_func = random.choice(event_generators)
            event = generator_func()
            
            gen.send_event(topic, event)
            message_count += 1
            
            # Периодический вывод статистики
            if message_count % 10 == 0:
                logger.info(f"📊 Всего отправлено сообщений: {message_count}")
            
            # Строго 5 сообщений в минуту.
            next_send_ts += interval_seconds

    except KeyboardInterrupt:
        logger.info("⛔ Получен сигнал прерывания")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}", exc_info=True)
    finally:
        gen.close()


if __name__ == "__main__":
    run_continuous_generation()
