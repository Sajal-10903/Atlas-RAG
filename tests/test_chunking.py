from app.services.chunking import chunk
from app.services.extraction import ExtractedPage


def test_chunking_preserves_page_and_overlap():
    source = "alpha " * 200
    chunks = chunk([ExtractedPage(source, 3)], size=100, overlap=20)
    assert len(chunks) > 2
    assert all(item.page == 3 for item in chunks)
    assert chunks[0].content[-10:] in chunks[1].content


def test_chunking_discards_empty_pages():
    assert chunk([ExtractedPage("   ", 1)]) == []

