"""update played_at and player last_played_at

Revision ID: 20260217_143025_update_played_at_and_last_played_at
Revises: beee527fd1bb
Create Date: 2026-02-17 14:30:25+00:00
"""

import shutil
from typing import Sequence, Union
from pathlib import Path

from alembic import op
import sqlalchemy as sa

from config.settings import Settings


# revision identifiers, used by Alembic.
revision: str = "20260217_143025_update_played_at_and_last_played_at"
down_revision: Union[str, None] = "beee527fd1bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
settings = Settings()

def upgrade() -> None:
    try:
        if settings.backup_path.exists():
            # 백업 파일 생성
            shutil.copy2(settings.backup_path, settings.backup_path.with_suffix('.bak'))
    except Exception as e:
        raise Exception(f"Failed to backup database: {e}")

    """Apply data migration for played_at and last_played_at."""
    # 1) match_histories.played_at 에 playtime(초) 더하고 updated_at 갱신
    op.execute(
        sa.text(
            """
            UPDATE match_histories
            SET played_at = datetime(played_at, '+' || playtime || ' seconds'),
                updated_at = CURRENT_TIMESTAMP
            """
        )
    )

    # 2) players.last_played_at 를 각 player 의 마지막 played_at 으로 갱신
    op.execute(
        sa.text(
            """
            UPDATE players
            SET last_played_at = (
                SELECT MAX(mh.played_at)
                FROM match_histories AS mh
                WHERE mh.player_id = players.id
            )
            """
        )
    )

    try:
        if settings.backup_path.with_suffix('.bak').exists():
            # 백업 파일 삭제
            Path(settings.backup_path.with_suffix('.bak')).unlink()
    except Exception:
        pass


def downgrade() -> None:
    """Revert data migration if needed.

    이 데이터 마이그레이션은 손실 없이 정확히 되돌리기 어렵기 때문에
    기본적으로는 no-op 로 둡니다. 필요하다면 별도 로직을 구현하세요.
    """
    try:
        if settings.backup_path.with_suffix('.bak').exists():
            # 백업 파일 복원
            shutil.copy2(settings.backup_path.with_suffix('.bak'), settings.backup_path)
    except Exception as e:
        raise Exception(f"Failed to restore database: {e}")

