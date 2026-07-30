from pathlib import Path


def load_docx(path: str | Path) -> str:
    try:
        from docx import Document
    except ImportError as e:
        raise ImportError(
            "Install python-docx to load DOCX files: pip install python-docx"
        ) from e

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
