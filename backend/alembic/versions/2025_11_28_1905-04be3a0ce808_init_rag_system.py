"""init_rag_system

Revision ID: 04be3a0ce808
Revises: 
Create Date: 2025-11-28 19:05:45.341825

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '04be3a0ce808'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # STEP 1: Ensure pgvector extension is enabled
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # STEP 2: Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    
    # STEP 3: Create analysis_history table
    op.create_table(
        'analysis_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('rfp_filename', sa.String(length=500), nullable=False),
        sa.Column('num_provided_docs', sa.Integer(), nullable=False),
        sa.Column('num_required_docs', sa.Integer(), nullable=False),
        sa.Column('num_matched', sa.Integer(), nullable=False),
        sa.Column('num_review', sa.Integer(), default=0, nullable=True),
        sa.Column('num_missing', sa.Integer(), nullable=False),
        sa.Column('completion_rate', sa.Float(), nullable=False),
        sa.Column('api_cost', sa.Float(), default=0.0, nullable=True),
        sa.Column('results_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_history_id'), 'analysis_history', ['id'], unique=False)
    op.create_index(op.f('ix_analysis_history_user_id'), 'analysis_history', ['user_id'], unique=False)
    
    # STEP 4: Create document_chunks table (RAG)
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('source_filename', sa.String(500), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_chunks_id'), 'document_chunks', ['id'], unique=False)
    op.create_index(op.f('ix_document_chunks_user_id'), 'document_chunks', ['user_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_source_filename'), 'document_chunks', ['source_filename'], unique=False)
    
    # STEP 5: Create vector similarity index (CRITICAL!)
    op.execute("""
        CREATE INDEX idx_document_chunks_embedding_vector 
        ON document_chunks 
        USING ivfflat (embedding vector_l2_ops)
        WITH (lists = 100);
    """)
    
    print("✓ RAG system initialized successfully!")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DROP INDEX IF EXISTS idx_document_chunks_embedding_vector')
    op.drop_index(op.f('ix_document_chunks_source_filename'), table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_user_id'), table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_id'), table_name='document_chunks')
    op.drop_table('document_chunks')
    
    op.drop_index(op.f('ix_analysis_history_user_id'), table_name='analysis_history')
    op.drop_index(op.f('ix_analysis_history_id'), table_name='analysis_history')
    op.drop_table('analysis_history')
    
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')