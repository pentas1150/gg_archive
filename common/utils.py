"""
Common utility functions.
"""
from datetime import datetime
from typing import Optional


def format_datetime(dt: Optional[datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a datetime object to string.
    
    Args:
        dt: Datetime object to format
        format_str: Format string (default: YYYY-MM-DD HH:MM:SS)
    
    Returns:
        Formatted datetime string or empty string if dt is None
    """
    if dt is None:
        return ""
    return dt.strftime(format_str)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Human-readable size string (e.g., "1.5 MB")
    """
    if size_bytes < 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.1f} {units[unit_index]}"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename safe for filesystem
    """
    # Characters not allowed in filenames
    invalid_chars = '<>:"/\\|?*'
    
    result = filename
    for char in invalid_chars:
        result = result.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    result = result.strip('. ')
    
    return result or "unnamed"


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate a string to specified length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to append when truncated
    
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
