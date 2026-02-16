-- Migration: 002_execution_states
-- Description: Add execution_states table for checkpoint/resume support
-- Created: 2025-02-05

CREATE TABLE IF NOT EXISTS execution_states (
    execution_id TEXT PRIMARY KEY REFERENCES executions(id),
    current_node TEXT NOT NULL,
    context JSON NOT NULL,
    status TEXT DEFAULT 'running',
    error TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_exec_states_status ON execution_states(status);
