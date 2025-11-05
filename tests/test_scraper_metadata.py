"""Tests for ScholarInboxScraper metadata enrichment."""

from unittest.mock import MagicMock

from src.scraper import ScholarInboxScraper


def test_scraper_enriches_paper_with_arxiv_metadata(temp_dir):
    scraper = ScholarInboxScraper(temp_dir)
    scraper._extract_abstract_for_arxiv = MagicMock(return_value="Scraped abstract")
    scraper._extract_teaser_figures_for_arxiv = MagicMock(return_value=[])

    scraper.arxiv_client.fetch_paper_metadata_sync = MagicMock(return_value={
        "title": "API Title",
        "authors": ["API Author"],
        "abstract": "API Abstract",
        "categories": ["cs.AI"],
        "published": "2025-01-01",
        "updated": "2025-01-05",
        "abs_url": "https://arxiv.org/abs/1234.5678",
    })

    page = MagicMock()
    paper_data = {
        "titleLink": "Scraped Title",
        "authorsLink": "Scraped Author",
        "arxivId": "1234.5678",
        "href": "https://scholar-inbox.com/paper/1234",
        "metadata": {},
    }

    paper = scraper._extract_paper_full_info(page, paper_data, 1)

    assert paper.title == "API Title"
    assert paper.authors == ["API Author"]
    assert paper.abstract == "API Abstract"
    assert paper.arxiv_id == "1234.5678"
    assert paper.arxiv_url == "https://arxiv.org/abs/1234.5678"
    assert paper.categories == ["cs.AI"]
    assert paper.submitted_date == "2025-01-01"


def test_scraper_skips_arxiv_metadata_when_id_missing(temp_dir):
    scraper = ScholarInboxScraper(temp_dir)
    scraper._extract_abstract_for_arxiv = MagicMock(return_value="")
    scraper._extract_teaser_figures_for_arxiv = MagicMock(return_value=[])
    scraper.arxiv_client.fetch_paper_metadata_sync = MagicMock()

    page = MagicMock()
    paper_data = {
        "titleLink": "Non Arxiv Paper",
        "authorsLink": "Author One",
        "href": "https://scholar-inbox.com/paper/non-arxiv",
        "metadata": {},
    }

    paper = scraper._extract_paper_full_info(page, paper_data, 1)

    assert paper.title == "Non Arxiv Paper"
    assert paper.arxiv_id is None
    assert paper.abstract == ""
    scraper.arxiv_client.fetch_paper_metadata_sync.assert_not_called()

