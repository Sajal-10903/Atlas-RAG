from dataclasses import dataclass
from app.services.extraction import ExtractedPage


@dataclass
class ChunkText:
    content: str
    page: int | None


def chunk(pages: list[ExtractedPage], size: int = 1200, overlap: int = 180) -> list[ChunkText]:
    """Paragraph-aware chunks; character length keeps the pipeline tokenizer-neutral."""
    results: list[ChunkText] = []
    for page in pages:
        text = " ".join(page.text.split())
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                boundary = max(text.rfind(". ", start, end), text.rfind(" ", start, end))
                if boundary > start + size // 2:
                    end = boundary + 1
            results.append(ChunkText(text[start:end].strip(), page.page))
            if end == len(text):
                break
            start = max(end - overlap, start + 1)
    return results

