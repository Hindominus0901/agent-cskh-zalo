-- Migration 001 — so do ban dau
-- Luu y: KHONG co bang poll_state/offset. Zalo getUpdates khong ho tro offset;
-- idempotency dua hoan toan vao message_id (bang processed_updates).

-- ========== Dinh danh & quyen ==========
-- Bon vai, xep tang:
--   stranger  khach la — mac dinh, khong khai bao gi ca
--   student   KHACH DA DUOC NHAN DIEN: khach quen, thanh vien, hoc vien. Doc
--             them duoc muc `wiki/hocvien/`, va co bo nho dai han.
--   staff     nhan vien
--   owner     chu bot (dat qua OWNER_USER_IDS trong .env)
--
-- Ten `student` giu nguyen tu ban goc de khong phai doi ca ma tran quyen va
-- toan bo test di kem. Doc no la "khach quen" trong ngu canh CSKH.
--
-- Nang vai bang tay:
--   INSERT INTO principals (user_id, role, created_at, updated_at)
--   VALUES ('<user_id lay tu /whoami>', 'student', <now>, <now>);
CREATE TABLE IF NOT EXISTS principals (
    user_id      TEXT PRIMARY KEY,
    display_name TEXT,
    role         TEXT NOT NULL DEFAULT 'stranger'
                 CHECK (role IN ('stranger', 'student', 'staff', 'owner')),
    phone        TEXT,
    note         TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trusted_chats (
    chat_id         TEXT PRIMARY KEY,
    label           TEXT,
    role            TEXT NOT NULL DEFAULT 'staff' CHECK (role IN ('staff', 'owner')),
    is_alert_target INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL
);

-- ========== Hoi thoai ==========
CREATE TABLE IF NOT EXISTS conversations (
    chat_id       TEXT PRIMARY KEY,
    chat_type     TEXT NOT NULL DEFAULT 'unknown'
                  CHECK (chat_type IN ('private', 'group', 'unknown')),
    title         TEXT,
    session_id    TEXT,
    state         TEXT NOT NULL DEFAULT 'BOT'
                  CHECK (state IN ('BOT', 'HUMAN_PENDING', 'HUMAN_ACTIVE')),
    last_event_at TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY,
    chat_id    TEXT NOT NULL REFERENCES conversations (chat_id),
    message_id TEXT,
    session_id TEXT,
    user_id    TEXT,
    direction  TEXT NOT NULL CHECK (direction IN ('in', 'out')),
    kind       TEXT NOT NULL
               CHECK (kind IN ('text', 'photo', 'sticker', 'voice', 'system', 'unsupported')),
    text       TEXT,
    media_path TEXT,
    media_url  TEXT,
    -- Update goc. Vo gia khi debug schema Zalo — dung xoa.
    raw_json   TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_chat_time ON messages (chat_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id);

-- Idempotency: Zalo giao at-most-once va message_id la chuoi hex.
CREATE TABLE IF NOT EXISTS processed_updates (
    message_id   TEXT PRIMARY KEY,
    chat_id      TEXT,
    processed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_updates (processed_at);

-- ========== Bo nho ==========
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id    TEXT PRIMARY KEY,
    full_name  TEXT,
    company    TEXT,
    phone      TEXT,
    email      TEXT,
    industry   TEXT,
    notes      TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_facts (
    id                INTEGER PRIMARY KEY,
    user_id           TEXT NOT NULL,
    key               TEXT NOT NULL,
    value             TEXT NOT NULL,
    confidence        REAL NOT NULL DEFAULT 0.5,
    source_message_id INTEGER,
    created_at        TEXT NOT NULL,
    UNIQUE (user_id, key)
);

CREATE TABLE IF NOT EXISTS episodes (
    id         INTEGER PRIMARY KEY,
    session_id TEXT UNIQUE,
    chat_id    TEXT,
    user_id    TEXT,
    summary    TEXT NOT NULL,
    outcome    TEXT,
    started_at TEXT,
    ended_at   TEXT,
    indexed    INTEGER NOT NULL DEFAULT 0
);

-- ========== Kinh doanh ==========
CREATE TABLE IF NOT EXISTS leads (
    id             INTEGER PRIMARY KEY,
    user_id        TEXT,
    chat_id        TEXT,
    name           TEXT,
    phone          TEXT,
    email          TEXT,
    company        TEXT,
    service        TEXT,
    budget         TEXT,
    timeline       TEXT,
    stage          TEXT NOT NULL DEFAULT 'moi'
                   CHECK (stage IN ('moi', 'dang_tu_van', 'da_bao_gia', 'chot', 'mat')),
    source         TEXT NOT NULL DEFAULT 'zalo',
    notion_page_id TEXT,
    sheet_row      INTEGER,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS handoffs (
    id               INTEGER PRIMARY KEY,
    chat_id          TEXT NOT NULL,
    reason           TEXT NOT NULL,
    summary          TEXT NOT NULL,
    requested_at     TEXT NOT NULL,
    notified_chat_id TEXT,
    claimed_by       TEXT,
    claimed_at       TEXT,
    released_by      TEXT,
    released_at      TEXT,
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'active', 'released'))
);
CREATE INDEX IF NOT EXISTS idx_handoffs_open ON handoffs (chat_id, status);

-- Anh chuyen khoan: agent CHI trich xuat. verified_by chi nguoi dien.
CREATE TABLE IF NOT EXISTS payment_claims (
    id            INTEGER PRIMARY KEY,
    chat_id       TEXT,
    user_id       TEXT,
    media_path    TEXT,
    media_url     TEXT,
    amount        INTEGER,
    txn_time      TEXT,
    memo          TEXT,
    bank          TEXT,
    acct_last4    TEXT,
    matched_order TEXT,
    status        TEXT NOT NULL DEFAULT 'cho_doi_soat'
                  CHECK (status IN ('cho_doi_soat', 'khop', 'khong_khop', 'gia_mao')),
    verified_by   TEXT,
    verified_at   TEXT,
    created_at    TEXT NOT NULL
);

-- ========== Van hanh ==========
CREATE TABLE IF NOT EXISTS ingested_docs (
    id          INTEGER PRIMARY KEY,
    source_id   TEXT NOT NULL,
    external_id TEXT NOT NULL,
    doc_hash    TEXT NOT NULL,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    visibility  TEXT NOT NULL DEFAULT 'internal'
                CHECK (visibility IN ('public', 'internal')),
    indexed_at  TEXT NOT NULL,
    UNIQUE (source_id, external_id)
);

CREATE TABLE IF NOT EXISTS ingest_checkpoints (
    source_id   TEXT PRIMARY KEY,
    last_run_at TEXT,
    cursor      TEXT
);

CREATE TABLE IF NOT EXISTS tool_audit (
    id          INTEGER PRIMARY KEY,
    chat_id     TEXT,
    user_id     TEXT,
    tool_name   TEXT NOT NULL,
    args_json   TEXT,
    ok          INTEGER NOT NULL DEFAULT 1,
    error       TEXT,
    duration_ms INTEGER,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tool_audit_time ON tool_audit (created_at DESC);

CREATE TABLE IF NOT EXISTS llm_usage (
    id                INTEGER PRIMARY KEY,
    chat_id           TEXT,
    provider          TEXT NOT NULL,
    model             TEXT NOT NULL,
    input_tokens      INTEGER NOT NULL DEFAULT 0,
    output_tokens     INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd          REAL NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_llm_usage_time ON llm_usage (created_at DESC);

CREATE TABLE IF NOT EXISTS rate_limits (
    user_id    TEXT PRIMARY KEY,
    tokens     REAL NOT NULL,
    updated_at TEXT NOT NULL
);

-- Han muc Zalo: goi Basic 3000 tin/thang, dem ca hai chieu cho an toan.
CREATE TABLE IF NOT EXISTS zalo_quota (
    period    TEXT PRIMARY KEY,  -- 'YYYY-MM'
    sent      INTEGER NOT NULL DEFAULT 0,
    received  INTEGER NOT NULL DEFAULT 0,
    warned_at TEXT
);
