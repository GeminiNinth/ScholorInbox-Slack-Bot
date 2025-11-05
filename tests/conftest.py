"""Pytest configuration and fixtures."""

import pytest
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock
import tempfile
import yaml

from src.models import Paper, TeaserFigure, PaperRelevance, Config
from src.config import ConfigManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_dict():
    """Sample configuration dictionary."""
    return {
        "language": "ja",
        "date_range": {
            "max_days": 30
        },
        "schedule": {
            "check_time": "12:00",
            "weekdays_only": True
        },
        "slack": {
            "post_elements": {
                "title": True,
                "authors": True,
                "abstract": True,
                "paper_relevance": True,
                "arxiv_url": True,
                "github_url": True,
                "teaser_figures": True
            }
        },
        "summary": {
            "max_length": 300,
            "custom_instructions": "Test instructions",
            "sections": [
                {
                    "name": "どんなもの？",
                    "prompt": "What is this paper about?"
                }
            ]
        },
        "arxiv": {
            "prefer_html": True,
            "fallback_to_pdf": True
        }
    }


@pytest.fixture
def sample_config(sample_config_dict):
    """Sample Config object."""
    return Config(**sample_config_dict)


@pytest.fixture
def config_file(temp_dir, sample_config_dict):
    """Create a temporary config.yaml file."""
    config_path = temp_dir / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(sample_config_dict, f)
    return config_path


@pytest.fixture
def env_file(temp_dir):
    """Create a temporary .env file."""
    env_path = temp_dir / ".env"
    with open(env_path, 'w') as f:
        f.write("SCHOLAR_INBOX_SECRET_URL=https://scholar-inbox.com/login/test123\n")
        f.write("SLACK_BOT_TOKEN=xoxb-test-token\n")
        f.write("SLACK_CHANNEL_ID=C0123456789\n")
        f.write("OPENAI_API_KEY=sk-test-key\n")
    return env_path


@pytest.fixture
def sample_paper():
    """Sample Paper object."""
    return Paper(
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
        abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
        arxiv_id="1706.03762",
        arxiv_url="https://arxiv.org/abs/1706.03762",
        arxiv_html_url="https://arxiv.org/html/1706.03762",
        github_url="https://github.com/tensorflow/tensor2tensor",
        conference="NeurIPS 2017",
        submitted_date="2017-06-12",
        categories=["cs.CL", "cs.LG"],
        paper_relevance=PaperRelevance(
            thumbs_up=64,
            thumbs_down=21,
            score=8,
            category="Machine Learning"
        ),
        teaser_figures=[
            TeaserFigure(
                image_url="https://example.com/fig1.png",
                caption="Figure 1: The Transformer model architecture.",
                local_path="/tmp/fig1.png"
            )
        ]
    )


@pytest.fixture
def sample_papers(sample_paper):
    """List of sample Paper objects."""
    paper2 = Paper(
        title="BERT: Pre-training of Deep Bidirectional Transformers",
        authors=["Jacob Devlin", "Ming-Wei Chang"],
        abstract="We introduce a new language representation model called BERT.",
        arxiv_id="1810.04805",
        arxiv_url="https://arxiv.org/abs/1810.04805",
        arxiv_html_url="https://arxiv.org/html/1810.04805",
        categories=["cs.CL"]
    )
    return [sample_paper, paper2]


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Translated text"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_slack_client():
    """Mock Slack client."""
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.123456"}
    mock_client.files_upload_v2.return_value = {"ok": True}
    mock_client.auth_test.return_value = {"user": "test_bot"}
    return mock_client


@pytest.fixture
def mock_playwright_page():
    """Mock Playwright page."""
    mock_page = Mock()
    mock_page.content.return_value = "<html><body>Test content</body></html>"
    mock_page.locator.return_value.all.return_value = []
    return mock_page


@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment variables after each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)
