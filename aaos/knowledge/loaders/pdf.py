from pathlib import Path


def load_pdf(path: str | Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise ImportError("Install pypdf to load PDF files: pip install pypdf") from e

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        if t.strip():
            parts.append(t)
    return "\n\n".join(parts)
