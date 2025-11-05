"""Data models for Scholar Inbox papers."""

from typing import Optional, List
from pydantic import BaseModel, Field


class TeaserFigure(BaseModel):
    """Teaser figure with image and caption."""
    
    image_url: str = Field(..., description="URL of the teaser figure image")
    caption: str = Field(..., description="Caption text for the figure")
    local_path: Optional[str] = Field(None, description="Local file path after download")


class PaperRelevance(BaseModel):
    """Paper relevance scores from Scholar Inbox."""
    
    relevance_score: int = Field(0, description="Relevance score")
    thumbs_up: int = Field(0, description="Number of thumbs up")
    read_by: int = Field(0, description="Number of users who read this paper")
    category: str = Field("", description="Primary category")


class Paper(BaseModel):
    """Complete paper information from Scholar Inbox."""
    
    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(default_factory=list, description="List of authors")
    abstract: str = Field("", description="Paper abstract")
    arxiv_id: Optional[str] = Field(None, description="arXiv ID (e.g., '2301.12345')")
    arxiv_url: Optional[str] = Field(None, description="arXiv page URL")
    arxiv_html_url: Optional[str] = Field(None, description="arXiv HTML version URL")
    github_url: Optional[str] = Field(None, description="GitHub repository URL")
    conference: Optional[str] = Field(None, description="Conference or journal name")
    submitted_date: Optional[str] = Field(None, description="Submission date")
    categories: List[str] = Field(default_factory=list, description="arXiv categories")
    paper_relevance: Optional[PaperRelevance] = Field(None, description="Relevance scores")
    teaser_figures: List[TeaserFigure] = Field(default_factory=list, description="Teaser figures")
    
    # LLM-generated content
    translated_abstract: Optional[str] = Field(None, description="Translated abstract")
    summaries: dict[str, str] = Field(default_factory=dict, description="Section summaries")


class Config(BaseModel):
    """Application configuration."""
    
    language: str = Field("ja", description="Target language for translation")
    cache_dir: str = Field("data/cache", description="Directory for caching downloaded images")
    
    class LLMConfig(BaseModel):
        provider: str = Field("openai", description="LLM provider (openai, anthropic, google)")
        model: str = Field("gpt-4", description="Specific model name")
        temperature: float = Field(0.3, description="Temperature for LLM generation")
    
    llm: LLMConfig = Field(default_factory=LLMConfig)
    
    class DateRangeConfig(BaseModel):
        max_days: int = Field(30, description="Maximum days in a date range")
    
    date_range: DateRangeConfig = Field(default_factory=DateRangeConfig)
    
    class Schedule(BaseModel):
        check_time: str = Field("12:00", description="Daily check time (HH:MM)")
        weekdays_only: bool = Field(True, description="Run only on weekdays")
    
    schedule: Schedule = Field(default_factory=Schedule)
    
    class SlackConfig(BaseModel):
        class PostElements(BaseModel):
            title: bool = True
            authors: bool = True
            abstract: bool = True
            paper_relevance: bool = True
            conference: bool = True
            submitted_date: bool = True
            categories: bool = True
            arxiv_url: bool = True
            github_url: bool = True
            teaser_figures: bool = True
        
        post_elements: PostElements = Field(default_factory=PostElements)
    
    slack: SlackConfig = Field(default_factory=SlackConfig)
    
    class SummaryConfig(BaseModel):
        max_length: int = Field(300, description="Maximum length per summary section")
        custom_instructions: str = Field("", description="Custom instructions for LLM")
        
        class SummarySection(BaseModel):
            name: str
            prompt: str
        
        sections: List[SummarySection] = Field(default_factory=list)
    
    summary: SummaryConfig = Field(default_factory=SummaryConfig)
    
    class ArxivConfig(BaseModel):
        prefer_html: bool = Field(True, description="Prefer HTML version over PDF")
        fallback_to_pdf: bool = Field(True, description="Fallback to PDF if HTML not available")
    
    arxiv: ArxivConfig = Field(default_factory=ArxivConfig)
    
    class FilterConfig(BaseModel):
        set_threshold: bool = Field(False, description="Enable relevance threshold filtering")
        relevance_threshold: int = Field(0, description="Relevance score threshold (can be negative, 0 means no filtering when set_threshold is true)")
        require_github: bool = Field(False, description="Only include papers with GitHub links")
    
    filter: FilterConfig = Field(default_factory=FilterConfig)
    
    class SortingConfig(BaseModel):
        order: str = Field("relevance_desc", description="Sort order for papers (relevance_desc, relevance_asc, date_desc, date_asc, dom_order)")
    
    sorting: SortingConfig = Field(default_factory=SortingConfig)
