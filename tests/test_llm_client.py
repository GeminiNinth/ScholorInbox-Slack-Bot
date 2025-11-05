"""Tests for llm_client module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.llm_client import LLMClient
from src.models import Paper


class TestLLMClient:
    """Tests for LLMClient class."""
    
    @pytest.fixture
    def llm_client(self, sample_config, mock_openai_client):
        """Create LLMClient with mocked OpenAI client."""
        with patch('src.llm_client.OpenAI', return_value=mock_openai_client):
            client = LLMClient(sample_config)
            client.client = mock_openai_client
            return client
    
    def test_translate_abstract(self, llm_client, mock_openai_client):
        """Test translating abstract."""
        abstract = "This is a test abstract."
        
        result = llm_client.translate_abstract(abstract)
        
        assert result == "Translated text"
        mock_openai_client.chat.completions.create.assert_called_once()
        
        # Check that the call was made with correct parameters
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]['model'] == 'gpt-4'
        assert len(call_args[1]['messages']) == 2
        # Check for Japanese in user prompt
        assert 'Japanese' in call_args[1]['messages'][1]['content']
    
    def test_translate_abstract_error(self, llm_client, mock_openai_client):
        """Test translating abstract with API error."""
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        abstract = "This is a test abstract."
        result = llm_client.translate_abstract(abstract)
        
        # Should return original abstract on error
        assert result == abstract
    
    def test_generate_section_summary(self, llm_client, mock_openai_client):
        """Test generating summary for a section."""
        content = "This is paper content."
        section_name = "どんなもの？"
        prompt = "What is this paper about?"
        
        result = llm_client._generate_section_summary(content, section_name, prompt)
        
        assert result == "Translated text"
        mock_openai_client.chat.completions.create.assert_called()
    
    @patch('src.llm_client.requests.get')
    def test_fetch_arxiv_html_success(self, mock_get, llm_client):
        """Test fetching arXiv HTML content."""
        mock_response = Mock()
        mock_response.url = "https://arxiv.org/html/1234.5678"
        mock_response.text = "<html><body><article>Paper content</article></body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        url = "https://arxiv.org/html/1234.5678"
        result = llm_client._fetch_arxiv_html(url)
        
        assert "Paper content" in result
        mock_get.assert_called_once_with(url, timeout=30)
    
    @patch('src.llm_client.requests.get')
    def test_fetch_arxiv_html_redirected_to_pdf(self, mock_get, llm_client):
        """Test fetching arXiv HTML when redirected to PDF."""
        mock_response = Mock()
        mock_response.url = "https://arxiv.org/pdf/1234.5678.pdf"
        mock_get.return_value = mock_response
        
        url = "https://arxiv.org/html/1234.5678"
        result = llm_client._fetch_arxiv_html(url)
        
        assert result == ""
    
    @patch('src.llm_client.requests.get')
    def test_fetch_arxiv_html_error(self, mock_get, llm_client):
        """Test fetching arXiv HTML with error."""
        mock_get.side_effect = Exception("Network error")
        
        url = "https://arxiv.org/html/1234.5678"
        result = llm_client._fetch_arxiv_html(url)
        
        assert result == ""
    
    def test_fetch_arxiv_content_no_arxiv_id(self, llm_client, sample_paper):
        """Test fetching content when paper has no arXiv ID."""
        sample_paper.arxiv_id = None
        
        result = llm_client._fetch_arxiv_content(sample_paper)
        
        assert result == ""
    
    @patch.object(LLMClient, '_fetch_arxiv_html')
    def test_fetch_arxiv_content_html_preferred(self, mock_fetch_html, llm_client, sample_paper):
        """Test fetching content with HTML preferred."""
        mock_fetch_html.return_value = "HTML content"
        
        result = llm_client._fetch_arxiv_content(sample_paper)
        
        assert result == "HTML content"
        mock_fetch_html.assert_called_once_with(sample_paper.arxiv_html_url)
    
    @patch.object(LLMClient, '_fetch_arxiv_html')
    def test_fetch_arxiv_content_html_failed(self, mock_fetch_html, llm_client, sample_paper):
        """Test fetching content when HTML fetch fails."""
        mock_fetch_html.return_value = ""
        
        result = llm_client._fetch_arxiv_content(sample_paper)
        
        # Should return abstract as fallback
        assert result == sample_paper.abstract
    
    @patch.object(LLMClient, 'translate_abstract')
    @patch.object(LLMClient, '_fetch_arxiv_content')
    @patch.object(LLMClient, 'generate_summaries')
    def test_process_paper(self, mock_gen_summaries, mock_fetch_content, 
                          mock_translate, llm_client, sample_paper):
        """Test processing a complete paper."""
        mock_translate.return_value = "翻訳されたAbstract"
        mock_fetch_content.return_value = "Paper content"
        mock_gen_summaries.return_value = {"どんなもの？": "要約"}
        
        result = llm_client.process_paper(sample_paper)
        
        assert result.translated_abstract == "翻訳されたAbstract"
        assert "どんなもの？" in result.summaries
        mock_translate.assert_called_once_with(sample_paper.abstract)
        mock_fetch_content.assert_called_once()
        mock_gen_summaries.assert_called_once_with("Paper content")
