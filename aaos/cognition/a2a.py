"""
Agent-to-Agent (A2A) in-process message bus.

Specialist agents can publish partial results and subscribe without
routing every micro-step through the Supervisor.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Callable, Optional


@dataclass
class A2AMessage:
    id: str
    sender: str
    topic: str
    payload: dict[str, Any]
    ts: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None


class A2ABus:
    def __init__(self, history: int = 200):
        self._lock = Lock()
        self._queues: dict[str, deque[A2AMessage]] = defaultdict(
            lambda: deque(maxlen=history)
        )
        self._subscribers: dict[str, list[Callable[[A2AMessage], None]]] = defaultdict(
            list
        )
        self._inbox: dict[str, deque[A2AMessage]] = defaultdict(
            lambda: deque(maxlen=history)
        )

    def publish(
        self,
        sender: str,
        topic: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> A2AMessage:
        msg = A2AMessage(
            id=str(uuid.uuid4()),
            sender=sender,
            topic=topic,
            payload=payload,
            correlation_id=correlation_id,
        )
        with self._lock:
            self._queues[topic].append(msg)
            # deliver to agent inboxes listening on topic pattern agent:*
            for agent, q in list(self._inbox.items()):
                if topic == f"agent:{agent}" or topic.startswith("broadcast"):
                    q.append(msg)
            subs = list(self._subscribers.get(topic, []))
        for cb in subs:
            try:
                cb(msg)
            except Exception:
                pass
        return msg

    def send(
        self, sender: str, to_agent: str, payload: dict[str, Any], **kw: Any
    ) -> A2AMessage:
        return self.publish(
            sender, f"agent:{to_agent}", payload, correlation_id=kw.get("correlation_id")
        )

    def receive(self, agent: str, max_messages: int = 10) -> list[A2AMessage]:
        with self._lock:
            q = self._inbox[agent]
            out = []
            for _ in range(min(max_messages, len(q))):
                out.append(q.popleft())
            return out

    def subscribe(self, topic: str, callback: Callable[[A2AMessage], None]) -> None:
        with self._lock:
            self._subscribers[topic].append(callback)

    def history(self, topic: str, limit: int = 20) -> list[A2AMessage]:
        with self._lock:
            return list(self._queues.get(topic, deque()))[-limit:]


_bus = A2ABus()


def get_a2a_bus() -> A2ABus:
    return _bus
