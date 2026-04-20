"""
Fake Message Generator для тестирования Notification Service
Генерирует тестовые сообщения в Kafka топики
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any

from kafka import KafkaProducer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FakeMessageGenerator:
    """Генератор фейковых сообщений"""

    def __init__(self, bootstrap_servers: str = "kafka:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.producer = KafkaProducer(
            bootstrap_servers=[bootstrap_servers],
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )
        logger.info(f"✅ Generator инициализирован (Kafka: {bootstrap_servers})")

    def generate_booking_created(self, booking_id: int = 1, room_id: int = 101, user_id: int = 1) -> Dict[str, Any]:
        """Генерирует событие создания бронирования"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "booking.created",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "booking_id": booking_id,
                "room_id": room_id,
                "user_id": user_id,
                "start_date": "2024-04-25",
                "end_date": "2024-04-27",
                "status": "confirmed"
            }
        }
        return event

    def generate_booking_updated(self, booking_id: int = 1, room_id: int = 101) -> Dict[str, Any]:
        """Генерирует событие обновления бронирования"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "booking.updated",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "booking_id": booking_id,
                "room_id": room_id,
                "status": "confirmed"
            }
        }
        return event

    def generate_booking_cancelled(self, booking_id: int = 1, room_id: int = 101, reason: str = "User cancelled") -> Dict[str, Any]:
        """Генерирует событие отмены бронирования"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "booking.cancelled",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "booking_id": booking_id,
                "room_id": room_id,
                "reason": reason
            }
        }
        return event

    def generate_room_maintenance(self, room_id: int = 101, reason: str = "Plumbing issue") -> Dict[str, Any]:
        """Генерирует событие обслуживания комнаты"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "room.maintenance",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "room_id": room_id,
                "reason": reason,
                "status": "in_progress"
            }
        }
        return event

    def generate_room_updated(self, room_id: int = 101) -> Dict[str, Any]:
        """Генерирует событие обновления информации комнаты"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "room.updated",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "room_id": room_id,
                "price": 100.0,
                "capacity": 2,
                "amenities": ["WiFi", "TV", "AC"]
            }
        }
        return event

    def generate_schedule_synced(self, rooms_count: int = 50) -> Dict[str, Any]:
        """Генерирует событие синхронизации расписания"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "schedule.synced",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "rooms_count": rooms_count,
                "total_bookings": 150,
                "sync_status": "success"
            }
        }
        return event

    def generate_schedule_conflict(self, room_id: int = 101) -> Dict[str, Any]:
        """Генерирует событие конфликта расписания"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "schedule.conflict",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "room_id": room_id,
                "conflict_bookings": [1, 2],
                "conflict_reason": "Overlapping dates"
            }
        }
        return event

    def send_event(self, topic: str, event: Dict[str, Any]):
        """Отправляет событие в Kafka"""
        try:
            self.producer.send(topic, event)
            self.producer.flush()
            logger.info(f"✅ Событие отправлено в {topic}: {event['event_type']} ({event['event_id']})")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки: {e}")

    def close(self):
        """Закрывает producer"""
        if self.producer:
            self.producer.close()
            logger.info("✅ Producer закрыт")


def run_test_scenarios():
    """Запускает сценарии тестирования"""
    gen = FakeMessageGenerator()

    try:
        # Сценарий 1: Создание бронирования
        logger.info("\n📋 Сценарий 1: Создание бронирования")
        event = gen.generate_booking_created(booking_id=1, room_id=101, user_id=1)
        gen.send_event("booking.created", event)
        time.sleep(2)

        # Сценарий 2: Обновление бронирования
        logger.info("\n📋 Сценарий 2: Обновление бронирования")
        event = gen.generate_booking_updated(booking_id=1, room_id=101)
        gen.send_event("booking.updated", event)
        time.sleep(2)

        # Сценарий 3: Обслуживание комнаты
        logger.info("\n📋 Сценарий 3: Обслуживание комнаты")
        event = gen.generate_room_maintenance(room_id=101, reason="Cleaning required")
        gen.send_event("room.maintenance", event)
        time.sleep(2)

        # Сценарий 4: Отмена бронирования
        logger.info("\n📋 Сценарий 4: Отмена бронирования")
        event = gen.generate_booking_cancelled(booking_id=1, room_id=101)
        gen.send_event("booking.cancelled", event)
        time.sleep(2)

        # Сценарий 5: Синхронизация расписания
        logger.info("\n📋 Сценарий 5: Синхронизация расписания")
        event = gen.generate_schedule_synced(rooms_count=50)
        gen.send_event("schedule.synced", event)
        time.sleep(2)

        # Сценарий 6: Конфликт расписания
        logger.info("\n📋 Сценарий 6: Конфликт расписания")
        event = gen.generate_schedule_conflict(room_id=102)
        gen.send_event("schedule.conflict", event)

        logger.info("\n✅ Все тестовые сценарии завершены!")

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}", exc_info=True)
    finally:
        gen.close()


if __name__ == "__main__":
    run_test_scenarios()
