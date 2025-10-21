-- =====================================================
-- MCP Analytics Server - Metadata Database Schema
-- =====================================================
-- Purpose: Store dataset registry, LLM metadata, query logs
-- Database: metadata_db (separate from user datasets)
-- PostgreSQL 14+
-- =====================================================

-- Drop existing tables (for fresh install)
DROP TABLE IF EXISTS query_logs CASCADE;
DROP TABLE IF EXISTS llm_metadata CASCADE;
DROP TABLE IF EXISTS dataset_schemas CASCADE;
DROP TABLE IF EXISTS datasets CASCADE;
DROP TABLE IF EXISTS context_cache CASCADE;

-- =====================================================
-- Table: datasets
-- =====================================================
-- Stores registered datasets with connection info and metadata
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,

    -- Basic Info
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,  -- Short 1-2 line description for LLM

    -- Connection
    connection_string_encrypted TEXT NOT NULL,  -- Encrypted using Fernet
    dataset_type VARCHAR(50),  -- 'event_level', 'aggregated', 'mixed'
    data_source VARCHAR(100) DEFAULT 'postgres',  -- 'fabric', 'postgres', 'custom'

    -- Status Management
    status VARCHAR(50) DEFAULT 'draft',
    -- States: 'draft' → 'profiling' → 'metadata_pending' → 'approved' → 'active' / 'inactive'

    -- LLM-Generated Metadata (populated after profiling)
    date_range_start DATE,
    date_range_end DATE,
    data_category VARCHAR(100),  -- 'ctv', 'mobile', 'ecommerce', 'ads', 'mixed'
    use_cases TEXT[],  -- ['media planning', 'ecommerce optimization', etc.]

    -- Weighting Info
    has_weight_column BOOLEAN DEFAULT false,
    weight_column_name VARCHAR(100),

    -- Governance
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,
    approved_by VARCHAR(100),

    -- Performance Metadata
    estimated_row_count BIGINT,
    estimated_size_mb NUMERIC(10, 2),
    last_profiled_at TIMESTAMP,

    -- Soft Delete
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP,

    CONSTRAINT valid_status CHECK (
        status IN ('draft', 'profiling', 'metadata_pending', 'approved', 'active', 'inactive', 'error')
    ),
    CONSTRAINT valid_dataset_type CHECK (
        dataset_type IN ('event_level', 'aggregated', 'mixed')
    )
);

-- Indexes for performance
CREATE INDEX idx_datasets_status ON datasets(status) WHERE is_deleted = false;
CREATE INDEX idx_datasets_name ON datasets(name) WHERE is_deleted = false;
CREATE INDEX idx_datasets_created_at ON datasets(created_at DESC);
CREATE INDEX idx_datasets_data_category ON datasets(data_category) WHERE status = 'approved';

-- Comments
COMMENT ON TABLE datasets IS 'Registry of all datasets with connection strings and metadata';
COMMENT ON COLUMN datasets.connection_string_encrypted IS 'Encrypted PostgreSQL connection string using Fernet cipher';
COMMENT ON COLUMN datasets.status IS 'Lifecycle state: draft → profiling → metadata_pending → approved → active';


-- =====================================================
-- Table: dataset_schemas
-- =====================================================
-- Stores profiled schemas for each table in a dataset
CREATE TABLE dataset_schemas (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,

    -- Table Info
    table_name VARCHAR(255) NOT NULL,
    table_schema_name VARCHAR(100) DEFAULT 'public',

    -- Schema Data (stored as JSONB for flexibility)
    table_schema JSONB NOT NULL,
    -- Example: {"columns": [...], "indexes": [...], "constraints": [...]}

    -- Sample Data
    sample_data JSONB,
    -- Example: [{"col1": "val1", "col2": 123}, ...]
    sample_size INTEGER DEFAULT 10,

    -- Statistics
    row_count BIGINT,
    size_mb NUMERIC(10, 2),

    -- Column Metadata (denormalized for quick access)
    columns JSONB NOT NULL,
    -- Example: [
    --   {
    --     "name": "user_id",
    --     "type": "bigint",
    --     "nullable": false,
    --     "description": "Unique user identifier",
    --     "stats": {
    --       "null_count": 0,
    --       "distinct_count": 1234567,
    --       "min": 1,
    --       "max": 9999999
    --     }
    --   }
    -- ]

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(dataset_id, table_schema_name, table_name)
);

CREATE INDEX idx_dataset_schemas_dataset_id ON dataset_schemas(dataset_id);
CREATE INDEX idx_dataset_schemas_table_name ON dataset_schemas(table_name);
CREATE INDEX idx_dataset_schemas_columns ON dataset_schemas USING GIN(columns);

