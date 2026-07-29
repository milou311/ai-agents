"""Generic HTTP API caller."""

from typing import Any, Optional

import httpx


def call_api(
    url: str,
    method: str = "GET",
    headers: Optional[dict[str, str]] = None,
    body: Optional[dict[str, Any]] = None,
    timeout: int = 20,
) -> str:
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
