"""Tests for slack_client module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from src.slack_client import SlackClient
from src.models import Paper, TeaserFigure


class TestSlackClient:
    """Tests for SlackClient class."""
    
    @pytest.fixture
    def slack_client(self, sample_config, mock_slack_client):
        """Create SlackClient with mocked Slack SDK client."""
        with patch('src.slack_client.WebClient', return_value=mock_slack_client):
            client = SlackClient("test-token", "C0123456789", sample_config)
            client.client = mock_slack_client
            return client
    
    def test_test_connection_success(self, slack_client, mock_slack_client):
        """Test successful Slack connection."""
        result = slack_client.test_connection()
        
        assert result is True
        mock_slack_client.auth_test.assert_called_once()
    
    def test_test_connection_failure(self, slack_client, mock_slack_client):
        """Test failed Slack connection."""
        from slack_sdk.errors import SlackApiError
        mock_slack_client.auth_test.side_effect = SlackApiError("error", {"error": "invalid_auth"})
        
        result = slack_client.test_connection()
        
        assert result is False
    
    def test_post_main_message(self, slack_client, mock_slack_client, sample_paper):
        """Test posting main message."""
        thread_ts = slack_client._post_main_message(sample_paper)
        
        assert thread_ts == "1234567890.123456"
        mock_slack_client.chat_postMessage.assert_called_once()
        
        # Check call arguments
        call_args = mock_slack_client.chat_postMessage.call_args
        assert call_args[1]['channel'] == "C0123456789"
        assert 'blocks' in call_args[1]
        assert 'text' in call_args[1]
    
    def test_post_main_message_with_translated_abstract(self, slack_client, 
                                                        mock_slack_client, sample_paper):
        """Test posting main message with translated abstract."""
        sample_paper.translated_abstract = "これは翻訳されたAbstractです。"
        
        thread_ts = slack_client._post_main_message(sample_paper)
        
        assert thread_ts is not None
        call_args = mock_slack_client.chat_postMessage.call_args
        blocks = call_args[1]['blocks']
        
        # Check that translated abstract is in blocks
        abstract_block = [b for b in blocks if b['type'] == 'section' 
                         and 'Abstract' in b['text']['text']]
        assert len(abstract_block) > 0
    
    def test_post_summaries(self, slack_client, mock_slack_client):
        """Test posting summaries in thread."""
        thread_ts = "1234567890.123456"
        summaries = {
            "どんなもの？": "テスト要約1",
            "先行研究と比べてどこがすごい？": "テスト要約2"
        }
        
        slack_client._post_summaries(thread_ts, summaries)
        
        assert mock_slack_client.chat_postMessage.call_count == 2
        
        # Check that all summaries were posted
        for call in mock_slack_client.chat_postMessage.call_args_list:
            assert call[1]['thread_ts'] == thread_ts
            assert call[1]['channel'] == "C0123456789"
    
    def test_post_teaser_figures_with_local_file(self, slack_client, 
                                                  mock_slack_client, temp_dir):
        """Test posting teaser figures with local files."""
        thread_ts = "1234567890.123456"
        
        # Create a temporary image file
        img_path = temp_dir / "test_fig.png"
        img_path.write_bytes(b"fake image data")
        
        figures = [
            TeaserFigure(
                image_url="https://example.com/fig1.png",
                caption="Figure 1: Test figure",
                local_path=str(img_path)
            )
        ]
        
        slack_client._post_teaser_figures(thread_ts, figures)
        
        mock_slack_client.files_upload_v2.assert_called_once()
        call_args = mock_slack_client.files_upload_v2.call_args
        assert call_args[1]['thread_ts'] == thread_ts
        assert call_args[1]['file'] == str(img_path)
    
    def test_post_teaser_figures_without_local_file(self, slack_client, mock_slack_client):
        """Test posting teaser figures without local files."""
        thread_ts = "1234567890.123456"
        
        figures = [
            TeaserFigure(
                image_url="https://example.com/fig1.png",
                caption="Figure 1: Test figure"
            )
        ]
        
        slack_client._post_teaser_figures(thread_ts, figures)
        
        # Should post as text message instead of file upload
        mock_slack_client.chat_postMessage.assert_called_once()
        call_args = mock_slack_client.chat_postMessage.call_args
        assert "https://example.com/fig1.png" in call_args[1]['text']
    
    @patch.object(SlackClient, '_post_main_message')
    @patch.object(SlackClient, '_post_summaries')
    @patch.object(SlackClient, '_post_teaser_figures')
    def test_post_paper_complete(self, mock_post_figures, mock_post_summaries,
                                 mock_post_main, slack_client, sample_paper):
        """Test posting a complete paper."""
        mock_post_main.return_value = "1234567890.123456"
        sample_paper.summaries = {"どんなもの？": "要約"}
        
        result = slack_client.post_paper(sample_paper)
        
        assert result is True
        mock_post_main.assert_called_once_with(sample_paper)
        mock_post_summaries.assert_called_once()
        mock_post_figures.assert_called_once()
    
    @patch.object(SlackClient, '_post_main_message')
    def test_post_paper_failure(self, mock_post_main, slack_client, sample_paper):
        """Test posting paper with failure."""
        mock_post_main.return_value = None
        
        result = slack_client.post_paper(sample_paper)
        
        assert result is False
    
    def test_post_paper_with_config_filters(self, sample_config, mock_slack_client, sample_paper):
        """Test posting paper with config filters."""
        # Disable some post elements
        sample_config.slack.post_elements.authors = False
        sample_config.slack.post_elements.github_url = False
        
        with patch('src.slack_client.WebClient', return_value=mock_slack_client):
            client = SlackClient("test-token", "C0123456789", sample_config)
            client.client = mock_slack_client
            
            client._post_main_message(sample_paper)
            
            call_args = mock_slack_client.chat_postMessage.call_args
            blocks = call_args[1]['blocks']
            
            # Authors should not be in blocks
            author_blocks = [b for b in blocks if b['type'] == 'section' 
                           and 'Authors' in b['text']['text']]
            assert len(author_blocks) == 0
