-- 数据库迁移脚本
-- Social Feed Aggregator

-- 启用扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 用于模糊搜索

-- 平台枚举类型
DO $$ BEGIN
    CREATE TYPE platform AS ENUM ('discord', 'reddit', 'qq', 'wecom');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE sentiment AS ENUM ('positive', 'neutral', 'negative');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE fetch_status AS ENUM ('success', 'failed', 'partial');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============ 渠道配置表 ============
CREATE TABLE IF NOT EXISTS channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform platform NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- 渠道配置 (加密存储)
    config JSONB NOT NULL DEFAULT '{}',
    
    -- Webhook 配置
    webhook_id VARCHAR(255),
    webhook_url VARCHAR(500),
    
    -- 状态
    enabled BOOLEAN DEFAULT TRUE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_channels_platform ON channels(platform);
CREATE INDEX IF NOT EXISTS idx_channels_enabled ON channels(enabled);

-- ============ 消息表 ============
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id UUID NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    
    -- 原始信息
    platform_message_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    author_id VARCHAR(255) NOT NULL,
    author_name VARCHAR(255) NOT NULL,
    author_avatar VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- 元数据
    extra_metadata JSONB,
    attachments JSONB,
    channel_name VARCHAR(255),
    
    -- AI 分析结果
    sentiment sentiment,
    categories TEXT[],
    entities JSONB,
    summary VARCHAR(500),
    embedding JSONB,
    
    -- 状态
    analyzed BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_messages_channel_id ON messages(channel_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_author_id ON messages(author_id);
CREATE INDEX IF NOT EXISTS idx_messages_platform_msg_id ON messages(platform_message_id);
CREATE INDEX IF NOT EXISTS idx_messages_analyzed ON messages(analyzed);
CREATE INDEX IF NOT EXISTS idx_messages_is_deleted ON messages(is_deleted);

-- GIN 索引用于数组搜索 (categories)
CREATE INDEX IF NOT EXISTS idx_messages_categories ON messages USING GIN(categories);

-- GIN 索引用于 JSONB 搜索 (entities)
CREATE INDEX IF NOT EXISTS idx_messages_entities ON messages USING GIN(entities);

-- 全文搜索索引 (仅英文)
CREATE INDEX IF NOT EXISTS idx_messages_content_fts ON messages USING GIN(
    to_tsvector('english', content)
);

-- 复合唯一索引: 渠道 + 平台消息ID
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_unique_platform_msg
ON messages(channel_id, platform_message_id);

-- ============ 抓取日志表 ============
CREATE TABLE IF NOT EXISTS fetch_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id UUID NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    
    status fetch_status NOT NULL DEFAULT 'success',
    messages_count INTEGER DEFAULT 0,
    new_messages_count INTEGER DEFAULT 0,
    error_message TEXT,
    
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_fetch_logs_channel_id ON fetch_logs(channel_id);
CREATE INDEX IF NOT EXISTS idx_fetch_logs_started_at ON fetch_logs(started_at DESC);

-- ============ AI 分析任务表 ============
CREATE TABLE IF NOT EXISTS analysis_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_status ON analysis_tasks(status);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_message_id ON analysis_tasks(message_id);

-- ============ 视图 ============
-- 未分析消息视图 (用于 Worker 轮询)
CREATE OR REPLACE VIEW pending_analysis AS
SELECT m.*
FROM messages m
LEFT JOIN analysis_tasks t ON m.id = t.message_id AND t.status = 'processing'
WHERE m.analyzed = FALSE AND m.content IS NOT NULL AND m.content != '' AND t.id IS NULL;

-- ============ 函数 ============
-- 更新时间戳函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 触发器
DROP TRIGGER IF EXISTS update_channels_updated_at ON channels;
CREATE TRIGGER update_channels_updated_at
    BEFORE UPDATE ON channels
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============ 统计函数 ============
CREATE OR REPLACE FUNCTION get_channel_stats(p_channel_id UUID)
RETURNS TABLE(
    total_messages BIGINT,
    analyzed_messages BIGINT,
    messages_today BIGINT,
    messages_this_week BIGINT,
    positive_count BIGINT,
    neutral_count BIGINT,
    negative_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_messages,
        COUNT(*) FILTER (WHERE m.analyzed) AS analyzed_messages,
        COUNT(*) FILTER (WHERE m.created_at >= CURRENT_DATE) AS messages_today,
        COUNT(*) FILTER (WHERE m.created_at >= CURRENT_DATE - INTERVAL '7 days') AS messages_this_week,
        COUNT(*) FILTER (WHERE m.sentiment = 'positive') AS positive_count,
        COUNT(*) FILTER (WHERE m.sentiment = 'neutral') AS neutral_count,
        COUNT(*) FILTER (WHERE m.sentiment = 'negative') AS negative_count
    FROM messages m
    WHERE m.channel_id = p_channel_id AND NOT m.is_deleted;
END;
$$ LANGUAGE plpgsql;
