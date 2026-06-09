CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    raw_text TEXT NOT NULL,
    annotations JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,   -- category, summary, tags (for smart browser)
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pages_user ON pages(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pages_metadata ON pages USING gin(metadata);

CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cefr_level TEXT NOT NULL,
    family TEXT NOT NULL,
    covered_on DATE
);

CREATE TABLE IF NOT EXISTS exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    page_id UUID REFERENCES pages(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    prompt TEXT,
    model_answer TEXT,
    content JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_exercises_user ON exercises(user_id, created_at DESC);

-- Append-only participation ledger — never deduct points
CREATE TABLE IF NOT EXISTS points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    amount INT NOT NULL CHECK (amount > 0),
    earned_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_points_user ON points(user_id, earned_at DESC);

-- PRIVATE table (defined here but never written by the public Space)
CREATE TABLE IF NOT EXISTS mistakes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    concept_id TEXT REFERENCES concepts(id),
    category TEXT NOT NULL,
    user_answer TEXT,
    correct_answer TEXT,
    explanation TEXT,
    made_on TIMESTAMPTZ DEFAULT NOW()
);
