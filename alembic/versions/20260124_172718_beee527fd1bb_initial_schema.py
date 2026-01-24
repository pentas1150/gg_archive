"""initial_schema

Revision ID: beee527fd1bb
Revises:
Create Date: 2026-01-24 17:27:18.454250+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'beee527fd1bb'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # maps 테이블 생성
    op.create_table(
        'maps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uidx_map_name')
    )

    # players 테이블 생성
    op.create_table(
        'players',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('game_id', sa.String(length=255), nullable=False),
        sa.Column('total_games', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_wins', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_losses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_win_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('last_played_at', sa.DateTime(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_id', name='uidx_player_game_id')
    )
    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.create_index('idx_player_last_played_at', [sa.literal_column('last_played_at DESC')], unique=False)

    # match_histories 테이블 생성
    op.create_table(
        'match_histories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('opponent_id', sa.String(length=255), nullable=False),
        sa.Column('race', sa.String(length=10), nullable=False),
        sa.Column('map_id', sa.Integer(), nullable=False),
        sa.Column('map_name', sa.String(length=255), nullable=False),
        sa.Column('apm', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('eapm', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_win', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('playtime', sa.Integer(), nullable=False, server_default='0', comment='Playtime in seconds'),
        sa.Column('played_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id']),
        sa.ForeignKeyConstraint(['player_id'], ['players.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('played_at', 'player_id', name='uidx_match_history_played_at_player_id')
    )

    # stats 테이블 생성
    op.create_table(
        'stats',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('map_id', sa.Integer(), nullable=False),
        sa.Column('map_name', sa.String(length=255), nullable=False),
        sa.Column('total_games', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('wins', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('losses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('win_rate', sa.Double(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id']),
        sa.ForeignKeyConstraint(['player_id'], ['players.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('player_id', 'map_id', name='uidx_stat_player_id_map_id')
    )
    with op.batch_alter_table('stats', schema=None) as batch_op:
        batch_op.create_index('idx_stat_map_name', ['map_name'], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""
    with op.batch_alter_table('stats', schema=None) as batch_op:
        batch_op.drop_index('idx_stat_map_name')

    op.drop_table('stats')
    op.drop_table('match_histories')

    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.drop_index('idx_player_last_played_at')

    op.drop_table('players')
    op.drop_table('maps')
