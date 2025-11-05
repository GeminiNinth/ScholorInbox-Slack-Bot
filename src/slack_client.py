"""Slack client for posting paper summaries."""

import logging
from typing import Optional
from pathlib import Path
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from .models import Paper, Config

logger = logging.getLogger(__name__)


class SlackClient:
    """Client for posting to Slack."""
    
    def __init__(self, token: str, channel_id: str, config: Config):
        """
        Initialize Slack client.
        
        Args:
            token: Slack bot token
            channel_id: Target channel ID
            config: Application configuration
        """
        self.client = WebClient(token=token)
        self.channel_id = channel_id
        self.config = config
    
    def post_paper(self, paper: Paper) -> bool:
        """
        Post a paper to Slack as a thread.
        
        Args:
            paper: Paper object to post
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Posting paper to Slack: {paper.title[:50]}...")
            
            # Post main message
            thread_ts = self._post_main_message(paper)
            if not thread_ts:
                return False
            
            # Post summaries in thread
            if paper.summaries:
                self._post_summaries(thread_ts, paper.summaries)
            
            # Post teaser figures in thread
            if self.config.slack.post_elements.teaser_figures and paper.teaser_figures:
                self._post_teaser_figures(thread_ts, paper.teaser_figures)
            
            logger.info("Successfully posted paper to Slack")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post paper to Slack: {e}")
            return False
    
    def _post_main_message(self, paper: Paper) -> Optional[str]:
        """
        Post the main paper information.
        
        Returns:
            Thread timestamp if successful, None otherwise
        """
        try:
            # Build message blocks
            blocks = []
            
            # Title (link to abstract page)
            if self.config.slack.post_elements.title:
                title_text = f"*{paper.title}*"
                if paper.arxiv_id:
                    abs_url = f"https://arxiv.org/abs/{paper.arxiv_id}"
                    title_text = f"*<{abs_url}|{paper.title}>*"
                elif paper.arxiv_url:
                    title_text = f"*<{paper.arxiv_url}|{paper.title}>*"
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": title_text}
                })
            
            # Authors
            if self.config.slack.post_elements.authors and paper.authors:
                authors_text = ", ".join(paper.authors[:5])  # Limit to first 5 authors
                if len(paper.authors) > 5:
                    authors_text += f" et al. ({len(paper.authors)} authors)"
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"_Authors:_ {authors_text}"}
                })
            
            # Metadata
            metadata_parts = []
            if self.config.slack.post_elements.conference and paper.conference:
                metadata_parts.append(f"*Conference:* {paper.conference}")
            if self.config.slack.post_elements.submitted_date and paper.submitted_date:
                metadata_parts.append(f"*Submitted:* {paper.submitted_date}")
            
            # Relevance score
            if self.config.slack.post_elements.paper_relevance and paper.paper_relevance:
                rel = paper.paper_relevance
                relevance_text = f"*Relevance:* 📊 {rel.relevance_score}  👍 {rel.thumbs_up}  👤 {rel.read_by}"
                metadata_parts.append(relevance_text)
            
            if self.config.slack.post_elements.categories and paper.categories:
                cats = ", ".join(paper.categories[:3])
                metadata_parts.append(f"*Categories:* {cats}")
            
            if metadata_parts:
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "\n".join(metadata_parts)}
                })
            

            
            # URLs (PDF, HTML, GitHub)
            url_parts = []
            if self.config.slack.post_elements.arxiv_url and paper.arxiv_id:
                pdf_url = f"https://arxiv.org/pdf/{paper.arxiv_id}"
                url_parts.append(f"<{pdf_url}|PDF>")
            if paper.arxiv_html_url:
                url_parts.append(f"<{paper.arxiv_html_url}|HTML>")
            if self.config.slack.post_elements.github_url and paper.github_url:
                url_parts.append(f"<{paper.github_url}|GitHub>")
            
            if url_parts:
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "*Links:* " + " | ".join(url_parts)}
                })
            
            blocks.append({"type": "divider"})
            
            # Translated Abstract
            if self.config.slack.post_elements.abstract and paper.translated_abstract:
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Abstract:*\n{paper.translated_abstract}"}
                })
            
            # Post message
            response = self.client.chat_postMessage(
                channel=self.channel_id,
                blocks=blocks,
                text=f"New paper: {paper.title}"  # Fallback text
            )
            
            return response['ts']
            
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return None
    
    def _post_summaries(self, thread_ts: str, summaries: dict):
        """Post summaries as thread replies."""
        for section_name, summary in summaries.items():
            try:
                self.client.chat_postMessage(
                    channel=self.channel_id,
                    thread_ts=thread_ts,
                    text=f"*{section_name}*\n{summary}"
                )
            except SlackApiError as e:
                logger.error(f"Failed to post summary {section_name}: {e}")
    
    def _post_teaser_figures(self, thread_ts: str, figures: list):
        """Post teaser figures as thread replies."""
        # Remove duplicates by local_path or image_url
        seen_images = set()
        unique_figures = []
        
        for figure in figures:
            # Use local_path as primary identifier, fallback to image_url
            identifier = figure.local_path if figure.local_path else figure.image_url
            if identifier and identifier not in seen_images:
                seen_images.add(identifier)
                unique_figures.append(figure)
        
        logger.info(f"Posting {len(unique_figures)} unique figures (filtered from {len(figures)} total)")
        
        for idx, figure in enumerate(unique_figures):
            try:
                # Check if local file exists
                if figure.local_path and Path(figure.local_path).exists():
                    # Upload file with caption
                    caption_text = figure.caption if figure.caption else f"Figure {idx + 1}"
                    self.client.files_upload_v2(
                        channel=self.channel_id,
                        thread_ts=thread_ts,
                        file=figure.local_path,
                        title=caption_text[:100],  # Limit title length
                        initial_comment=caption_text
                    )
                    logger.debug(f"Posted figure {idx + 1}: {figure.local_path}")
                else:
                    # Post caption with image URL
                    self.client.chat_postMessage(
                        channel=self.channel_id,
                        thread_ts=thread_ts,
                        text=f"*Figure {idx + 1}*\n{figure.caption}\n{figure.image_url}"
                    )
                    logger.debug(f"Posted figure {idx + 1}: {figure.image_url}")
            except SlackApiError as e:
                logger.error(f"Failed to post figure {idx + 1}: {e}")
    
    def test_connection(self) -> bool:
        """
        Test Slack connection.
        
        Returns:
            True if connection is successful
        """
        try:
            response = self.client.auth_test()
            logger.info(f"Connected to Slack as {response['user']}")
            return True
        except SlackApiError as e:
            logger.error(f"Slack connection test failed: {e}")
            return False
