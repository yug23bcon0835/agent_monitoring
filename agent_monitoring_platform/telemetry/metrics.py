from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timedelta
import statistics
from threading import RLock


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricDefinition:
    name: str
    type: MetricType
    description: str
    unit: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricValue:
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)


class Metric:
    def __init__(self, definition: MetricDefinition):
        self.definition = definition
        self.values: List[MetricValue] = []
        self._lock = RLock()

    def record(self, value: float, tags: Optional[Dict[str, str]] = None):
        metric_value = MetricValue(value=value, tags=tags or {})
        with self._lock:
            self.values.append(metric_value)

    def get_values(self, start_time: Optional[datetime] = None, duration: Optional[timedelta] = None) -> List[MetricValue]:
        if not start_time:
            return self.values

        if duration:
            end_time = start_time + duration
        else:
            end_time = datetime.utcnow()

        return [v for v in self.values if start_time <= v.timestamp <= end_time]

    def cleanup_old_values(self, retention: timedelta):
        cutoff = datetime.utcnow() - retention
        with self._lock:
            # Atomic replacement protected by lock
            self.values = [v for v in self.values if v.timestamp > cutoff]

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "definition": {
                    "name": self.definition.name,
                    "type": self.definition.type.value,
                    "description": self.definition.description,
                    "unit": self.definition.unit,
                },
                "values_count": len(self.values),
            }


class Counter(Metric):
    def __init__(self, definition: MetricDefinition):
        if definition.type != MetricType.COUNTER:
            raise ValueError(f"Counter must have type COUNTER, got {definition.type}")
        super().__init__(definition)
        self.total = 0

    def increment(self, amount: float = 1, tags: Optional[Dict[str, str]] = None):
        self.total += amount
        self.record(amount, tags)

    def get_total(self) -> float:
        with self._lock:
            return self.total


class Gauge(Metric):
    def __init__(self, definition: MetricDefinition):
        if definition.type != MetricType.GAUGE:
            raise ValueError(f"Gauge must have type GAUGE, got {definition.type}")
        super().__init__(definition)
        self.current_value = 0

    def set(self, value: float, tags: Optional[Dict[str, str]] = None):
        with self._lock:
            self.current_value = value
            self.record(value, tags)

    def get_value(self) -> float:
        with self._lock:
            return self.current_value

    def increment(self, amount: float = 1, tags: Optional[Dict[str, str]] = None):
        with self._lock:
            self.current_value += amount
            self.record(self.current_value, tags)

    def decrement(self, amount: float = 1, tags: Optional[Dict[str, str]] = None):
        with self._lock:
            self.current_value -= amount
            self.record(self.current_value, tags)


class Histogram(Metric):
    def __init__(self, definition: MetricDefinition, buckets: Optional[List[float]] = None):
        if definition.type != MetricType.HISTOGRAM:
            raise ValueError(f"Histogram must have type HISTOGRAM, got {definition.type}")
        super().__init__(definition)
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self.sum = 0
        self.count = 0

    def record(self, value: float, tags: Optional[Dict[str, str]] = None):
        with self._lock:
            super().record(value, tags)
            self.sum += value
            self.count += 1

    def get_statistics(self) -> Dict[str, float]:
        with self._lock:
            if not self.values:
                return {}

            values = [v.value for v in self.values]
            values.sort()
            
            current_count = self.count
            current_sum = self.sum

            return {
                "count": current_count,
                "sum": current_sum,
                "mean": current_sum / current_count if current_count > 0 else 0,
                "min": values[0] if values else 0,
                "max": values[-1] if values else 0,
                "median": statistics.median(values) if values else 0,
                "p50": self._percentile(values, 50),
                "p90": self._percentile(values, 90),
                "p95": self._percentile(values, 95),
                "p99": self._percentile(values, 99),
            }

    @staticmethod
    def _percentile(values: List[float], percentile: float) -> float:
        if not values:
            return 0
        idx = int(len(values) * percentile / 100)
        return values[min(idx, len(values) - 1)]


class Summary(Metric):
    def __init__(self, definition: MetricDefinition):
        if definition.type != MetricType.SUMMARY:
            raise ValueError(f"Summary must have type SUMMARY, got {definition.type}")
        super().__init__(definition)
        self.sum = 0
        self.count = 0

    def record(self, value: float, tags: Optional[Dict[str, str]] = None):
        with self._lock:
            super().record(value, tags)
            self.sum += value
            self.count += 1

    def get_summary(self) -> Dict[str, float]:
        with self._lock:
            if not self.values:
                return {}

            values = [v.value for v in self.values]
            return {
                "count": self.count,
                "sum": self.sum,
                "mean": self.sum / self.count if self.count > 0 else 0,
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
            }


class MetricsRegistry:
    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self._lock = RLock()

    def register(self, metric: Metric):
        with self._lock:
            if metric.definition.name in self.metrics:
                raise ValueError(f"Metric {metric.definition.name} already registered")
            self.metrics[metric.definition.name] = metric

    def get_metric(self, name: str) -> Optional[Metric]:
        with self._lock:
            return self.metrics.get(name)

    def counter(self, name: str, description: str, unit: Optional[str] = None) -> Counter:
        with self._lock:
            if name in self.metrics:
                metric = self.metrics[name]
                if not isinstance(metric, Counter):
                    raise ValueError(f"Metric {name} already exists but is not a Counter")
                return metric
                
            definition = MetricDefinition(
                name=name,
                type=MetricType.COUNTER,
                description=description,
                unit=unit,
            )
            counter = Counter(definition)
            self.metrics[name] = counter
            return counter

    def gauge(self, name: str, description: str, unit: Optional[str] = None) -> Gauge:
        with self._lock:
            if name in self.metrics:
                metric = self.metrics[name]
                if not isinstance(metric, Gauge):
                    raise ValueError(f"Metric {name} already exists but is not a Gauge")
                return metric

            definition = MetricDefinition(
                name=name,
                type=MetricType.GAUGE,
                description=description,
                unit=unit,
            )
            gauge = Gauge(definition)
            self.metrics[name] = gauge
            return gauge

    def histogram(
        self, name: str, description: str, unit: Optional[str] = None, buckets: Optional[List[float]] = None
    ) -> Histogram:
        with self._lock:
            if name in self.metrics:
                metric = self.metrics[name]
                if not isinstance(metric, Histogram):
                    raise ValueError(f"Metric {name} already exists but is not a Histogram")
                return metric

            definition = MetricDefinition(
                name=name,
                type=MetricType.HISTOGRAM,
                description=description,
                unit=unit,
            )
            histogram = Histogram(definition, buckets)
            self.metrics[name] = histogram
            return histogram

    def summary(self, name: str, description: str, unit: Optional[str] = None) -> Summary:
        with self._lock:
            if name in self.metrics:
                metric = self.metrics[name]
                if not isinstance(metric, Summary):
                    raise ValueError(f"Metric {name} already exists but is not a Summary")
                return metric

            definition = MetricDefinition(
                name=name,
                type=MetricType.SUMMARY,
                description=description,
                unit=unit,
            )
            summary = Summary(definition)
            self.metrics[name] = summary
            return summary

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            # Create a snapshot of current metrics
            metrics_snapshot = list(self.metrics.items())
            
        return {name: metric.to_dict() for name, metric in metrics_snapshot}

    def cleanup_old_values(self, retention: timedelta):
        with self._lock:
            metrics = list(self.metrics.values())
            
        for metric in metrics:
            metric.cleanup_old_values(retention)
