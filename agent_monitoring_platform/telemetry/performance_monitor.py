import psutil
import os
from dataclasses import dataclass
from typing import Dict, Optional, Any
from datetime import datetime
from threading import Thread
import time


@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_rss_mb: float
    memory_vms_mb: float
    disk_percent: float
    network_sent_mb: float
    network_recv_mb: float


@dataclass
class ProcessMetrics:
    pid: int
    cpu_percent: float
    memory_mb: float
    num_threads: int
    num_fds: int
    memory_percent: float


class PerformanceMonitor:
    def __init__(self, interval: float = 5.0):
        self.interval = interval
        self.is_running = False
        self.monitor_thread: Optional[Thread] = None
        self.metrics_history: list[SystemMetrics] = []
        self.process_id = os.getpid()
        self.process = psutil.Process(self.process_id)
        self.last_net_io = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)

    def _monitor_loop(self):
        while self.is_running:
            try:
                metrics = self._collect_metrics()
                self.metrics_history.append(metrics)
                if len(self.metrics_history) > 1000:
                    self.metrics_history.pop(0)
            except Exception:
                pass
            time.sleep(self.interval)

    def _collect_metrics(self) -> SystemMetrics:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        net_io = psutil.net_io_counters()
        if self.last_net_io:
            net_sent = (net_io.bytes_sent - self.last_net_io.bytes_sent) / 1024 / 1024
            net_recv = (net_io.bytes_recv - self.last_net_io.bytes_recv) / 1024 / 1024
        else:
            net_sent = net_io.bytes_sent / 1024 / 1024
            net_recv = net_io.bytes_recv / 1024 / 1024
        self.last_net_io = net_io

        return SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_rss_mb=memory.used / 1024 / 1024,
            memory_vms_mb=memory.total / 1024 / 1024,
            disk_percent=disk.percent,
            network_sent_mb=net_sent,
            network_recv_mb=net_recv,
        )

    def get_current_metrics(self) -> SystemMetrics:
        return self._collect_metrics()

    def get_process_metrics(self) -> ProcessMetrics:
        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            try:
                memory_percent = self.process.memory_percent()
            except AttributeError:
                memory_percent = (memory_info.rss / psutil.virtual_memory().total) * 100

            return ProcessMetrics(
                pid=self.process_id,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                num_threads=self.process.num_threads(),
                num_fds=self.process.num_fds() if hasattr(self.process, "num_fds") else -1,
                memory_percent=memory_percent,
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return ProcessMetrics(
                pid=self.process_id,
                cpu_percent=0,
                memory_mb=0,
                num_threads=0,
                num_fds=0,
                memory_percent=0,
            )

    def get_metrics_summary(self) -> Dict[str, Any]:
        if not self.metrics_history:
            return {}

        cpu_values = [m.cpu_percent for m in self.metrics_history]
        memory_values = [m.memory_percent for m in self.metrics_history]

        return {
            "sample_count": len(self.metrics_history),
            "cpu": {
                "current": cpu_values[-1] if cpu_values else 0,
                "min": min(cpu_values),
                "max": max(cpu_values),
                "avg": sum(cpu_values) / len(cpu_values),
            },
            "memory": {
                "current": memory_values[-1] if memory_values else 0,
                "min": min(memory_values),
                "max": max(memory_values),
                "avg": sum(memory_values) / len(memory_values),
            },
            "process": self.get_process_metrics().to_dict() if hasattr(ProcessMetrics, "to_dict") else {},
        }

    def get_metrics_history(self, limit: Optional[int] = None) -> list[Dict[str, Any]]:
        history = self.metrics_history
        if limit:
            history = history[-limit:]
        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "cpu_percent": m.cpu_percent,
                "memory_percent": m.memory_percent,
                "memory_rss_mb": m.memory_rss_mb,
                "disk_percent": m.disk_percent,
            }
            for m in history
        ]

    def clear_history(self):
        self.metrics_history.clear()