COMMENT ON TABLE dataset_schemas IS 'Profiled schemas and statistics for tables in datasets';


-- =====================================================
-- Table: llm_metadata
-- =====================================================
-- Stores LLM-generated metadata and user edits
CREATE TABLE llm_metadata (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,

    -- LLM-Generated Content
    generated_description TEXT,  -- Detailed description
    data_dictionary JSONB,  -- {"column_name": "explanation", ...}
    quality_observations TEXT[],  -- ["observation1", "observation2", ...]
    improvement_suggestions TEXT[],  -- ["suggestion1", ...]
    recommended_use_cases TEXT[],  -- ["media planning", "ecommerce optimization"]

    -- Additional Context
    key_insights TEXT[],  -- Key findings from data analysis
    sample_queries TEXT[],  -- Suggested SQL queries

    -- LLM Metadata
    llm_model VARCHAR(100) DEFAULT 'gpt-4o-mini',
    llm_provider VARCHAR(50) DEFAULT 'openai',
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    generation_time_seconds NUMERIC(6, 2),
    generation_cost_usd NUMERIC(8, 4),

    -- User Validation
    user_edited BOOLEAN DEFAULT false,
    user_approved BOOLEAN DEFAULT false,
    user_notes TEXT,
    edited_fields TEXT[],  -- Track which fields were edited

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,

    -- Versioning (for regeneration)
    version INTEGER DEFAULT 1
);

CREATE INDEX idx_llm_metadata_dataset_id ON llm_metadata(dataset_id);
CREATE INDEX idx_llm_metadata_approved ON llm_metadata(user_approved);

COMMENT ON TABLE llm_metadata IS 'LLM-generated metadata and data dictionaries for datasets';


-- =====================================================
-- Table: query_logs
-- =====================================================
-- Logs all queries executed through the MCP server
CREATE TABLE query_logs (
    id SERIAL PRIMARY KEY,

    -- Query Info
    query_text TEXT NOT NULL,
    query_hash VARCHAR(64),  -- MD5 hash for deduplication
    query_type VARCHAR(50),  -- 'raw', 'aggregated', 'weighted', 'multi'

    -- Datasets Used
    datasets_used INTEGER[],  -- Array of dataset IDs
    primary_dataset_id INTEGER REFERENCES datasets(id) ON DELETE SET NULL,

    -- Execution Details
    execution_time_ms INTEGER NOT NULL,
    rows_returned INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    error_type VARCHAR(100),  -- 'syntax_error', 'permission_denied', 'timeout', etc.

    -- Context
    tool_used VARCHAR(100),  -- 'chatgpt', 'claude', 'manus', 'cursor', 'api'
    user_agent TEXT,
    session_id VARCHAR(255),
    ip_address INET,

    -- Response Metadata
    response_format VARCHAR(50) DEFAULT 'markdown',  -- 'markdown', 'json'
    response_size_bytes INTEGER,
    response_token_count INTEGER,
    was_cached BOOLEAN DEFAULT false,
    cache_hit_key VARCHAR(255),

    -- Performance Tracking
    db_connection_time_ms INTEGER,
    query_parsing_time_ms INTEGER,
    result_formatting_time_ms INTEGER,

    -- Weighting Applied
    weights_applied BOOLEAN DEFAULT false,
    weight_column_used VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),

    -- User Context (if applicable)
    user_id VARCHAR(100),
    organization_id VARCHAR(100)
);

-- Indexes for query log analytics
CREATE INDEX idx_query_logs_created_at ON query_logs(created_at DESC);
CREATE INDEX idx_query_logs_tool_used ON query_logs(tool_used);
CREATE INDEX idx_query_logs_datasets_used ON query_logs USING GIN(datasets_used);
CREATE INDEX idx_query_logs_success ON query_logs(success);
CREATE INDEX idx_query_logs_query_hash ON query_logs(query_hash);
CREATE INDEX idx_query_logs_session_id ON query_logs(session_id);

-- Partial index for errors only
CREATE INDEX idx_query_logs_errors ON query_logs(created_at DESC, error_type)
WHERE success = false;

COMMENT ON TABLE query_logs IS 'Audit log of all MCP queries with performance metrics';


