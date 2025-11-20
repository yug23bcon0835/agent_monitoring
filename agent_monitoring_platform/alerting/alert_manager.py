from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class Alert:
    alert_id: str
    rule_id: str
    timestamp: datetime
    severity: str
    message: str
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "message": self.message,
            "acknowledged": self.acknowledged,
        }


class AlertManager:
    def __init__(self):
        self.alerts: List[Alert] = []
        self.rules: Dict[str, any] = {}

    def create_alert(self, rule_id: str, severity: str, message: str) -> Alert:
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            rule_id=rule_id,
            timestamp=datetime.utcnow(),
            severity=severity,
            message=message,
        )
        self.alerts.append(alert)
        return alert

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        return next((a for a in self.alerts if a.alert_id == alert_id), None)

    def get_active_alerts(self) -> List[Alert]:
        return [a for a in self.alerts if not a.acknowledged]

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        alert = self.get_alert(alert_id)
        if alert:
            alert.acknowledged = True
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = acknowledged_by
            return True
        return False

    def add_rule(self, rule):
        self.rules[rule.rule_id] = rule

    def get_alerts_by_severity(self, severity: str) -> List[Alert]:
        return [a for a in self.alerts if a.severity == severity]

    def get_alerts_history(self, limit: int = 100) -> List[Alert]:
        return self.alerts[-limit:]

    def clear_acknowledged_alerts(self) -> int:
        count = len([a for a in self.alerts if a.acknowledged])
        self.alerts = [a for a in self.alerts if not a.acknowledged]
        return count
