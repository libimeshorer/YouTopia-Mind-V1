"""Add agent capability tables for agentic features

Revision ID: 003
Revises: 002
Create Date: 2024-01-15

Adds tables for:
- agent_capabilities: Tracks enabled capabilities per clone (e.g., Slack observer)
- agent_preferences: Learned preferences for classification
- agent_observations: Classified messages from external sources
- observation_checkpoints: Progress tracking per channel
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    op.execute("CREATE TYPE agent_capability_status AS ENUM ('active', 'paused', 'setup_required', 'error')")
    op.execute("CREATE TYPE observation_status AS ENUM ('classified', 'reviewed')")

    # Create agent_capabilities table
    op.create_table(
        'agent_capabilities',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('integration_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('capability_type', sa.String(50), nullable=False),
        sa.Column('config', sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'paused', 'setup_required', 'error', name='agent_capability_status', create_type=False), nullable=False, server_default='active'),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['clone_id'], ['clones.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['integration_id'], ['integrations.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('clone_id', 'platform', 'capability_type', name='uq_capability_clone_platform_type'),
    )
    op.create_index('ix_agent_capabilities_clone_id', 'agent_capabilities', ['clone_id'])

    # Create agent_preferences table
    op.create_table(
        'agent_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('capability_type', sa.String(50), nullable=False),
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('preference_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('keywords', sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column('examples', sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['clone_id'], ['clones.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('clone_id', 'capability_type', 'platform', 'preference_type', name='uq_preference_clone_capability_platform_type'),
    )
    op.create_index('ix_agent_preferences_clone_id', 'agent_preferences', ['clone_id'])

    # Create agent_observations table
    op.create_table(
        'agent_observations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('clone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('capability_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', sa.String(255), nullable=False),
        sa.Column('source_metadata', sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('classification', sa.String(50), nullable=True),
        sa.Column('classification_confidence', sa.Float(), nullable=True),
        sa.Column('classification_reasoning', sa.Text(), nullable=True),
        sa.Column('needs_review', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('user_feedback', sa.String(50), nullable=True),
        sa.Column('status', postgresql.ENUM('classified', 'reviewed', name='observation_status', create_type=False), nullable=False, server_default='classified'),
        sa.Column('observed_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['clone_id'], ['clones.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['capability_id'], ['agent_capabilities.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('clone_id', 'source_type', 'source_id', name='uq_observation_clone_source'),
    )
    op.create_index('ix_agent_observations_clone_id', 'agent_observations', ['clone_id'])
    op.create_index('ix_agent_observations_capability_id', 'agent_observations', ['capability_id'])
    op.create_index('ix_observation_clone_classification', 'agent_observations', ['clone_id', 'classification'])

    # Create observation_checkpoints table
    op.create_table(
        'observation_checkpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('capability_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', sa.String(100), nullable=False),
        sa.Column('last_message_ts', sa.String(50), nullable=True),
        sa.Column('last_observed_at', sa.DateTime(), nullable=True),
        sa.Column('messages_seen', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('messages_stored', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['capability_id'], ['agent_capabilities.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('capability_id', 'channel_id', name='uq_checkpoint_capability_channel'),
    )
    op.create_index('ix_observation_checkpoints_capability_id', 'observation_checkpoints', ['capability_id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('observation_checkpoints')
    op.drop_table('agent_observations')
    op.drop_table('agent_preferences')
    op.drop_table('agent_capabilities')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS observation_status")
    op.execute("DROP TYPE IF EXISTS agent_capability_status")
