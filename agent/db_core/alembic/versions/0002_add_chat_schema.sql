-- 👤 Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR NOT NULL UNIQUE,
    email VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    full_name VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- 🤖 Agents table
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    description TEXT,
    config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- 🗃️ Chat Sessions Table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_agent_id ON chat_sessions (agent_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_agent ON chat_sessions (user_id, agent_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_active ON chat_sessions (user_id, is_active, updated_at DESC);

-- 📨 Chat History Table
CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    attachments TEXT[] DEFAULT ARRAY[]::TEXT[],
    parent_message_id UUID REFERENCES chat_history(id),
    token_count INTEGER DEFAULT 0,
    processing_time_ms INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history (session_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_timestamp ON chat_history (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_chat_history_role ON chat_history (role);
CREATE INDEX IF NOT EXISTS idx_chat_history_session_timestamp ON chat_history (session_id, timestamp);

-- 🧠 Chat Summaries Table
CREATE TABLE IF NOT EXISTS chat_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    keywords TEXT[] DEFAULT ARRAY[]::TEXT[],
    sentiment VARCHAR(20) DEFAULT 'neutral' CHECK (sentiment IN ('positive', 'negative', 'neutral')),
    message_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_summaries_session_id ON chat_summaries (session_id);
CREATE INDEX IF NOT EXISTS idx_chat_summaries_keywords ON chat_summaries USING GIN (keywords);
CREATE INDEX IF NOT EXISTS idx_chat_summaries_sentiment ON chat_summaries (sentiment);
CREATE INDEX IF NOT EXISTS idx_chat_summaries_updated_at ON chat_summaries (updated_at DESC);

-- 🤖 Update agents with chat fields
ALTER TABLE agents ADD COLUMN IF NOT EXISTS total_sessions INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS last_used TIMESTAMPTZ;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS avatar_url TEXT;

CREATE INDEX IF NOT EXISTS idx_agents_last_used ON agents (last_used DESC);
CREATE INDEX IF NOT EXISTS idx_agents_total_sessions ON agents (total_sessions DESC);

-- 📎 File Attachments Table
CREATE TABLE IF NOT EXISTS file_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_id UUID REFERENCES chat_history(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_path TEXT NOT NULL,
    upload_status VARCHAR(20) DEFAULT 'uploaded' CHECK (upload_status IN ('uploading', 'uploaded', 'processed', 'failed')),
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_file_attachments_user_id ON file_attachments (user_id);
CREATE INDEX IF NOT EXISTS idx_file_attachments_message_id ON file_attachments (message_id);
CREATE INDEX IF NOT EXISTS idx_file_attachments_status ON file_attachments (upload_status);
CREATE INDEX IF NOT EXISTS idx_file_attachments_created_at ON file_attachments (created_at DESC);

-- 📊 Chat Analytics Table
CREATE TABLE IF NOT EXISTS chat_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    event_date DATE GENERATED ALWAYS AS ((timestamp AT TIME ZONE 'UTC')::DATE) STORED
);


CREATE INDEX IF NOT EXISTS idx_chat_analytics_user_id ON chat_analytics (user_id);
CREATE INDEX IF NOT EXISTS idx_chat_analytics_agent_id ON chat_analytics (agent_id);
CREATE INDEX IF NOT EXISTS idx_chat_analytics_event_type ON chat_analytics (event_type);
CREATE INDEX IF NOT EXISTS idx_chat_analytics_timestamp ON chat_analytics (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_chat_analytics_user_date ON chat_analytics (user_id, event_date);


-- 🔁 Triggers
CREATE OR REPLACE FUNCTION update_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE chat_sessions SET updated_at = NOW() WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_update_session_timestamp'
    ) THEN
        CREATE TRIGGER trigger_update_session_timestamp
        AFTER INSERT ON chat_history
        FOR EACH ROW
        EXECUTE FUNCTION update_session_timestamp();
    END IF;
END $$;

CREATE OR REPLACE FUNCTION update_agent_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE agents SET last_used = NOW() WHERE id = NEW.agent_id;

    IF TG_OP = 'INSERT' THEN
        UPDATE agents SET total_sessions = total_sessions + 1
        WHERE id = NEW.agent_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_update_agent_stats'
    ) THEN
        CREATE TRIGGER trigger_update_agent_stats
        AFTER INSERT ON chat_sessions
        FOR EACH ROW
        EXECUTE FUNCTION update_agent_stats();
    END IF;
END $$;

CREATE OR REPLACE FUNCTION auto_generate_summary()
RETURNS TRIGGER AS $$
DECLARE
    msg_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO msg_count
    FROM chat_history WHERE session_id = NEW.session_id;

    IF msg_count % 10 = 0 THEN
        INSERT INTO chat_summaries (session_id, summary, message_count, keywords)
        VALUES (
            NEW.session_id,
            'Auto-generated summary - ' || msg_count || ' messages',
            msg_count,
            ARRAY[]::TEXT[]
        )
        ON CONFLICT (session_id) DO UPDATE SET
            summary = 'Updated auto-generated summary - ' || msg_count || ' messages',
            message_count = msg_count,
            updated_at = NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_auto_generate_summary'
    ) THEN
        CREATE TRIGGER trigger_auto_generate_summary
        AFTER INSERT ON chat_history
        FOR EACH ROW
        EXECUTE FUNCTION auto_generate_summary();
    END IF;
END $$;

-- 📊 Views
CREATE OR REPLACE VIEW recent_chat_sessions AS
SELECT 
    cs.*,
    a.name AS agent_name,
    a.avatar_url AS agent_avatar,
    (
        SELECT COUNT(*) FROM chat_history ch WHERE ch.session_id = cs.id
    ) AS message_count,
    (
        SELECT ch.content
        FROM chat_history ch
        WHERE ch.session_id = cs.id AND ch.role = 'user'
        ORDER BY ch.timestamp ASC
        LIMIT 1
    ) AS first_message
FROM chat_sessions cs
JOIN agents a ON cs.agent_id = a.id
WHERE cs.is_active = true
ORDER BY cs.updated_at DESC;

CREATE OR REPLACE VIEW chat_session_stats AS
SELECT 
    cs.id,
    cs.title,
    cs.created_at,
    cs.updated_at,
    COUNT(ch.id) AS total_messages,
    COUNT(CASE WHEN ch.role = 'user' THEN 1 END) AS user_messages,
    COUNT(CASE WHEN ch.role = 'assistant' THEN 1 END) AS assistant_messages,
    AVG(ch.token_count) AS avg_token_count,
    AVG(ch.processing_time_ms) AS avg_processing_time
FROM chat_sessions cs
LEFT JOIN chat_history ch ON cs.id = ch.session_id
GROUP BY cs.id;

CREATE OR REPLACE VIEW user_chat_analytics AS
SELECT 
    u.id AS user_id,
    u.username,
    COUNT(DISTINCT cs.id) AS total_sessions,
    COUNT(DISTINCT cs.agent_id) AS agents_used,
    COUNT(ch.id) AS total_messages,
    MAX(cs.updated_at) AS last_chat_date,
    AVG(session_stats.total_messages) AS avg_messages_per_session
FROM users u
LEFT JOIN chat_sessions cs ON u.id = cs.user_id
LEFT JOIN chat_history ch ON cs.id = ch.session_id
LEFT JOIN chat_session_stats session_stats ON cs.id = session_stats.id
WHERE cs.is_active = true
GROUP BY u.id, u.username;
