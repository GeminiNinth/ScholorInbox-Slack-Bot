"""Tests for date_utils module."""

import pytest
from datetime import datetime, timedelta
from src.date_utils import DateRange, DateParser, build_scholar_inbox_url


class TestDateRange:
    """Tests for DateRange class."""
    
    def test_single_date(self):
        """Test DateRange with single date."""
        date = datetime(2025, 10, 31)
        dr = DateRange(date)
        
        assert dr.start_date == date
        assert dr.end_date == date
        assert len(dr) == 1
        assert dr.get_dates() == [date]
    
    def test_date_range(self):
        """Test DateRange with multiple dates."""
        start = datetime(2025, 10, 31)
        end = datetime(2025, 11, 2)
        dr = DateRange(start, end)
        
        assert dr.start_date == start
        assert dr.end_date == end
        assert len(dr) == 3
        
        dates = dr.get_dates()
        assert len(dates) == 3
        assert dates[0] == start
        assert dates[1] == datetime(2025, 11, 1)
        assert dates[2] == end
    
    def test_invalid_range(self):
        """Test DateRange with start after end."""
        start = datetime(2025, 11, 2)
        end = datetime(2025, 10, 31)
        
        with pytest.raises(ValueError, match="Start date .* is after end date"):
            DateRange(start, end)
    
    def test_repr(self):
        """Test DateRange string representation."""
        # Single date
        date = datetime(2025, 10, 31)
        dr = DateRange(date)
        assert repr(dr) == "DateRange(2025-10-31)"
        
        # Date range
        start = datetime(2025, 10, 31)
        end = datetime(2025, 11, 2)
        dr = DateRange(start, end)
        assert repr(dr) == "DateRange(2025-10-31 to 2025-11-02)"


class TestDateParser:
    """Tests for DateParser class."""
    
    @pytest.mark.parametrize("date_str,expected", [
        ("2025-10-31", datetime(2025, 10, 31)),
        ("10-31-2025", datetime(2025, 10, 31)),
        ("2025/10/31", datetime(2025, 10, 31)),
        ("10/31/2025", datetime(2025, 10, 31)),
        ("20251031", datetime(2025, 10, 31)),
    ])
    def test_parse_date_formats(self, date_str, expected):
        """Test parsing various date formats."""
        result = DateParser.parse_date(date_str)
        assert result == expected
    
    def test_parse_date_invalid(self):
        """Test parsing invalid date."""
        with pytest.raises(ValueError, match="Invalid date format"):
            DateParser.parse_date("invalid-date")
    
    def test_parse_date_with_whitespace(self):
        """Test parsing date with whitespace."""
        result = DateParser.parse_date("  2025-10-31  ")
        assert result == datetime(2025, 10, 31)
    
    @pytest.mark.parametrize("range_str,expected_start,expected_end", [
        ("2025-10-31", datetime(2025, 10, 31), datetime(2025, 10, 31)),
        ("2025-10-31 to 2025-11-02", datetime(2025, 10, 31), datetime(2025, 11, 2)),
        ("2025-10-31:2025-11-02", datetime(2025, 10, 31), datetime(2025, 11, 2)),
        ("2025-10-31..2025-11-02", datetime(2025, 10, 31), datetime(2025, 11, 2)),
        ("2025-10-31~2025-11-02", datetime(2025, 10, 31), datetime(2025, 11, 2)),
    ])
    def test_parse_date_range(self, range_str, expected_start, expected_end):
        """Test parsing date ranges with various separators."""
        dr = DateParser.parse_date_range(range_str)
        assert dr.start_date == expected_start
        assert dr.end_date == expected_end
    
    def test_validate_date_range_valid(self):
        """Test validating valid date range."""
        start = datetime.now() - timedelta(days=5)
        end = datetime.now() - timedelta(days=1)
        dr = DateRange(start, end)
        
        is_valid, warning = DateParser.validate_date_range(dr, max_days=30)
        assert is_valid is True
        assert warning is None
    
    def test_validate_date_range_too_large(self):
        """Test validating date range that exceeds max days."""
        start = datetime(2025, 1, 1)
        end = datetime(2025, 2, 15)  # 46 days
        dr = DateRange(start, end)
        
        is_valid, warning = DateParser.validate_date_range(dr, max_days=30)
        assert is_valid is False
        assert "exceeds the recommended maximum" in warning
    
    def test_validate_date_range_future(self):
        """Test validating date range in the future."""
        start = datetime.now() + timedelta(days=1)
        end = datetime.now() + timedelta(days=5)
        dr = DateRange(start, end)
        
        is_valid, warning = DateParser.validate_date_range(dr, max_days=30)
        assert is_valid is False
        assert "is in the future" in warning
    
    def test_validate_date_range_old(self):
        """Test validating date range more than 1 year ago."""
        start = datetime.now() - timedelta(days=400)
        end = datetime.now() - timedelta(days=395)
        dr = DateRange(start, end)
        
        is_valid, warning = DateParser.validate_date_range(dr, max_days=30)
        assert is_valid is True  # Valid but with warning
        assert "more than 1 year ago" in warning


class TestBuildScholarInboxUrl:
    """Tests for build_scholar_inbox_url function."""
    
    def test_build_url_from_login_format(self):
        """Test building URL from /login/KEY format."""
        base_url = "https://scholar-inbox.com/login/abc123def456"
        date = datetime(2025, 10, 31)
        
        result = build_scholar_inbox_url(base_url, date)
        expected = "https://www.scholar-inbox.com/login?sha_key=abc123def456&date=10-31-2025"
        assert result == expected
    
    def test_build_url_from_query_format(self):
        """Test building URL from ?sha_key=KEY format."""
        base_url = "https://www.scholar-inbox.com/login?sha_key=abc123def456"
        date = datetime(2025, 10, 31)
        
        result = build_scholar_inbox_url(base_url, date)
        expected = "https://www.scholar-inbox.com/login?sha_key=abc123def456&date=10-31-2025"
        assert result == expected
    
    def test_build_url_replace_existing_date(self):
        """Test replacing existing date parameter."""
        base_url = "https://www.scholar-inbox.com/login?sha_key=abc123def456&date=10-30-2025"
        date = datetime(2025, 10, 31)
        
        result = build_scholar_inbox_url(base_url, date)
        expected = "https://www.scholar-inbox.com/login?sha_key=abc123def456&date=10-31-2025"
        assert result == expected
    
    def test_build_url_invalid_format(self):
        """Test building URL with invalid format."""
        base_url = "https://invalid-url.com"
        date = datetime(2025, 10, 31)
        
        with pytest.raises(ValueError, match="Invalid Scholar Inbox URL format"):
            build_scholar_inbox_url(base_url, date)
