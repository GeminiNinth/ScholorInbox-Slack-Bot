"""Tests for config module."""

import pytest
import os
from pathlib import Path
from src.config import ConfigManager
from src.models import Config


class TestConfigManager:
    """Tests for ConfigManager class."""
    
    def test_load_config_from_file(self, temp_dir, config_file, env_file):
        """Test loading configuration from files."""
        os.chdir(temp_dir)
        
        manager = ConfigManager(
            config_path=str(config_file),
            env_path=str(env_file)
        )
        
        assert manager.config.language == "ja"
        assert manager.config.schedule.check_time == "12:00"
        assert manager.get_scholar_inbox_url() == "https://scholar-inbox.com/login/test123"
        assert manager.get_slack_token() == "xoxb-test-token"
    
    def test_load_config_missing_file(self, temp_dir, env_file):
        """Test loading configuration with missing config file."""
        os.chdir(temp_dir)
        
        manager = ConfigManager(
            config_path="nonexistent.yaml",
            env_path=str(env_file)
        )
        
        # Should use default configuration
        assert isinstance(manager.config, Config)
        assert manager.config.language == "ja"
    
    def test_missing_env_vars(self, temp_dir, config_file):
        """Test with missing required environment variables."""
        os.chdir(temp_dir)
        
        # Create empty .env file
        env_path = temp_dir / ".env"
        env_path.touch()
        
        with pytest.raises(ValueError, match="Missing required environment variables"):
            ConfigManager(
                config_path=str(config_file),
                env_path=str(env_path)
            )
    
    def test_get_methods(self, temp_dir, config_file, env_file):
        """Test getter methods for environment variables."""
        os.chdir(temp_dir)
        
        # Set environment variables explicitly for this test
        os.environ["SCHOLAR_INBOX_SECRET_URL"] = "https://scholar-inbox.com/login/test123"
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-test-token"
        os.environ["SLACK_CHANNEL_ID"] = "C0123456789"
        os.environ["OPENAI_API_KEY"] = "sk-test-key"
        
        manager = ConfigManager(
            config_path=str(config_file),
            env_path=str(env_file)
        )
        
        assert manager.get_scholar_inbox_url() == "https://scholar-inbox.com/login/test123"
        assert manager.get_slack_token() == "xoxb-test-token"
        assert manager.get_slack_channel_id() == "C0123456789"
        assert manager.get_llm_api_key() == "sk-test-key"
    
    def test_config_validation(self, sample_config_dict):
        """Test Config model validation."""
        config = Config(**sample_config_dict)
        
        assert config.language == "ja"
        assert config.date_range.max_days == 30
        assert config.schedule.check_time == "12:00"
        assert config.schedule.weekdays_only is True
        assert config.slack.post_elements.title is True
        assert config.summary.max_length == 300
        assert len(config.summary.sections) == 1
        assert config.arxiv.prefer_html is True
    
    def test_config_defaults(self):
        """Test Config model with default values."""
        config = Config()
        
        assert config.language == "ja"
        assert config.date_range.max_days == 30
        assert config.schedule.check_time == "12:00"
        assert config.schedule.weekdays_only is True
