import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from .metrics import Metric
from .events import Event


class MetricsExporter(ABC):
    @abstractmethod
    def export(self, metrics: Dict[str, Metric]) -> bool:
        pass

    @abstractmethod
    def export_events(self, events: List[Event]) -> bool:
        pass


class JSONExporter(MetricsExporter):
    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, metrics: Dict[str, Metric]) -> bool:
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"metrics_{timestamp}.json"

            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": {},
            }

            for name, metric in metrics.items():
                metric_data = {
                    "definition": {
                        "name": metric.definition.name,
                        "type": metric.definition.type.value,
                        "description": metric.definition.description,
                        "unit": metric.definition.unit,
                    },
                    "values": [],
                }

                if hasattr(metric, "get_statistics"):
                    metric_data["statistics"] = metric.get_statistics()
                elif hasattr(metric, "get_summary"):
                    metric_data["summary"] = metric.get_summary()
                elif hasattr(metric, "get_total"):
                    metric_data["total"] = metric.get_total()
                elif hasattr(metric, "get_value"):
                    metric_data["value"] = metric.get_value()

                for value in metric.values:
                    metric_data["values"].append({
                        "value": value.value,
                        "timestamp": value.timestamp.isoformat(),
                        "tags": value.tags,
                    })

                data["metrics"][name] = metric_data

            with open(output_file, "w") as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error exporting metrics to JSON: {e}")
            return False

    def export_events(self, events: List[Event]) -> bool:
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"events_{timestamp}.json"

            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "events": [event.to_dict() for event in events],
            }

            with open(output_file, "w") as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error exporting events to JSON: {e}")
            return False


class PrometheusExporter(MetricsExporter):
    def __init__(self, registry=None):
        try:
            from prometheus_client import CollectorRegistry, Gauge, Counter as PrometheusCounter
            self.registry = registry or CollectorRegistry()
            self.prometheus_metrics = {}
        except ImportError:
            raise ImportError("prometheus-client is required for PrometheusExporter")

    def export(self, metrics: Dict[str, Metric]) -> bool:
        try:
            from prometheus_client import Gauge, Counter as PrometheusCounter, generate_latest

            for name, metric in metrics.items():
                if name not in self.prometheus_metrics:
                    if "counter" in metric.definition.type.value.lower():
                        self.prometheus_metrics[name] = PrometheusCounter(
                            name=name,
                            documentation=metric.definition.description,
                            registry=self.registry,
                        )
                    else:
                        self.prometheus_metrics[name] = Gauge(
                            name=name,
                            documentation=metric.definition.description,
                            registry=self.registry,
                        )

                prom_metric = self.prometheus_metrics[name]

                if hasattr(metric, "get_total"):
                    prom_metric.set(metric.get_total())
                elif hasattr(metric, "get_value"):
                    prom_metric.set(metric.get_value())

            output = generate_latest(self.registry).decode("utf-8")
            return True
        except Exception as e:
            print(f"Error exporting metrics to Prometheus: {e}")
            return False

    def export_events(self, events: List[Event]) -> bool:
        try:
            from prometheus_client import Counter, generate_latest

            event_counter = Counter(
                "events_total",
                "Total number of events",
                ["event_type", "severity"],
                registry=self.registry,
            )

            for event in events:
                event_counter.labels(event_type=event.event_type.value, severity=event.severity.value).inc()

            return True
        except Exception as e:
            print(f"Error exporting events to Prometheus: {e}")
            return False

    def get_metrics_output(self) -> str:
        try:
            from prometheus_client import generate_latest
            return generate_latest(self.registry).decode("utf-8")
        except Exception:
            return ""


class WebhookExporter(MetricsExporter):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def export(self, metrics: Dict[str, Metric]) -> bool:
        try:
            import requests

            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": {},
            }

            for name, metric in metrics.items():
                payload["metrics"][name] = {
                    "type": metric.definition.type.value,
                    "description": metric.definition.description,
                }

                if hasattr(metric, "get_statistics"):
                    payload["metrics"][name]["statistics"] = metric.get_statistics()
                elif hasattr(metric, "get_value"):
                    payload["metrics"][name]["value"] = metric.get_value()

            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code < 400
        except Exception as e:
            print(f"Error exporting metrics to webhook: {e}")
            return False

    def export_events(self, events: List[Event]) -> bool:
        try:
            import requests

            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "events": [event.to_dict() for event in events],
            }

            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code < 400
        except Exception as e:
            print(f"Error exporting events to webhook: {e}")
            return False


class BatchExporter(MetricsExporter):
    def __init__(self, exporters: List[MetricsExporter]):
        self.exporters = exporters

    def export(self, metrics: Dict[str, Metric]) -> bool:
        results = [exporter.export(metrics) for exporter in self.exporters]
        return all(results)

    def export_events(self, events: List[Event]) -> bool:
        results = [exporter.export_events(events) for exporter in self.exporters]
        return all(results)
