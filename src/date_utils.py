"""Date handling utilities for Scholar Inbox URL generation."""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class DateRange:
    """Represents a date range for paper fetching."""
    
    def __init__(self, start_date: datetime, end_date: Optional[datetime] = None):
        """
        Initialize date range.
        
        Args:
            start_date: Start date
            end_date: End date (if None, same as start_date)
        """
        self.start_date = start_date
        self.end_date = end_date or start_date
        
        if self.start_date > self.end_date:
            raise ValueError(f"Start date {self.start_date} is after end date {self.end_date}")
    
    def get_dates(self) -> list[datetime]:
        """
        Get list of dates in the range.
        
        Returns:
            List of datetime objects
        """
        dates = []
        current = self.start_date
        while current <= self.end_date:
            dates.append(current)
            current += timedelta(days=1)
        return dates
    
    def __len__(self) -> int:
        """Get number of days in the range."""
        return (self.end_date - self.start_date).days + 1
    
    def __repr__(self) -> str:
        if self.start_date == self.end_date:
            return f"DateRange({self.start_date.strftime('%Y-%m-%d')})"
        return f"DateRange({self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')})"


class DateParser:
    """Parser for date strings and date ranges."""
    
    # Supported date formats
    DATE_FORMATS = [
        "%Y-%m-%d",      # 2025-10-31
        "%m-%d-%Y",      # 10-31-2025
        "%Y/%m/%d",      # 2025/10/31
        "%m/%d/%Y",      # 10/31/2025
        "%Y%m%d",        # 20251031
    ]
    
    @classmethod
    def parse_date(cls, date_str: str) -> datetime:
        """
        Parse a date string into datetime object.
        
        Args:
            date_str: Date string in various formats
        
        Returns:
            datetime object
        
        Raises:
            ValueError: If date string is invalid
        """
        date_str = date_str.strip()
        
        # Try each format
        for fmt in cls.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # If no format matches, raise error
        raise ValueError(
            f"Invalid date format: '{date_str}'. "
            f"Supported formats: YYYY-MM-DD, MM-DD-YYYY, YYYY/MM/DD, MM/DD/YYYY, YYYYMMDD"
        )
    
    @classmethod
    def parse_date_range(cls, date_range_str: str) -> DateRange:
        """
        Parse a date range string.
        
        Supported formats:
        - Single date: "2025-10-31"
        - Date range: "2025-10-31 to 2025-11-02"
        - Date range: "2025-10-31:2025-11-02"
        - Date range: "2025-10-31..2025-11-02"
        
        Args:
            date_range_str: Date range string
        
        Returns:
            DateRange object
        
        Raises:
            ValueError: If date range string is invalid
        """
        date_range_str = date_range_str.strip()
        
        # Check for range separators
        separators = [' to ', ':', '..', '~']
        for sep in separators:
            if sep in date_range_str:
                parts = date_range_str.split(sep, 1)
                if len(parts) == 2:
                    start_date = cls.parse_date(parts[0])
                    end_date = cls.parse_date(parts[1])
                    return DateRange(start_date, end_date)
        
        # Single date
        date = cls.parse_date(date_range_str)
        return DateRange(date)
    
    @classmethod
    def validate_date_range(cls, date_range: DateRange, max_days: int = 30) -> Tuple[bool, Optional[str]]:
        """
        Validate date range.
        
        Args:
            date_range: DateRange object to validate
            max_days: Maximum allowed days in range
        
        Returns:
            Tuple of (is_valid, warning_message)
        """
        # Check if range is too large
        if len(date_range) > max_days:
            warning = (
                f"Date range spans {len(date_range)} days, which exceeds the recommended "
                f"maximum of {max_days} days. This may result in a large number of papers "
                f"and high API costs. Consider processing a smaller date range."
            )
            return False, warning
        
        # Check if dates are in the future
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if date_range.start_date > today:
            warning = f"Start date {date_range.start_date.strftime('%Y-%m-%d')} is in the future."
            return False, warning
        
        # Check if dates are too far in the past (more than 1 year)
        one_year_ago = today - timedelta(days=365)
        if date_range.end_date < one_year_ago:
            warning = (
                f"End date {date_range.end_date.strftime('%Y-%m-%d')} is more than 1 year ago. "
                f"Papers may no longer be available."
            )
            logger.warning(warning)
            return True, warning  # Warning but still valid
        
        return True, None


def build_scholar_inbox_url(base_url: str, date: datetime) -> str:
    """
    Build Scholar Inbox URL with date parameter.
    
    Args:
        base_url: Base Scholar Inbox URL (with secret key)
        date: Date to fetch papers for
    
    Returns:
        Complete URL with date parameter
    """
    # Extract secret key from URL
    match = re.search(r'/login/([a-f0-9]+)', base_url)
    if not match:
        # URL might already have date parameter or different format
        if 'sha_key=' in base_url:
            # Replace existing date parameter
            base_url = re.sub(r'&date=[\d-]+', '', base_url)
        else:
            raise ValueError(f"Invalid Scholar Inbox URL format: {base_url}")
    
    # Build URL with date parameter
    date_str = date.strftime('%m-%d-%Y')  # Format: MM-DD-YYYY
    
    if 'sha_key=' in base_url:
        return f"{base_url}&date={date_str}"
    else:
        # Convert /login/KEY format to ?sha_key=KEY&date=DATE format
        secret_key = match.group(1)
        return f"https://www.scholar-inbox.com/login?sha_key={secret_key}&date={date_str}"
