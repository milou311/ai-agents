"""Generic HTTP API caller (GET/POST)."""

import httpx
from typing import Optional, Dict, Any
import json


def call_api(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 20,
) -> str:
    """
    Call an external HTTP API and return the response text (truncated to 4000 chars).
    """
    try:
        method = method.upper()
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            if method == "GET":
                r = client.get(url, headers=headers or {})
            elif method == "POST":
                r = client.post(url, headers=headers or {}, json=body)
            elif method == "PUT":
                r = client.put(url, headers=headers or {}, json=body)
            else:
                return f"طريقة غير مدعومة: {method}"

        text = r.text
        if len(text) > 4000:
            text = text[:4000] + "\n... (مقطوع)"
        return f"Status: {r.status_code}\n\n{text}"
    except Exception as e:
        return f"خطأ في الاتصال بالـ API: {e}"
