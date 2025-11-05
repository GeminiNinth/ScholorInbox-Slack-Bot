"""Integration tests for the Scholar Inbox Bot."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.main import ScholarInboxBot
from src.date_utils import DateRange


@pytest.mark.integration
class TestScholarInboxBotIntegration:
    """Integration tests for ScholarInboxBot."""
    
    @pytest.fixture
    def mock_dependencies(self, mock_openai_client, mock_slack_client, mock_playwright_page):
        """Mock all external dependencies."""
        import os
        
        # Set required environment variables
        os.environ["SCHOLAR_INBOX_SECRET_URL"] = "https://scholar-inbox.com/login/test"
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-test-token"
        os.environ["SLACK_CHANNEL_ID"] = "C0123456789"
        os.environ["OPENAI_API_KEY"] = "sk-test-key"
        
        with patch('src.scraper.ScholarInboxScraper') as mock_scraper, \
             patch('src.llm_client.LLMClient') as mock_llm, \
             patch('src.slack_client.SlackClient') as mock_slack:
            
            # Configure mocks
            mock_scraper_instance = Mock()
            mock_scraper.return_value = mock_scraper_instance
            
            mock_llm_instance = Mock()
            mock_llm.return_value = mock_llm_instance
            
            mock_slack_instance = Mock()
            mock_slack.return_value = mock_slack_instance
            
            yield {
                'scraper': mock_scraper_instance,
                'llm': mock_llm_instance,
                'slack': mock_slack_instance
            }
    
    def test_bot_initialization(self, mock_dependencies):
        """Test bot initialization with all components."""
        bot = ScholarInboxBot()
        
        assert bot.config_manager is not None
        assert bot.scraper is not None
        assert bot.llm_client is not None
        assert bot.slack_client is not None
    
    def test_workflow_with_papers(self, mock_dependencies, sample_papers):
        """Test complete workflow with papers."""
        # Setup mocks
        mock_dependencies['scraper'].scrape_papers.return_value = sample_papers
        
        def process_paper_side_effect(paper):
            paper.translated_abstract = "翻訳されたAbstract"
            paper.summaries = {"どんなもの？": "要約"}
            return paper
        
        mock_dependencies['llm'].process_paper.side_effect = process_paper_side_effect
        mock_dependencies['slack'].post_paper.return_value = True
        
        # Run workflow
        bot = ScholarInboxBot()
        bot.check_and_post_papers(max_papers=2)
        
        # Verify calls
        mock_dependencies['scraper'].scrape_papers.assert_called_once()
        assert mock_dependencies['llm'].process_paper.call_count == 2
        assert mock_dependencies['slack'].post_paper.call_count == 2
    
    def test_workflow_with_no_papers(self, mock_dependencies):
        """Test workflow when no papers are found."""
        mock_dependencies['scraper'].scrape_papers.return_value = []
        
        bot = ScholarInboxBot()
        bot.check_and_post_papers()
        
        # LLM and Slack should not be called
        mock_dependencies['llm'].process_paper.assert_not_called()
        mock_dependencies['slack'].post_paper.assert_not_called()
    
    def test_workflow_with_date_range(self, mock_dependencies, sample_papers):
        """Test workflow with date range."""
        mock_dependencies['scraper'].scrape_papers.return_value = sample_papers
        mock_dependencies['llm'].process_paper.return_value = sample_papers[0]
        mock_dependencies['slack'].post_paper.return_value = True
        
        # Create date range
        start = datetime(2025, 10, 31)
        end = datetime(2025, 11, 2)
        date_range = DateRange(start, end)
        
        bot = ScholarInboxBot()
        bot.check_and_post_papers(date_range=date_range)
        
        # Scraper should be called 3 times (one for each date)
        assert mock_dependencies['scraper'].scrape_papers.call_count == 3
    
    def test_workflow_with_llm_error(self, mock_dependencies, sample_papers):
        """Test workflow when LLM processing fails."""
        mock_dependencies['scraper'].scrape_papers.return_value = sample_papers
        mock_dependencies['llm'].process_paper.side_effect = Exception("LLM Error")
        
        bot = ScholarInboxBot()
        
        # Should not raise exception
        bot.check_and_post_papers()
        
        # Slack should not be called due to LLM error
        mock_dependencies['slack'].post_paper.assert_not_called()
    
    def test_workflow_with_slack_error(self, mock_dependencies, sample_papers):
        """Test workflow when Slack posting fails."""
        mock_dependencies['scraper'].scrape_papers.return_value = sample_papers
        mock_dependencies['llm'].process_paper.return_value = sample_papers[0]
        mock_dependencies['slack'].post_paper.side_effect = Exception("Slack Error")
        
        bot = ScholarInboxBot()
        
        # Should not raise exception
        bot.check_and_post_papers()
        
        # LLM should still be called
        mock_dependencies['llm'].process_paper.assert_called()


@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end workflow tests."""
    
    def test_date_range_validation_and_processing(self, temp_dir, config_file, env_file):
        """Test date range validation in the workflow."""
        from src.date_utils import DateParser
        from datetime import timedelta
        
        # Test valid date range
        start = datetime.now() - timedelta(days=5)
        end = datetime.now() - timedelta(days=1)
        date_range_str = f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"
        
        date_range = DateParser.parse_date_range(date_range_str)
        is_valid, warning = DateParser.validate_date_range(date_range, max_days=30)
        
        assert is_valid is True
        assert warning is None
        assert len(date_range) == 5
    
    def test_date_range_exceeds_limit(self):
        """Test date range that exceeds the limit."""
        from src.date_utils import DateParser
        
        start = datetime(2025, 1, 1)
        end = datetime(2025, 2, 15)  # 46 days
        date_range = DateRange(start, end)
        
        is_valid, warning = DateParser.validate_date_range(date_range, max_days=30)
        
        assert is_valid is False
        assert "exceeds the recommended maximum" in warning
        assert "46 days" in warning
