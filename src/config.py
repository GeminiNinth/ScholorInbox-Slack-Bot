"""Configuration management module."""

import os
import yaml
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from .models import Config
import logging

logger = logging.getLogger(__name__)


def sanitize_env_value(value: str) -> str:
    """
    Sanitize environment variable value by removing surrounding quotes and whitespace.
    
    This function handles cases where environment variables might be quoted in .env files
    or passed via --env-file in Docker, ensuring the actual value is extracted correctly.
    
    Args:
        value: The raw environment variable value
        
    Returns:
        The sanitized value with quotes and whitespace removed
    """
    if not value:
        return ""
    
    # Remove surrounding whitespace
    value = value.strip()
    
    # Remove quotes from both ends if present
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1].strip()
    # Also handle cases where only one end has a quote
    elif value.startswith('"') or value.startswith("'"):
        value = value[1:].strip()
    elif value.endswith('"') or value.endswith("'"):
        value = value[:-1].strip()
    
    return value


class ConfigManager:
    """Manages application configuration from YAML and environment variables."""
    
    def __init__(self, config_path: str = "config.yaml", env_path: str = ".env"):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to config.yaml file
            env_path: Path to .env file
        """
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        
        # Load environment variables
        # Try to load from .env file if it exists
        # If using --env-file in Docker, environment variables are already set
        if self.env_path.exists():
            load_dotenv(self.env_path)
            logger.info(f"Successfully loaded .env file from {self.env_path}")
        else:
            # Check if required env vars are already set (e.g., from --env-file in Docker)
            if not os.getenv("SCHOLAR_INBOX_SECRET_URL") and not os.getenv("SLACK_BOT_TOKEN"):
                logger.warning(f".env file not found at {self.env_path}, but environment variables may be set via --env-file")
            else:
                logger.debug(f".env file not found at {self.env_path}, using environment variables from system")
        
        # Load YAML configuration
        self.config = self._load_config()
        
        # Validate required environment variables
        self._validate_env_vars()
    
    def _load_config(self) -> Config:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found at {self.config_path}, using defaults")
            return Config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
            
            logger.info(f"Loaded configuration from {self.config_path}")
            return Config(**config_dict)
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            raise
    
    def _validate_env_vars(self):
        """Validate required environment variables."""
        required_vars = [
            "SCHOLAR_INBOX_SECRET_URL",
            "SLACK_BOT_TOKEN",
            "SLACK_CHANNEL_ID"
        ]
        
        # Check LLM provider API key
        llm_provider = self.config.llm.provider
        if llm_provider == "openai":
            required_vars.append("OPENAI_API_KEY")
        elif llm_provider == "anthropic":
            required_vars.append("ANTHROPIC_API_KEY")
        elif llm_provider == "google":
            required_vars.append("GOOGLE_API_KEY")
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("All required environment variables are set")
    
    def get_scholar_inbox_url(self) -> str:
        """Get Scholar Inbox secret URL."""
        url = os.getenv("SCHOLAR_INBOX_SECRET_URL", "")
        return sanitize_env_value(url)
    
    def get_slack_token(self) -> str:
        """Get Slack bot token."""
        token = os.getenv("SLACK_BOT_TOKEN", "")
        return sanitize_env_value(token)
    
    def get_slack_channel_id(self) -> str:
        """Get Slack channel ID."""
        channel_id = os.getenv("SLACK_CHANNEL_ID", "")
        return sanitize_env_value(channel_id)
    
    def get_llm_api_key(self) -> str:
        """Get LLM API key based on configured provider."""
        provider = self.config.llm.provider
        if provider == "openai":
            key = os.getenv("OPENAI_API_KEY", "")
        elif provider == "anthropic":
            key = os.getenv("ANTHROPIC_API_KEY", "")
        elif provider == "google":
            key = os.getenv("GOOGLE_API_KEY", "")
        else:
            return ""
        
        key = sanitize_env_value(key)
        
        # Debug: Log API key info (without exposing the actual key)
        if key:
            logger.debug(f"API key loaded for {provider}: length={len(key)}, starts_with={key[:7]}..., ends_with=...{key[-3:]}")
        else:
            logger.warning(f"No API key found for provider: {provider}")
        
        return key
    
    def get_config(self) -> Config:
        """Get the loaded configuration object."""
        return self.config
