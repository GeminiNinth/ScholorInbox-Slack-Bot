"""Tests for models module."""

import pytest
from src.models import Paper, TeaserFigure, PaperRelevance, Config


class TestTeaserFigure:
    """Tests for TeaserFigure model."""
    
    def test_create_teaser_figure(self):
        """Test creating TeaserFigure."""
        fig = TeaserFigure(
            image_url="https://example.com/fig1.png",
            caption="Figure 1: Test figure"
        )
        
        assert fig.image_url == "https://example.com/fig1.png"
        assert fig.caption == "Figure 1: Test figure"
        assert fig.local_path is None
    
    def test_teaser_figure_with_local_path(self):
        """Test TeaserFigure with local path."""
        fig = TeaserFigure(
            image_url="https://example.com/fig1.png",
            caption="Figure 1",
            local_path="/tmp/fig1.png"
        )
        
        assert fig.local_path == "/tmp/fig1.png"


class TestPaperRelevance:
    """Tests for PaperRelevance model."""
    
    def test_create_paper_relevance(self):
        """Test creating PaperRelevance."""
        rel = PaperRelevance(
            thumbs_up=64,
            thumbs_down=21,
            score=8,
            category="Machine Learning"
        )
        
        assert rel.thumbs_up == 64
        assert rel.thumbs_down == 21
        assert rel.score == 8
        assert rel.category == "Machine Learning"
    
    def test_paper_relevance_defaults(self):
        """Test PaperRelevance with default values."""
        rel = PaperRelevance()
        
        assert rel.thumbs_up == 0
        assert rel.thumbs_down == 0
        assert rel.score == 0
        assert rel.category == ""


class TestPaper:
    """Tests for Paper model."""
    
    def test_create_minimal_paper(self):
        """Test creating Paper with minimal fields."""
        paper = Paper(title="Test Paper")
        
        assert paper.title == "Test Paper"
        assert paper.authors == []
        assert paper.abstract == ""
        assert paper.arxiv_id is None
        assert paper.teaser_figures == []
    
    def test_create_full_paper(self, sample_paper):
        """Test creating Paper with all fields."""
        assert sample_paper.title == "Attention Is All You Need"
        assert len(sample_paper.authors) == 3
        assert sample_paper.arxiv_id == "1706.03762"
        assert sample_paper.arxiv_url == "https://arxiv.org/abs/1706.03762"
        assert sample_paper.github_url == "https://github.com/tensorflow/tensor2tensor"
        assert sample_paper.conference == "NeurIPS 2017"
        assert len(sample_paper.categories) == 2
        assert sample_paper.paper_relevance is not None
        assert len(sample_paper.teaser_figures) == 1
    
    def test_paper_with_summaries(self, sample_paper):
        """Test Paper with LLM-generated summaries."""
        sample_paper.translated_abstract = "これはテスト論文です。"
        sample_paper.summaries = {
            "どんなもの？": "テスト要約1",
            "先行研究と比べてどこがすごい？": "テスト要約2"
        }
        
        assert sample_paper.translated_abstract == "これはテスト論文です。"
        assert len(sample_paper.summaries) == 2
        assert "どんなもの？" in sample_paper.summaries


class TestConfig:
    """Tests for Config model."""
    
    def test_config_structure(self, sample_config):
        """Test Config model structure."""
        assert hasattr(sample_config, 'language')
        assert hasattr(sample_config, 'date_range')
        assert hasattr(sample_config, 'schedule')
        assert hasattr(sample_config, 'slack')
        assert hasattr(sample_config, 'summary')
        assert hasattr(sample_config, 'arxiv')
    
    def test_config_nested_models(self, sample_config):
        """Test nested models in Config."""
        # DateRangeConfig
        assert sample_config.date_range.max_days == 30
        
        # Schedule
        assert sample_config.schedule.check_time == "12:00"
        assert sample_config.schedule.weekdays_only is True
        
        # SlackConfig
        assert sample_config.slack.post_elements.title is True
        
        # SummaryConfig
        assert sample_config.summary.max_length == 300
        assert len(sample_config.summary.sections) == 1
        
        # ArxivConfig
        assert sample_config.arxiv.prefer_html is True
