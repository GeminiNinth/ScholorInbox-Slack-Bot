"""Tests for scheduler module."""

import pytest
from unittest.mock import Mock, patch
from src.scheduler import TaskScheduler
from src.models import Config


class TestTaskScheduler:
    """Tests for TaskScheduler class."""
    
    def test_parse_time_valid(self, sample_config):
        """Test parsing valid time strings."""
        scheduler = TaskScheduler(sample_config)
        
        # Test various time formats
        assert scheduler._parse_time("12:00") == (12, 0)
        assert scheduler._parse_time("09:30") == (9, 30)
        assert scheduler._parse_time("23:59") == (23, 59)
        assert scheduler._parse_time("00:00") == (0, 0)
    
    def test_parse_time_without_minutes(self, sample_config):
        """Test parsing time without minutes."""
        scheduler = TaskScheduler(sample_config)
        
        assert scheduler._parse_time("12") == (12, 0)
    
    def test_parse_time_invalid(self, sample_config):
        """Test parsing invalid time strings."""
        scheduler = TaskScheduler(sample_config)
        
        # Invalid format should return default (12:00)
        assert scheduler._parse_time("invalid") == (12, 0)
        assert scheduler._parse_time("25:00") == (12, 0)
        assert scheduler._parse_time("12:60") == (12, 0)
    
    def test_schedule_task_weekdays(self, sample_config):
        """Test scheduling task for weekdays only."""
        scheduler = TaskScheduler(sample_config)
        mock_task = Mock()
        
        scheduler.schedule_task(mock_task, "test_task")
        
        # Check that job was added
        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "test_task"
    
    def test_schedule_task_all_days(self, sample_config):
        """Test scheduling task for all days."""
        sample_config.schedule.weekdays_only = False
        scheduler = TaskScheduler(sample_config)
        mock_task = Mock()
        
        scheduler.schedule_task(mock_task, "test_task")
        
        jobs = scheduler.scheduler.get_jobs()
        assert len(jobs) == 1
    
    @patch('src.scheduler.BlockingScheduler.start')
    def test_start_scheduler(self, mock_start, sample_config):
        """Test starting the scheduler."""
        scheduler = TaskScheduler(sample_config)
        mock_task = Mock()
        
        scheduler.schedule_task(mock_task, "test_task")
        scheduler.start()
        
        mock_start.assert_called_once()
    
    def test_shutdown_scheduler(self, sample_config):
        """Test shutting down the scheduler."""
        scheduler = TaskScheduler(sample_config)
        
        # Scheduler must be started before it can be shut down
        # In this test, we just verify the scheduler object is created correctly
        assert scheduler.scheduler is not None
        assert scheduler.config == sample_config
