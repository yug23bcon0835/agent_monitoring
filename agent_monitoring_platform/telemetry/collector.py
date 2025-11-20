from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from threading import Thread, Lock
import time

from .metrics import MetricsRegistry, Metric
from .events import EventEmitter, Event
from .agent_tracer import AgentTracer
from .performance_monitor import PerformanceMonitor
from .exporters import MetricsExporter, JSONExporter


class TelemetryCollector:
    def __init__(self, metrics_registry: Optional[MetricsRegistry] = None, export_interval: int = 60):
        self.metrics_registry = metrics_registry or MetricsRegistry()
        self.event_emitter = EventEmitter()
        self.agent_tracer = AgentTracer(self.metrics_registry, self.event_emitter)
        self.performance_monitor = PerformanceMonitor()
        self.exporters: List[MetricsExporter] = []
        self.export_interval = export_interval
        self.is_running = False
        self.export_thread: Optional[Thread] = None
        self.lock = Lock()
        self._retention_days = 90

    def add_exporter(self, exporter: MetricsExporter):
        with self.lock:
            self.exporters.append(exporter)

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.performance_monitor.start()
        self.export_thread = Thread(target=self._export_loop, daemon=True)
        self.export_thread.start()

    def stop(self):
        self.is_running = False
        self.performance_monitor.stop()
        if self.export_thread:
            self.export_thread.join(timeout=5.0)

    def _export_loop(self):
        while self.is_running:
            try:
                self.export_all()
                self.cleanup_old_data()
            except Exception as e:
                print(f"Error in export loop: {e}")
            time.sleep(self.export_interval)

    def export_all(self) -> bool:
        with self.lock:
            if not self.exporters:
                return False

            results = []
            for exporter in self.exporters:
                try:
                    result = exporter.export(self.metrics_registry.metrics)
                    exporter.export_events(self.event_emitter.get_events())
                    results.append(result)
                except Exception as e:
                    print(f"Error exporting metrics: {e}")
                    results.append(False)

            return all(results) if results else False

    def export_to_file(self, output_dir: str = ".") -> bool:
        exporter = JSONExporter(output_dir)
        return exporter.export(self.metrics_registry.metrics)

    def cleanup_old_data(self):
        retention = timedelta(days=self._retention_days)
        self.metrics_registry.cleanup_old_values(retention)
        self.agent_tracer.clear_spans()

    def set_retention_days(self, days: int):
        self._retention_days = days

    def get_metrics(self) -> Dict[str, Metric]:
        return self.metrics_registry.metrics

    def get_metric(self, name: str) -> Optional[Metric]:
        return self.metrics_registry.get_metric(name)

    def get_all_metrics_summary(self) -> Dict[str, Any]:
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": self.metrics_registry.get_all_metrics(),
            "events": self.event_emitter.get_stats(),
            "traces": self.agent_tracer.get_statistics(),
            "system": self.performance_monitor.get_metrics_summary(),
        }
        return summary

    def record_agent_execution(
        self,
        agent_id: str,
        duration_ms: float,
        success: bool,
        tokens_used: int = 0,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        trace_id = self.agent_tracer.start_trace(agent_id, context=metadata)
        dur_metric = self.metrics_registry.get_metric("agent_execution_duration") or self._create_default_histogram("agent_execution_duration")
        success_metric = self.metrics_registry.get_metric("agent_success_rate") or self._create_default_counter("agent_success_rate")

        if dur_metric:
            dur_metric.record(duration_ms)

        if success and success_metric:
            success_metric.increment()

        self.agent_tracer.end_trace(trace_id, status="OK" if success else "ERROR")

    def record_llm_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        cost: float = 0.0,
        error: Optional[str] = None,
    ):
        span_id = self.agent_tracer.trace_llm_call(model, prompt_tokens)

        if error:
            self.agent_tracer.end_span(span_id, status="ERROR", error=error)
        else:
            self.agent_tracer.add_span_attribute(span_id, "completion_tokens", completion_tokens)
            self.agent_tracer.add_span_attribute(span_id, "latency_ms", latency_ms)
            self.agent_tracer.add_span_attribute(span_id, "cost", cost)
            self.agent_tracer.end_span(span_id, status="OK")

        llm_latency_metric = self.metrics_registry.get_metric("llm_latency_ms") or self._create_default_histogram(
            "llm_latency_ms"
        )
        if llm_latency_metric:
            llm_latency_metric.record(latency_ms, tags={"model": model})

    def record_tool_execution(
        self, tool_name: str, duration_ms: float, success: bool, error: Optional[str] = None
    ):
        span_id = self.agent_tracer.trace_tool_call(tool_name, {})

        if error:
            self.agent_tracer.end_span(span_id, status="ERROR", error=error)
        else:
            self.agent_tracer.end_span(span_id, status="OK")

        tool_duration_metric = self.metrics_registry.get_metric("tool_execution_duration") or self._create_default_histogram(
            "tool_execution_duration"
        )
        if tool_duration_metric:
            tool_duration_metric.record(duration_ms, tags={"tool": tool_name})

    def get_traces(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        spans = self.agent_tracer.get_all_spans()
        if agent_id:
            spans = [s for s in spans if agent_id in s.operation_name]
        return [s.to_dict() for s in spans]

    def get_events_since(self, timestamp: datetime) -> List[Event]:
        return self.event_emitter.get_events_since(timestamp)

    def _create_default_histogram(self, name: str):
        with self.lock:
            existing = self.metrics_registry.get_metric(name)
            if existing:
                return existing
            return self.metrics_registry.histogram(name, f"Default histogram: {name}", unit="ms")

    def _create_default_counter(self, name: str):
        with self.lock:
            existing = self.metrics_registry.get_metric(name)
            if existing:
                return existing
            return self.metrics_registry.counter(name, f"Default counter: {name}")

    def emit_event(self, event: Event):
        self.event_emitter.emit(event)

    def get_health_status(self) -> Dict[str, Any]:
        system_metrics = self.performance_monitor.get_current_metrics()
        return {
            "is_running": self.is_running,
            "cpu_percent": system_metrics.cpu_percent,
            "memory_percent": system_metrics.memory_percent,
            "disk_percent": system_metrics.disk_percent,
            "metrics_count": len(self.metrics_registry.metrics),
            "events_count": len(self.event_emitter.event_history),
            "active_spans": len(self.agent_tracer.active_spans),
            "completed_spans": len(self.agent_tracer.completed_spans),
        }
