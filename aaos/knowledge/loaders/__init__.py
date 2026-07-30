from pathlib import Path

from aaos.knowledge.loaders.txt import load_txt
from aaos.knowledge.loaders.pdf import load_pdf
from aaos.knowledge.loaders.docx_loader import load_docx

TEXT_EXT = {".txt", ".md", ".markdown", ".csv", ".log", ".py", ".json", ".html", ".xml"}


def load_document(path: str | Path) -> str:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    ext = path.suffix.lower()
    if ext in TEXT_EXT:
        return load_txt(path)
    if ext == ".pdf":
        return load_pdf(path)
    if ext in {".docx"}:
        return load_docx(path)
    raise ValueError(f"Unsupported document type: {ext}")


__all__ = ["load_document", "load_txt", "load_pdf", "load_docx", "TEXT_EXT"]
