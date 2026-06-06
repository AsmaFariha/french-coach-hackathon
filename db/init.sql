CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    raw_text TEXT NOT NULL,
    annotations JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cefr_level TEXT NOT NULL,
    family TEXT NOT NULL,
    covered_on DATE
);

CREATE TABLE IF NOT EXISTS exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID REFERENCES pages(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    prompt TEXT,
    model_answer TEXT,
    content JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Append-only participation ledger — never deduct points
CREATE TABLE IF NOT EXISTS points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reason TEXT NOT NULL,
    amount INT NOT NULL CHECK (amount > 0),
    earned_at TIMESTAMPTZ DEFAULT NOW()
);

-- PRIVATE table (defined here but never written by the public Space)
CREATE TABLE IF NOT EXISTS mistakes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concept_id TEXT REFERENCES concepts(id),
    category TEXT NOT NULL,
    user_answer TEXT,
    correct_answer TEXT,
    explanation TEXT,
    made_on TIMESTAMPTZ DEFAULT NOW()
);
