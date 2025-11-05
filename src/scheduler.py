"""Task scheduler for automated paper checking."""

import logging
from typing import Callable
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from .models import Config

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Scheduler for periodic paper checking."""
    
    def __init__(self, config: Config):
        """
        Initialize scheduler.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.scheduler = BlockingScheduler()
    
    def schedule_task(self, task_func: Callable, task_name: str = "check_papers"):
        """
        Schedule a task based on configuration.
        
        Args:
            task_func: Function to execute
            task_name: Name of the task
        """
        # Parse check time
        hour, minute = self._parse_time(self.config.schedule.check_time)
        
        # Create cron trigger
        if self.config.schedule.weekdays_only:
            # Monday to Friday (0-4 in Python's cron, where Monday=0)
            trigger = CronTrigger(
                day_of_week='mon-fri',
                hour=hour,
                minute=minute
            )
            logger.info(f"Scheduled task '{task_name}' for weekdays at {hour:02d}:{minute:02d}")
        else:
            # Every day
            trigger = CronTrigger(
                hour=hour,
                minute=minute
            )
            logger.info(f"Scheduled task '{task_name}' for every day at {hour:02d}:{minute:02d}")
        
        # Add job to scheduler
        self.scheduler.add_job(
            task_func,
            trigger=trigger,
            id=task_name,
            name=task_name,
            replace_existing=True
        )
    
    def start(self):
        """Start the scheduler."""
        logger.info("Starting scheduler...")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped by user")
            self.shutdown()
    
    def shutdown(self):
        """Shutdown the scheduler."""
        logger.info("Shutting down scheduler...")
        self.scheduler.shutdown()
    
    def _parse_time(self, time_str: str) -> tuple[int, int]:
        """
        Parse time string in HH:MM format.
        
        Args:
            time_str: Time string (e.g., "12:00")
        
        Returns:
            Tuple of (hour, minute)
        """
        try:
            parts = time_str.split(':')
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time range")
            
            return hour, minute
        except Exception as e:
            logger.error(f"Invalid time format '{time_str}': {e}")
            logger.info("Using default time 12:00")
            return 12, 0
