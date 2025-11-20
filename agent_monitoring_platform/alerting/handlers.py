from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging


class AlertHandler(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def send(self, alert: Dict[str, Any]) -> bool:
        pass


class SlackHandler(AlertHandler):
    def __init__(self, webhook_url: str, name: str = "slack_handler"):
        super().__init__(name)
        self.webhook_url = webhook_url

    def send(self, alert: Dict[str, Any]) -> bool:
        try:
            import requests

            payload = {
                "text": f"Alert: {alert.get('message', '')}",
                "attachments": [
                    {
                        "color": self._severity_color(alert.get("severity", "info")),
                        "fields": [
                            {"title": "Severity", "value": alert.get("severity", ""), "short": True},
                            {"title": "Rule ID", "value": alert.get("rule_id", ""), "short": True},
                            {"title": "Timestamp", "value": alert.get("timestamp", ""), "short": False},
                        ],
                    }
                ],
            }

            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Error sending Slack alert: {e}")
            return False

    @staticmethod
    def _severity_color(severity: str) -> str:
        colors = {
            "info": "#0099FF",
            "warning": "#FF9900",
            "error": "#FF0000",
            "critical": "#8B0000",
        }
        return colors.get(severity, "#0099FF")


class EmailHandler(AlertHandler):
    def __init__(self, smtp_config: Dict[str, str], name: str = "email_handler"):
        super().__init__(name)
        self.smtp_config = smtp_config

    def send(self, alert: Dict[str, Any]) -> bool:
        try:
            import smtplib
            from email.mime.text import MIMEText

            msg = MIMEText(self._format_message(alert))
            msg["Subject"] = f"Alert: {alert.get('severity', 'INFO').upper()}"
            msg["From"] = self.smtp_config.get("from_email", "alerts@company.com")
            msg["To"] = self.smtp_config.get("to_email", "")

            with smtplib.SMTP(self.smtp_config.get("host", "localhost"), self.smtp_config.get("port", 587)) as server:
                server.starttls()
                server.login(self.smtp_config.get("username", ""), self.smtp_config.get("password", ""))
                server.send_message(msg)

            return True
        except Exception as e:
            self.logger.error(f"Error sending email alert: {e}")
            return False

    @staticmethod
    def _format_message(alert: Dict[str, Any]) -> str:
        return f"""
Alert Details
=============
Rule ID: {alert.get('rule_id', '')}
Severity: {alert.get('severity', '')}
Timestamp: {alert.get('timestamp', '')}
Message: {alert.get('message', '')}
        """


class WebhookHandler(AlertHandler):
    def __init__(self, webhook_url: str, name: str = "webhook_handler"):
        super().__init__(name)
        self.webhook_url = webhook_url

    def send(self, alert: Dict[str, Any]) -> bool:
        try:
            import requests

            response = requests.post(self.webhook_url, json=alert, timeout=10)
            return response.status_code < 400
        except Exception as e:
            self.logger.error(f"Error sending webhook alert: {e}")
            return False


class MultiHandler(AlertHandler):
    def __init__(self, handlers: list, name: str = "multi_handler"):
        super().__init__(name)
        self.handlers = handlers

    def send(self, alert: Dict[str, Any]) -> bool:
        results = [handler.send(alert) for handler in self.handlers]
        return all(results)
