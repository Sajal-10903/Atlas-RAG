"""Safe, dependency-light document text extraction with page provenance."""
from dataclasses import dataclass
from pathlib import Path
import csv
from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pypdf import PdfReader


@dataclass
class ExtractedPage:
    text: str
    page: int | None


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".html", ".htm", ".csv"}


def extract(path: str) -> list[ExtractedPage]:
    file = Path(path)
    ext = file.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext or 'unknown'}")
    if ext == ".pdf":
        return [ExtractedPage(page.extract_text() or "", i + 1) for i, page in enumerate(PdfReader(path).pages)]
    if ext == ".docx":
        return [ExtractedPage("\n".join(p.text for p in DocxDocument(path).paragraphs), None)]
    if ext in {".html", ".htm"}:
        return [ExtractedPage(BeautifulSoup(file.read_text(encoding="utf-8", errors="replace"), "html.parser").get_text("\n"), None)]
    if ext == ".csv":
        with file.open(encoding="utf-8", errors="replace", newline="") as handle:
            return [ExtractedPage("\n".join(" | ".join(row) for row in csv.reader(handle)), None)]
    return [ExtractedPage(file.read_text(encoding="utf-8", errors="replace"), None)]

