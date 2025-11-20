import os
from typing import Optional


class Config:
    """Configuration management for the monitoring platform"""

    # Database
    DB_URL: str = os.getenv("MONITORING_DB_URL", "sqlite:///monitoring.db")
    DB_POOL_SIZE: int = int(os.getenv("MONITORING_DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("MONITORING_DB_MAX_OVERFLOW", "20"))
    DB_SSL: bool = os.getenv("MONITORING_DB_SSL", "false").lower() == "true"

    # Telemetry
    LOG_LEVEL: str = os.getenv("MONITORING_LOG_LEVEL", "INFO")
    EXPORT_INTERVAL: int = int(os.getenv("MONITORING_EXPORT_INTERVAL", "60"))
    RETENTION_DAYS: int = int(os.getenv("MONITORING_RETENTION_DAYS", "90"))
    METRICS_BATCH_SIZE: int = int(os.getenv("MONITORING_METRICS_BATCH_SIZE", "1000"))

    # Alerting
    SLACK_WEBHOOK_URL: Optional[str] = os.getenv("SLACK_WEBHOOK_URL")
    ALERT_THRESHOLD_SEVERITY: str = os.getenv("ALERT_THRESHOLD_SEVERITY", "error")
    ALERT_DEDUPLICATE_WINDOW: int = int(os.getenv("ALERT_DEDUPLICATE_WINDOW", "300"))
    ALERT_RATE_LIMIT: int = int(os.getenv("ALERT_RATE_LIMIT", "100"))

    # Dashboard
    DASHBOARD_HOST: str = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "8501"))
    DASHBOARD_THEME: str = os.getenv("DASHBOARD_THEME", "light")

    # Analytics
    ANOMALY_DETECTION_THRESHOLD: float = float(os.getenv("ANOMALY_DETECTION_THRESHOLD", "2.0"))
    REGRESSION_SIGNIFICANCE_LEVEL: float = float(os.getenv("REGRESSION_SIGNIFICANCE_LEVEL", "0.05"))
    REGRESSION_PERCENT_THRESHOLD: float = float(os.getenv("REGRESSION_PERCENT_THRESHOLD", "5.0"))

    # Performance
    MAX_WORKERS: int = int(os.getenv("MONITORING_MAX_WORKERS", "4"))
    CACHE_TTL: int = int(os.getenv("MONITORING_CACHE_TTL", "300"))

    @classmethod
    def get_db_url(cls) -> str:
        return cls.DB_URL

    @classmethod
    def is_production(cls) -> bool:
        return os.getenv("ENVIRONMENT", "development") == "production"

    @classmethod
    def get_all_settings(cls) -> dict:
        return {
            "database": {
                "url": cls.DB_URL,
                "pool_size": cls.DB_POOL_SIZE,
                "max_overflow": cls.DB_MAX_OVERFLOW,
                "ssl": cls.DB_SSL,
            },
            "telemetry": {
                "log_level": cls.LOG_LEVEL,
                "export_interval": cls.EXPORT_INTERVAL,
                "retention_days": cls.RETENTION_DAYS,
                "metrics_batch_size": cls.METRICS_BATCH_SIZE,
            },
            "alerting": {
                "slack_webhook_url": bool(cls.SLACK_WEBHOOK_URL),
                "threshold_severity": cls.ALERT_THRESHOLD_SEVERITY,
                "deduplicate_window": cls.ALERT_DEDUPLICATE_WINDOW,
            },
            "dashboard": {
                "host": cls.DASHBOARD_HOST,
                "port": cls.DASHBOARD_PORT,
                "theme": cls.DASHBOARD_THEME,
            },
        }
