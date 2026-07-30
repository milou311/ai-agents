"""
Phase 6 — Operational Self-State.

Tracks live operational facts the agent can report about itself:
active tasks, recent errors, skill outcomes, metrics snapshot.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class SkillStat:
    attempts: int = 0
    successes: int = 0
    failures: int = 0

    @property
    def success_rate(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.successes / self.attempts


class OperationalState:
    def __init__(self, error_limit: int = 50):
        self._lock = Lock()
        self.active_goals: dict[str, dict[str, Any]] = {}
        self.recent_errors: deque[dict[str, Any]] = deque(maxlen=error_limit)
        self.skill_stats: dict[str, SkillStat] = defaultdict(SkillStat)
        self.tool_stats: dict[str, SkillStat] = defaultdict(SkillStat)
        self.started_at = time.time()

    def start_goal(self, goal_id: str, text: str, user_id: Any = None) -> None:
        with self._lock:
            self.active_goals[goal_id] = {
                "text": text[:500],
                "user_id": user_id,
                "started_at": time.time(),
            }

    def end_goal(self, goal_id: str, ok: bool = True) -> None:
        with self._lock:
            self.active_goals.pop(goal_id, None)

    def record_error(self, source: str, message: str) -> None:
        with self._lock:
            self.recent_errors.append(
                {
                    "ts": time.time(),
                    "source": source,
                    "message": message[:500],
                }
            )

    def record_skill(self, name: str, ok: bool) -> None:
        with self._lock:
            st = self.skill_stats[name]
            st.attempts += 1
            if ok:
                st.successes += 1
            else:
                st.failures += 1

    def record_tool(self, name: str, ok: bool) -> None:
        with self._lock:
            st = self.tool_stats[name]
            st.attempts += 1
            if ok:
                st.successes += 1
            else:
                st.failures += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            metrics = {}
            try:
                from aaos.monitoring import get_metrics

                metrics = get_metrics().snapshot()
            except Exception:
                pass

            return {
                "uptime_sec": round(time.time() - self.started_at, 1),
                "active_goals": list(self.active_goals.values()),
                "active_goals_count": len(self.active_goals),
                "recent_errors": list(self.recent_errors)[-10:],
                "skill_stats": {
                    k: {
                        "attempts": v.attempts,
                        "successes": v.successes,
                        "failures": v.failures,
                        "success_rate": round(v.success_rate, 3),
                    }
                    for k, v in self.skill_stats.items()
                },
                "tool_stats": {
                    k: {
                        "attempts": v.attempts,
                        "successes": v.successes,
                        "failures": v.failures,
                        "success_rate": round(v.success_rate, 3),
                    }
                    for k, v in self.tool_stats.items()
                },
                "metrics": metrics,
            }


_state = OperationalState()


def get_operational_state() -> OperationalState:
    return _state
