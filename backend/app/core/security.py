"""Layered input/output guardrails, rate limiting and PII redaction."""
from __future__ import annotations

import html
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

CANARY = f"HM_CANARY_{secrets.token_hex(12)}"

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"reveal\s+(the\s+)?(system\s+)?prompt",
    r"print\s+(the\s+)?(system\s+)?prompt",
    r"show\s+me\s+your\s+(system\s+)?prompt",
    r"忽略(之前|以上|前面|所有)的?(指令|提示|规则)",
    r"无视(之前|以上|前面|所有)的?(指令|提示|规则)",
    r"(输出|显示|泄露|告诉我).{0,8}(系统提示词|系统指令|developer message|system prompt)",
    r"你现在是.{0,12}(开发者模式|越狱模式|DAN)",
    r"jailbreak|developer\s+mode|do\s+anything\s+now",
    r"(调用|执行).{0,8}(删除|转账|付款|rm\s+-rf|drop\s+table)",
]
SECRET_REQUEST = re.compile(
    r"(api[_\s-]?key|secret[_\s-]?key|access[_\s-]?token|密码|密钥).{0,20}(给我|输出|显示|是什么|多少)",
    re.IGNORECASE,
)
HTML_SCRIPT = re.compile(r"<\s*(script|iframe|object|embed|form)\b", re.IGNORECASE)
SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CARD = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE = re.compile(
    r"(?<!\d)(?:(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}|1[3-9]\d{9})(?!\d)"
)
SECRET_VALUE = re.compile(r"(sk-[A-Za-z0-9]{12,}|HM_CANARY_[a-f0-9]+|DEEPSEEK_API_KEY\s*=\s*\S+)")
PROMPT_LEAK_MARKERS = [
    "You are HouseMind", "系统提示词如下", "CANARY", "以下是系统消息",
]


@dataclass
class GuardResult:
    allowed: bool
    text: str
    reasons: list[str] = field(default_factory=list)
    severity: str = "none"
    redactions: int = 0


def inspect_input(text: str, max_length: int = 2000) -> GuardResult:
    reasons: list[str] = []
    severity = "none"
    if len(text) > max_length:
        return GuardResult(False, text[:max_length], ["输入超过长度限制"], "medium")
    if HTML_SCRIPT.search(text):
        reasons.append("检测到可执行 HTML 标签")
        severity = "medium"
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            reasons.append("检测到疑似提示词注入或越权工具指令")
            severity = "high"
            break
    if SECRET_REQUEST.search(text):
        reasons.append("检测到索取密钥/系统提示的请求")
        severity = "high"
    cleaned = "".join(char for char in text if char in "\n\t" or ord(char) >= 32)
    return GuardResult(not any(r for r in reasons if "注入" in r or "越权" in r or "密钥" in r), cleaned, reasons, severity)


def sanitize_output(text: str) -> str:
    """Remove secret-like strings, canaries, raw HTML and obvious prompt leaks."""
    if not text:
        return text
    text = text.replace(CANARY, "[已拦截]")
    text = SECRET_VALUE.sub("[已脱敏]", text)
    for marker in PROMPT_LEAK_MARKERS:
        text = text.replace(marker, "[已拦截]")
    text = re.sub(r"<\s*(script|iframe|object|embed)[^>]*>.*?<\s*/\s*\1\s*>", "", text, flags=re.I | re.S)
    text = re.sub(r"<\s*(script|iframe|object|embed)[^>]*>", "", text, flags=re.I)
    return text.strip()


def redact_pii(text: str) -> tuple[str, int]:
    count = 0
    for pattern, replacement in [
        (SSN, "[SSN]"),
        (CARD, "[CARD]"),
        (EMAIL, "[EMAIL]"),
        (PHONE, "[PHONE]"),
    ]:
        text, number = pattern.subn(replacement, text)
        count += number
    return text, count


def escape_html(text: str) -> str:
    return html.escape(text, quote=True)


class RateLimiter:
    """In-process sliding-window limiter. Use Redis when running many workers."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        now = time.time()
        with self._lock:
            bucket = self._events[key]
            while bucket and now - bucket[0] > window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                retry = max(1, int(window_seconds - (now - bucket[0])))
                return False, retry
            bucket.append(now)
            return True, 0

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {key: len(value) for key, value in self._events.items() if value}


rate_limiter = RateLimiter()
