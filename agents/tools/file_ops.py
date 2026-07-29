"""
Safe file operations inside a per-user sandbox folder.
Users can only read/write inside data/files/<user_id>/
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "files"


def _user_dir(user_id: int) -> Path:
    d = BASE_DIR / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_path(user_id: int, filename: str) -> Path:
    """Prevent path traversal attacks."""
    filename = filename.lstrip("/\\").replace("..", "")
    path = (_user_dir(user_id) / filename).resolve()
    if not str(path).startswith(str(_user_dir(user_id).resolve())):
        raise ValueError("مسار غير مسموح")
    return path


def read_file(user_id: int, filename: str) -> str:
    try:
        path = _safe_path(user_id, filename)
        if not path.exists():
            return f"الملف '{filename}' غير موجود."
        if path.stat().st_size > 500_000:
            return "الملف كبير جداً (الحد الأقصى 500KB)."
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"خطأ في القراءة: {e}"


def write_file(user_id: int, filename: str, content: str) -> str:
    try:
        path = _safe_path(user_id, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"تم حفظ الملف '{filename}' بنجاح ({len(content)} حرف)."
    except Exception as e:
        return f"خطأ في الكتابة: {e}"


def list_files(user_id: int) -> str:
    try:
        d = _user_dir(user_id)
        files = sorted(d.rglob("*"))
        files = [f for f in files if f.is_file()]
        if not files:
            return "لا توجد ملفات محفوظة."
        lines = []
        for f in files:
            rel = f.relative_to(d)
            size = f.stat().st_size
            lines.append(f"- {rel} ({size} بايت)")
        return "الملفات المتاحة:\n" + "\n".join(lines)
    except Exception as e:
        return f"خطأ: {e}"


def delete_file(user_id: int, filename: str) -> str:
    try:
        path = _safe_path(user_id, filename)
        if not path.exists():
            return f"الملف '{filename}' غير موجود."
        path.unlink()
        return f"تم حذف '{filename}'."
    except Exception as e:
        return f"خطأ في الحذف: {e}"
