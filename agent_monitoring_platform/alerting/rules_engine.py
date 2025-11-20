from dataclasses import dataclass
from typing import Optional, Callable, Any
from enum import Enum


class Operator(str, Enum):
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="
    NEQ = "!="


@dataclass
class Rule:
    rule_id: str
    metric_name: str
    operator: str
    threshold: float
    duration_seconds: int
    severity: str
    enabled: bool = True
    description: str = ""

    def evaluate(self, current_value: float) -> bool:
        if operator_instance.get(self.operator):
            return operator_instance[self.operator](current_value, self.threshold)
        return False


operator_instance = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


class RulesEngine:
    def __init__(self):
        self.rules: dict = {}
        self.evaluations: list = []

    def add_rule(self, rule: Rule):
        self.rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def evaluate_all(self, metrics: dict) -> list:
        triggered_rules = []
        for rule in self.rules.values():
            if not rule.enabled:
                continue

            if rule.metric_name in metrics:
                metric_value = metrics[rule.metric_name]
                if rule.evaluate(metric_value):
                    triggered_rules.append(rule)

        return triggered_rules

    def evaluate_rule(self, rule_id: str, metric_value: float) -> bool:
        rule = self.rules.get(rule_id)
        if not rule:
            return False
        return rule.evaluate(metric_value)

    def get_enabled_rules(self) -> list:
        return [r for r in self.rules.values() if r.enabled]

    def enable_rule(self, rule_id: str) -> bool:
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            return True
        return False
