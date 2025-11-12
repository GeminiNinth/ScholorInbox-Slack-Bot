"""Task scheduler for automated paper checking."""

import logging
from datetime import datetime
from typing import Callable, Optional
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from .models import Config

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Scheduler for periodic paper checking."""
    
    def __init__(self, schedule_config: Config.Schedule):
        """
        Initialize scheduler.
        
        Args:
            schedule_config: Schedule configuration
        """
        self.schedule_config = schedule_config
        self.scheduler = BlockingScheduler()
        self.trigger: Optional[CronTrigger] = None
    
    def schedule_task(self, task_func: Callable, task_name: str = "check_papers"):
        """
        Schedule a task based on configuration.
        
        Args:
            task_func: Function to execute
            task_name: Name of the task
        """
        # Parse check time
        hour, minute = self._parse_time(self.schedule_config.check_time)
        
        # Create cron trigger
        if self.schedule_config.weekdays_only:
            # Monday to Friday (0-4 in Python's cron, where Monday=0)
            self.trigger = CronTrigger(
                day_of_week='mon-fri',
                hour=hour,
                minute=minute
            )
            logger.info(f"Scheduled task '{task_name}' for weekdays at {hour:02d}:{minute:02d}")
        else:
            # Every day
            self.trigger = CronTrigger(
                hour=hour,
                minute=minute
            )
            logger.info(f"Scheduled task '{task_name}' for every day at {hour:02d}:{minute:02d}")
        
        # Add job to scheduler
        self.scheduler.add_job(
            task_func,
            trigger=self.trigger,
            id=task_name,
            name=task_name,
            replace_existing=True
        )
    
    def start(self):
        """Start the scheduler."""
        logger.info("Starting scheduler...")
        
        # Log next run time using trigger before scheduler starts
        jobs = self.scheduler.get_jobs()
        if jobs:
            if self.trigger:
                try:
                    next_run = self.trigger.get_next_fire_time(None, datetime.now())
                    if next_run:
                        logger.info(f"Scheduler started successfully. Next run scheduled for: {next_run}")
                    else:
                        logger.warning("Could not determine next run time from trigger")
                except Exception as e:
                    logger.warning(f"Could not calculate next run time: {e}")
            else:
                logger.info(f"Scheduled {len(jobs)} job(s)")
        else:
            logger.warning("No jobs scheduled. Scheduler will start but no tasks will run.")
        
        logger.info("Scheduler is now running and waiting for scheduled tasks...")
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