-- =====================================================
-- Table: context_cache
-- =====================================================
-- Caches progressive context for different levels
CREATE TABLE context_cache (
    id SERIAL PRIMARY KEY,

    -- Cache Key
    cache_key VARCHAR(255) NOT NULL UNIQUE,

    -- Context Level (0=global, 1=datasets, 2=schema, 3=full)
    context_level INTEGER NOT NULL CHECK (context_level BETWEEN 0 AND 3),

    -- Cached Data
    context_data JSONB NOT NULL,
    context_markdown TEXT,  -- Pre-rendered markdown

    -- Token Metrics
    token_count INTEGER,
    compressed_size_bytes INTEGER,

    -- Related Entities
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE CASCADE,
    table_name VARCHAR(255),

    -- Expiration
    expires_at TIMESTAMP NOT NULL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed_at TIMESTAMP DEFAULT NOW(),
    access_count INTEGER DEFAULT 0
);

CREATE INDEX idx_context_cache_key ON context_cache(cache_key);
CREATE INDEX idx_context_cache_expires ON context_cache(expires_at);
CREATE INDEX idx_context_cache_dataset_id ON context_cache(dataset_id) WHERE dataset_id IS NOT NULL;

-- Auto-delete expired cache entries
CREATE OR REPLACE FUNCTION delete_expired_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM context_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE context_cache IS 'Cached context for progressive loading at different levels';


-- =====================================================
-- Table: system_config
-- =====================================================
-- Stores system-wide configuration
CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL UNIQUE,
    value JSONB NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT false,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default config
INSERT INTO system_config (key, value, description) VALUES
    ('weighting_rules', '{"merge_nccs": {"A": ["A", "A1"], "C/D/E": ["C", "D", "E"]}, "always_apply": true}', 'Global weighting and NCCS merging rules'),
    ('query_limits', '{"max_raw_rows": 5, "max_aggregated_rows": 1000, "max_parallel_queries": 30}', 'Query execution limits'),
    ('llm_config', '{"model": "gpt-4o-mini", "temperature": 0.3, "max_tokens": 4000}', 'LLM configuration for metadata generation'),
    ('cache_ttl', '{"level_0": 3600, "level_1": 1800, "level_2": 900, "level_3": 300}', 'Cache TTL in seconds for each context level');

COMMENT ON TABLE system_config IS 'System-wide configuration in key-value format';


-- =====================================================
-- Views for Analytics
-- =====================================================

-- View: Active Datasets Summary
CREATE VIEW v_active_datasets AS
SELECT
    d.id,
    d.name,
    d.description,
    d.data_category,
    d.date_range_start,
    d.date_range_end,
    d.estimated_row_count,
    d.has_weight_column,
    COUNT(DISTINCT ds.id) as table_count,
    d.created_at,
    d.last_profiled_at,
    CASE
        WHEN d.last_profiled_at > NOW() - INTERVAL '7 days' THEN 'fresh'
        WHEN d.last_profiled_at > NOW() - INTERVAL '30 days' THEN 'stale'
        ELSE 'outdated'
    END as freshness_status
FROM datasets d
LEFT JOIN dataset_schemas ds ON d.id = ds.dataset_id
WHERE d.status = 'approved' AND d.is_deleted = false
GROUP BY d.id;

-- View: Query Analytics
CREATE VIEW v_query_analytics AS
SELECT
    DATE_TRUNC('hour', created_at) as hour,
    tool_used,
    COUNT(*) as total_queries,
    COUNT(*) FILTER (WHERE success = true) as successful_queries,
    COUNT(*) FILTER (WHERE success = false) as failed_queries,
    AVG(execution_time_ms) as avg_execution_time_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_time_ms) as p95_execution_time_ms,
    SUM(rows_returned) as total_rows_returned,
    COUNT(DISTINCT session_id) as unique_sessions
FROM query_logs
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('hour', created_at), tool_used
ORDER BY hour DESC;

-- View: Dataset Usage Stats
CREATE VIEW v_dataset_usage AS
SELECT
    d.id as dataset_id,
    d.name as dataset_name,
    COUNT(ql.id) as query_count,
    COUNT(DISTINCT ql.session_id) as unique_users,
    AVG(ql.execution_time_ms) as avg_query_time_ms,
    MAX(ql.created_at) as last_queried_at,
    COUNT(*) FILTER (WHERE ql.created_at > NOW() - INTERVAL '7 days') as queries_last_7_days
FROM datasets d
LEFT JOIN query_logs ql ON d.id = ANY(ql.datasets_used)
WHERE d.status = 'approved' AND d.is_deleted = false
GROUP BY d.id, d.name
ORDER BY query_count DESC;


-- =====================================================
-- Functions and Triggers
-- =====================================================

