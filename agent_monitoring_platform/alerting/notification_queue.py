from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import logging


@dataclass
class Notification:
    notification_id: str
    alert_id: str
    severity: str
    message: str
    timestamp: datetime
    delivered: bool = False
    retry_count: int = 0


class NotificationQueue:
    def __init__(self, max_retries: int = 3, dedup_window_seconds: int = 300):
        self.queue: List[Notification] = []
        self.max_retries = max_retries
        self.dedup_window = timedelta(seconds=dedup_window_seconds)
        self.sent_alerts: Dict[str, datetime] = {}
        self.logger = logging.getLogger(__name__)

    def enqueue(self, notification: Notification) -> bool:
        # Check for deduplication
        if self._is_duplicate(notification.alert_id):
            self.logger.debug(f"Skipping duplicate alert: {notification.alert_id}")
            return False

        self.queue.append(notification)
        self.sent_alerts[notification.alert_id] = datetime.utcnow()
        return True

    def dequeue(self) -> Optional[Notification]:
        if self.queue:
            return self.queue.pop(0)
        return None

    def get_pending_notifications(self) -> List[Notification]:
        return [n for n in self.queue if not n.delivered]

    def mark_delivered(self, notification_id: str) -> bool:
        for n in self.queue:
            if n.notification_id == notification_id:
                n.delivered = True
                n.retry_count = 0
                return True
        return False

    def mark_failed(self, notification_id: str) -> bool:
        for n in self.queue:
            if n.notification_id == notification_id:
                n.retry_count += 1
                if n.retry_count >= self.max_retries:
                    n.delivered = True
                    self.logger.warning(f"Max retries reached for notification: {notification_id}")
                return True
        return False

    def _is_duplicate(self, alert_id: str) -> bool:
        if alert_id not in self.sent_alerts:
            return False

        time_since_sent = datetime.utcnow() - self.sent_alerts[alert_id]
        return time_since_sent < self.dedup_window

    def clear_delivered(self) -> int:
        original_length = len(self.queue)
        self.queue = [n for n in self.queue if not n.delivered]
        return original_length - len(self.queue)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "queue_size": len(self.queue),
            "pending": len(self.get_pending_notifications()),
            "total_sent": len(self.sent_alerts),
        }
