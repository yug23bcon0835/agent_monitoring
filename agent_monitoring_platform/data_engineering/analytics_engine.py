from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging

from .database_manager import DatabaseManager


class AnalyticsEngine:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)

    def get_time_series(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        granularity: str = "1h",
    ) -> List[Dict[str, Any]]:
        metrics = self.db_manager.get_metrics(metric_name=metric_name)
        filtered = [m for m in metrics if start_time <= m.timestamp <= end_time]

        buckets = self._create_time_buckets(start_time, end_time, granularity)
        result = []

        for bucket_start, bucket_end in buckets:
            bucket_data = [m for m in filtered if bucket_start <= m.timestamp <= bucket_end]
            if bucket_data:
                values = [m.value for m in bucket_data]
                result.append({
                    "timestamp": bucket_start.isoformat(),
                    "count": len(values),
                    "sum": sum(values),
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                })

        return result

    def get_aggregations(
        self,
        metric_name: str,
        group_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metrics = self.db_manager.get_metrics(metric_name=metric_name)

        if not metrics:
            return {}

        if group_by:
            grouped = {}
            for metric in metrics:
                key = metric.tags.get(group_by, "unknown")
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(metric.value)

            result = {}
            for key, values in grouped.items():
                result[key] = {
                    "count": len(values),
                    "sum": sum(values),
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }
            return result

        values = [m.value for m in metrics]
        return {
            "count": len(values),
            "sum": sum(values),
            "mean": sum(values) / len(values) if values else 0,
            "min": min(values) if values else 0,
            "max": max(values) if values else 0,
        }

    def get_correlations(self, metric_names: List[str]) -> Dict[str, float]:
        try:
            import numpy as np
            from scipy.stats import pearsonr

            metric_data = {}
            for metric_name in metric_names:
                metrics = self.db_manager.get_metrics(metric_name=metric_name)
                metric_data[metric_name] = [m.value for m in metrics]

            correlations = {}
            for i, metric1 in enumerate(metric_names):
                for metric2 in metric_names[i + 1 :]:
                    values1 = metric_data.get(metric1, [])
                    values2 = metric_data.get(metric2, [])

                    if len(values1) > 1 and len(values1) == len(values2):
                        corr, _ = pearsonr(values1, values2)
                        correlations[f"{metric1}_vs_{metric2}"] = corr

            return correlations
        except ImportError:
            self.logger.warning("scipy not available for correlation analysis")
            return {}

    def detect_anomalies(self, metric_name: str, window_size: int = 10, threshold: float = 2.0) -> List[Dict[str, Any]]:
        metrics = self.db_manager.get_metrics(metric_name=metric_name)
        if len(metrics) < window_size:
            return []

        values = [m.value for m in metrics]
        anomalies = []

        for i in range(window_size, len(values)):
            window = values[i - window_size : i]
            mean = sum(window) / len(window)
            variance = sum((x - mean) ** 2 for x in window) / len(window)
            std_dev = variance ** 0.5

            current_value = values[i]
            z_score = abs((current_value - mean) / std_dev) if std_dev > 0 else 0

            if z_score > threshold:
                anomalies.append({
                    "timestamp": metrics[i].timestamp.isoformat(),
                    "value": current_value,
                    "mean": mean,
                    "std_dev": std_dev,
                    "z_score": z_score,
                })

        return anomalies

    def forecast(self, metric_name: str, forecast_steps: int = 10) -> List[Dict[str, Any]]:
        try:
            from sklearn.linear_model import LinearRegression
            import numpy as np

            metrics = self.db_manager.get_metrics(metric_name=metric_name)
            if not metrics:
                return []

            values = np.array([m.value for m in metrics]).reshape(-1, 1)
            X = np.arange(len(values)).reshape(-1, 1)

            model = LinearRegression()
            model.fit(X, values)

            forecast_X = np.arange(len(values), len(values) + forecast_steps).reshape(-1, 1)
            forecast_values = model.predict(forecast_X)

            result = []
            last_time = metrics[-1].timestamp
            for i, value in enumerate(forecast_values):
                forecast_time = last_time + timedelta(hours=i + 1)
                result.append({
                    "timestamp": forecast_time.isoformat(),
                    "value": float(value[0]),
                })

            return result
        except ImportError:
            self.logger.warning("scikit-learn not available for forecasting")
            return []

    def get_metric_distribution(self, metric_name: str, bins: int = 10) -> Dict[str, Any]:
        metrics = self.db_manager.get_metrics(metric_name=metric_name)
        if not metrics:
            return {}

        values = [m.value for m in metrics]
        min_val = min(values)
        max_val = max(values)
        range_val = max_val - min_val

        if range_val == 0:
            return {
                "metric_name": metric_name,
                "distribution": [{
                    "bin": f"{min_val:.2f}",
                    "count": len(values),
                }],
            }

        bin_width = range_val / bins
        distribution = [0] * bins

        for value in values:
            bin_idx = min(int((value - min_val) / bin_width), bins - 1)
            distribution[bin_idx] += 1

        return {
            "metric_name": metric_name,
            "distribution": [
                {
                    "bin": f"{min_val + i * bin_width:.2f}-{min_val + (i + 1) * bin_width:.2f}",
                    "count": distribution[i],
                }
                for i in range(bins)
            ],
        }

    def get_execution_statistics(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        executions = self.db_manager.get_executions(agent_id=agent_id)

        if not executions:
            return {}

        durations = [e.duration_ms for e in executions if e.duration_ms]
        success_count = sum(1 for e in executions if e.success)

        return {
            "total_executions": len(executions),
            "successful": success_count,
            "failed": len(executions) - success_count,
            "success_rate": success_count / len(executions) if executions else 0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "min_duration_ms": min(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "total_tokens": sum(e.tokens_used for e in executions if e.tokens_used),
        }

    def _create_time_buckets(self, start: datetime, end: datetime, granularity: str) -> List[Tuple[datetime, datetime]]:
        buckets = []
        current = start

        if granularity == "1h":
            delta = timedelta(hours=1)
        elif granularity == "1d":
            delta = timedelta(days=1)
        elif granularity == "1w":
            delta = timedelta(weeks=1)
        else:
            delta = timedelta(hours=1)

        while current < end:
            next_bucket = current + delta
            buckets.append((current, min(next_bucket, end)))
            current = next_bucket

        return buckets