-- Function: Update timestamp on row modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update_updated_at trigger to relevant tables
CREATE TRIGGER update_datasets_updated_at BEFORE UPDATE ON datasets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dataset_schemas_updated_at BEFORE UPDATE ON dataset_schemas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_llm_metadata_updated_at BEFORE UPDATE ON llm_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- Function: Generate query hash
CREATE OR REPLACE FUNCTION generate_query_hash()
RETURNS TRIGGER AS $$
BEGIN
    NEW.query_hash = MD5(NEW.query_text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER generate_query_logs_hash BEFORE INSERT ON query_logs
    FOR EACH ROW EXECUTE FUNCTION generate_query_hash();


-- Function: Cleanup old query logs (retention policy)
CREATE OR REPLACE FUNCTION cleanup_old_query_logs(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM query_logs
    WHERE created_at < NOW() - (retention_days || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Schedule cleanup (run manually or via cron)
COMMENT ON FUNCTION cleanup_old_query_logs IS 'Delete query logs older than specified days (default 90)';


-- =====================================================
-- Materialized Views for Performance
-- =====================================================

-- Materialized View: Dataset Metadata for Quick Context Loading
CREATE MATERIALIZED VIEW mv_dataset_context AS
SELECT
    d.id,
    d.name,
    d.description,
    d.data_category,
    d.date_range_start,
    d.date_range_end,
    d.use_cases,
    d.has_weight_column,
    d.weight_column_name,
    d.estimated_row_count,
    json_agg(
        json_build_object(
            'table_name', ds.table_name,
            'row_count', ds.row_count,
            'columns', (
                SELECT json_agg(
                    json_build_object(
                        'name', col->>'name',
                        'type', col->>'type'
                    )
                )
                FROM jsonb_array_elements(ds.columns) col
            )
        )
    ) as tables,
    lm.generated_description,
    lm.recommended_use_cases
FROM datasets d
LEFT JOIN dataset_schemas ds ON d.id = ds.dataset_id
LEFT JOIN llm_metadata lm ON d.id = lm.dataset_id
WHERE d.status = 'approved' AND d.is_deleted = false
GROUP BY d.id, lm.generated_description, lm.recommended_use_cases;

CREATE UNIQUE INDEX ON mv_dataset_context (id);

-- Refresh function
CREATE OR REPLACE FUNCTION refresh_dataset_context()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dataset_context;
END;
$$ LANGUAGE plpgsql;

COMMENT ON MATERIALIZED VIEW mv_dataset_context IS 'Pre-computed dataset context for fast MCP tool responses';


-- =====================================================
-- Sample Data (for testing)
-- =====================================================

-- Note: In production, this would be inserted via the application
-- This is just for reference/testing

/*
-- Example: Insert a sample dataset
INSERT INTO datasets (
    name,
    description,
    connection_string_encrypted,
    dataset_type,
    data_source,
    status
) VALUES (
    'sample_ctv_data',
    'CTV viewership data Q1 2024 - weighted panel',
    'encrypted_connection_string_here',
    'event_level',
    'fabric',
    'approved'
);
*/


-- =====================================================
-- Database Permissions (Production)
-- =====================================================

-- Create application user
-- CREATE USER mcp_app WITH PASSWORD 'secure_password_here';

-- Grant necessary permissions
-- GRANT CONNECT ON DATABASE metadata_db TO mcp_app;
-- GRANT USAGE ON SCHEMA public TO mcp_app;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO mcp_app;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO mcp_app;

-- Read-only user for analytics
-- CREATE USER mcp_readonly WITH PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE metadata_db TO mcp_readonly;
-- GRANT USAGE ON SCHEMA public TO mcp_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;


-- =====================================================
-- Maintenance Tasks
-- =====================================================

-- Run these periodically (or set up pg_cron)

-- 1. Refresh materialized views (daily)
-- SELECT refresh_dataset_context();

-- 2. Cleanup old query logs (weekly)
-- SELECT cleanup_old_query_logs(90);

-- 3. Cleanup expired cache (hourly)
-- SELECT delete_expired_cache();

-- 4. Vacuum analyze (daily)
-- VACUUM ANALYZE;

-- 5. Update table statistics (weekly)
-- ANALYZE;


-- =====================================================
-- Performance Monitoring Queries
-- =====================================================

-- Check table sizes
/*
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
*/

-- Check query log statistics
/*
SELECT
    tool_used,
    COUNT(*) as total_queries,
    AVG(execution_time_ms) as avg_time_ms,
    MAX(execution_time_ms) as max_time_ms
FROM query_logs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY tool_used;
*/

-- =====================================================
-- End of Schema
-- =====================================================
