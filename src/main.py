"""
Main application entry point with filtering and cost tracking.
"""

import sys
import logging
from pathlib import Path
from typing import Optional


if __package__ in (None, ""):
    # Allow running as a standalone script: `python src/main.py`
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent

    for candidate in (current_dir, parent_dir):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)

    from config import ConfigManager  # type: ignore
    from scraper import ScholarInboxScraper  # type: ignore
    from llm_client import LLMClient  # type: ignore
    from slack_client import SlackClient  # type: ignore
    from scheduler import TaskScheduler  # type: ignore
    from date_utils import DateParser, DateRange, build_scholar_inbox_url  # type: ignore
else:
    from .config import ConfigManager
    from .scraper import ScholarInboxScraper
    from .llm_client import LLMClient
    from .slack_client import SlackClient
    from .scheduler import TaskScheduler
    from .date_utils import DateParser, DateRange, build_scholar_inbox_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scholar_inbox_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class ScholarInboxBot:
    """Main bot application with filtering and cost tracking."""
    
    def __init__(self, config_path: str = "config.yaml", env_path: str = ".env"):
        """Initialize the bot."""
        logger.info("Initializing Scholar Inbox Bot...")
        
        # Load configuration
        self.config_manager = ConfigManager(config_path, env_path)
        self.config = self.config_manager.get_config()
        
        # Initialize components
        cache_dir = Path(self.config.cache_dir)
        self.scraper = ScholarInboxScraper(cache_dir)
        self.llm_client = LLMClient(self.config)
        self.slack_client = SlackClient(
            self.config_manager.get_slack_token(),
            self.config_manager.get_slack_channel_id(),
            self.config
        )
        
        logger.info("Bot initialized successfully")
    
    def check_and_post_papers(self, max_papers: Optional[int] = None, date_range: Optional[DateRange] = None):
        """Main workflow: scrape, filter, process, and post papers."""
        logger.info("=" * 80)
        logger.info("Starting paper check workflow")
        logger.info("=" * 80)
        
        try:
            # Get base URL
            base_url = self.config_manager.get_scholar_inbox_url()
            
            # Scrape papers
            if date_range:
                logger.info(f"Processing date range: {date_range}")
                all_papers = []
                
                for date in date_range.get_dates():
                    url = build_scholar_inbox_url(base_url, date)
                    logger.info(f"Fetching papers for {date.strftime('%Y-%m-%d')}...")
                    
                    try:
                        papers = self.scraper.scrape_papers(url, max_papers)
                        all_papers.extend(papers)
                        logger.info(f"Found {len(papers)} papers for {date.strftime('%Y-%m-%d')}")
                    except Exception as e:
                        logger.error(f"Error fetching papers for {date.strftime('%Y-%m-%d')}: {e}")
                        continue
                
                papers = all_papers
            else:
                url = base_url
                logger.info("Step 1: Scraping papers from Scholar Inbox...")
                papers = self.scraper.scrape_papers(url, max_papers)
            
            if not papers:
                logger.warning("No papers found")
                return
            
            logger.info(f"Found {len(papers)} papers")
            
            # Apply relevance filtering
            if self.config.filter.set_threshold:
                original_count = len(papers)
                papers = [p for p in papers if p.paper_relevance and p.paper_relevance.relevance_score >= self.config.filter.relevance_threshold]
                filtered_count = original_count - len(papers)
                if filtered_count > 0:
                    logger.info(f"Filtered out {filtered_count} papers below relevance threshold {self.config.filter.relevance_threshold}")
            
            if not papers:
                logger.warning("No papers remaining after filtering")
                return
            
            # Sort papers according to config
            papers = self._sort_papers(papers)
            logger.info(f"Sorted papers by: {self.config.sorting.order}")
            
            logger.info(f"Processing {len(papers)} papers...")
            logger.info("")
            
            # Process papers
            processed_count = 0
            for idx, paper in enumerate(papers, 1):
                try:
                    logger.info("=" * 80)
                    logger.info(f"Paper {idx}/{len(papers)}: {paper.title}")
                    if paper.paper_relevance:
                        logger.info(f"Relevance Score: {paper.paper_relevance.relevance_score}")
                    logger.info("=" * 80)
                    
                    # Reset cost tracker for this paper
                    self.llm_client.reset_cost_tracker()
                    
                    # Process with LLM
                    logger.info(f"Step 2.{idx}: Processing with LLM...")
                    paper = self.llm_client.process_paper_sync(paper)
                    
                    # Print cost for this paper
                    logger.info("")
                    logger.info(f"--- API Cost for Paper {idx} ---")
                    self.llm_client.print_paper_cost()
                    logger.info("")
                    
                    # Post to Slack
                    logger.info(f"Step 3.{idx}: Posting to Slack...")
                    success = self.slack_client.post_paper(paper)
                    
                    if success:
                        processed_count += 1
                        logger.info(f"✓ Successfully posted paper {idx}/{len(papers)}")
                    else:
                        logger.error(f"✗ Failed to post paper {idx}/{len(papers)}")
                    
                    logger.info("")
                
                except Exception as e:
                    logger.error(f"Error processing paper {idx}: {e}", exc_info=True)
                    continue
            
            # Cleanup cached images
            logger.info("=" * 80)
            logger.info("Cleaning up cached images...")
            self.scraper.cleanup_images(papers)
            
            # Print total cost summary
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"Workflow completed: {processed_count}/{len(papers)} papers posted")
            logger.info("=" * 80)
            logger.info("")
            
            self.llm_client.print_total_cost_summary()
        
        except Exception as e:
            logger.error(f"Workflow failed: {e}", exc_info=True)
            raise
    
    def _sort_papers(self, papers):
        """Sort papers according to configuration."""
        from datetime import datetime
        
        sort_order = self.config.sorting.order
        
        if sort_order == "relevance_desc":
            # Sort by relevance score (highest first)
            return sorted(
                papers,
                key=lambda p: p.paper_relevance.relevance_score if p.paper_relevance else -999999,
                reverse=True
            )
        elif sort_order == "relevance_asc":
            # Sort by relevance score (lowest first)
            return sorted(
                papers,
                key=lambda p: p.paper_relevance.relevance_score if p.paper_relevance else -999999,
                reverse=False
            )
        elif sort_order == "date_desc":
            # Sort by submission date (newest first)
            def get_date_key(paper):
                if not paper.submitted_date:
                    return datetime.min
                try:
                    # Try parsing common date formats
                    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]:
                        try:
                            return datetime.strptime(paper.submitted_date, fmt)
                        except ValueError:
                            continue
                    return datetime.min
                except:
                    return datetime.min
            
            return sorted(papers, key=get_date_key, reverse=True)
        elif sort_order == "date_asc":
            # Sort by submission date (oldest first)
            def get_date_key(paper):
                if not paper.submitted_date:
                    return datetime.min
                try:
                    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]:
                        try:
                            return datetime.strptime(paper.submitted_date, fmt)
                        except ValueError:
                            continue
                    return datetime.min
                except:
                    return datetime.min
            
            return sorted(papers, key=get_date_key, reverse=False)
        elif sort_order == "dom_order":
            # Preserve DOM order (no sorting)
            return papers
        else:
            logger.warning(f"Unknown sort order '{sort_order}', using default (relevance_desc)")
            return sorted(
                papers,
                key=lambda p: p.paper_relevance.relevance_score if p.paper_relevance else -999999,
                reverse=True
            )


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scholar Inbox Slack Bot")
    parser.add_argument("--mode", choices=["once", "scheduled"], default="once",
                        help="Run mode: once (one-time) or scheduled (continuous)")
    parser.add_argument("--max-papers", type=int, default=None,
                        help="Maximum number of papers to process")
    parser.add_argument("--date", type=str, default=None,
                        help="Date or date range (e.g., '2025-10-31' or '2025-10-31 to 2025-11-02')")
    parser.add_argument("--config", type=str, default="config.yaml",
                        help="Path to config file")
    parser.add_argument("--env", type=str, default=".env",
                        help="Path to .env file")
    
    args = parser.parse_args()
    
    try:
        # Initialize bot
        bot = ScholarInboxBot(args.config, args.env)
        
        # Parse date if provided
        date_range = None
        if args.date:
            date_range = DateParser.parse_date_range(args.date)
            # Validate date range
            is_valid, warning = DateParser.validate_date_range(
                date_range, 
                bot.config.date_range.max_days
            )
            if warning:
                logger.warning(warning)
            if not is_valid:
                logger.error("Invalid date range. Please check your input.")
                sys.exit(1)
        
        if args.mode == "once":
            # Run once
            logger.info("Running in one-time mode")
            bot.check_and_post_papers(args.max_papers, date_range)
        else:
            # Run scheduled
            logger.info("Running in scheduled mode")
            scheduler = TaskScheduler(bot.config.schedule)
            
            def scheduled_task():
                bot.check_and_post_papers()
            
            scheduler.start(scheduled_task)
    
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
