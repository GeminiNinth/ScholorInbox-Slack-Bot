"""Tests for arXiv client metadata retrieval."""

import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.arxiv_client import ArxivClient


def _build_mock_result():
    return SimpleNamespace(
        title=" Sample Title ",
        authors=[SimpleNamespace(name="Author One"), SimpleNamespace(name="Author Two")],
        summary=" Sample abstract text. ",
        published=datetime(2024, 1, 5),
        updated=datetime(2024, 1, 6),
        pdf_url="https://arxiv.org/pdf/1234.5678.pdf",
        entry_id="https://arxiv.org/abs/1234.5678",
        primary_category="cs.AI",
        categories=["cs.AI", "cs.LG"],
        comment="Comment",
        journal_ref="Journal Ref",
        doi="10.1000/example",
        get_short_id=lambda: "1234.5678",
    )


def _setup_mock_search(monkeypatch, mock_result):
    mock_search = MagicMock()
    mock_search.results.return_value = iter([mock_result])
    monkeypatch.setattr("src.arxiv_client.arxiv.Search", MagicMock(return_value=mock_search))


def _assert_metadata(metadata):
    assert metadata is not None
    assert metadata["title"] == "Sample Title"
    assert metadata["authors"] == ["Author One", "Author Two"]
    assert metadata["abstract"] == "Sample abstract text."
    assert metadata["published"] == "2024-01-05"
    assert metadata["updated"] == "2024-01-06"
    assert metadata["categories"] == ["cs.AI", "cs.LG"]
    assert metadata["abs_url"] == "https://arxiv.org/abs/1234.5678"
    assert metadata["arxiv_id"] == "1234.5678"


def test_fetch_paper_metadata_sync_returns_clean_metadata(monkeypatch):
    client = ArxivClient()
    mock_result = _build_mock_result()
    _setup_mock_search(monkeypatch, mock_result)

    metadata = client.fetch_paper_metadata_sync("1234.5678")
    _assert_metadata(metadata)


def test_fetch_paper_metadata_async_returns_clean_metadata(monkeypatch):
    client = ArxivClient()
    mock_result = _build_mock_result()
    _setup_mock_search(monkeypatch, mock_result)

    metadata = asyncio.run(client.fetch_paper_metadata("1234.5678"))
    _assert_metadata(metadata)

