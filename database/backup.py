"""
Database backup and restore utilities.
"""
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


def backup_database(
    source_conn: sqlite3.Connection,
    backup_path: str,
    keep_versions: int = 5
) -> bool:
    """
    Backup the database to disk with optional versioning.
    
    Args:
        source_conn: Source SQLite connection (in-memory)
        backup_path: Path to save the backup
        keep_versions: Number of backup versions to keep (0 = no versioning)
    
    Returns:
        True if backup was successful
    """
    backup_file = Path(backup_path)
    
    # Create versioned backup if file exists and versioning is enabled
    if backup_file.exists() and keep_versions > 0:
        _rotate_backups(backup_file, keep_versions)
    
    # Ensure parent directory exists
    backup_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Perform backup
    dest_conn = sqlite3.connect(str(backup_file))
    try:
        source_conn.backup(dest_conn)
        return True
    except Exception:
        return False
    finally:
        dest_conn.close()


def restore_database(
    target_conn: sqlite3.Connection,
    backup_path: str
) -> bool:
    """
    Restore database from disk backup.
    
    Args:
        target_conn: Target SQLite connection (in-memory)
        backup_path: Path to the backup file
    
    Returns:
        True if restore was successful
    """
    backup_file = Path(backup_path)
    
    if not backup_file.exists():
        return False
    
    source_conn = sqlite3.connect(str(backup_file))
    try:
        source_conn.backup(target_conn)
        return True
    except Exception:
        return False
    finally:
        source_conn.close()


def _rotate_backups(backup_file: Path, keep_versions: int) -> None:
    """
    Rotate backup files, keeping specified number of versions.
    
    Args:
        backup_file: Current backup file path
        keep_versions: Number of versions to keep
    """
    # Generate versioned filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    versioned_name = f"{backup_file.stem}_{timestamp}{backup_file.suffix}"
    versioned_path = backup_file.parent / versioned_name
    
    # Move current backup to versioned file
    shutil.copy2(backup_file, versioned_path)
    
    # Clean up old versions
    pattern = f"{backup_file.stem}_*{backup_file.suffix}"
    backups = sorted(
        backup_file.parent.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    # Remove excess backups
    for old_backup in backups[keep_versions:]:
        old_backup.unlink()


def get_backup_info(backup_path: str) -> Optional[dict]:
    """
    Get information about a backup file.
    
    Args:
        backup_path: Path to the backup file
    
    Returns:
        Dictionary with backup info or None if file doesn't exist
    """
    backup_file = Path(backup_path)
    
    if not backup_file.exists():
        return None
    
    stat = backup_file.stat()
    return {
        "path": str(backup_file),
        "size_bytes": stat.st_size,
        "modified_time": datetime.fromtimestamp(stat.st_mtime),
        "created_time": datetime.fromtimestamp(stat.st_ctime),
    }
