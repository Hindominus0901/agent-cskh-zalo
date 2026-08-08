-- Migration 005 — tri nho lau dai
--
-- Hai lo hong that duoc va o day:
--
--   1. Bot chi nhin thay 12 tin gan nhat (ConversationBuffer.DEFAULT_WINDOW).
--      Hoc vien quay lai sau hai tuan la nguoi la voi no — du toan bo tin nhan
--      van nam nguyen trong bang `messages`, khong ai tra.
--
--   2. Ba bang bo nho cua migration 001 — user_profiles, user_facts, episodes —
--      co so do nhung KHONG mot dong code nao dung. So do chet nguy hiem hon
--      khong co so do: nguoi doc tuong tinh nang da ton tai.
--
-- Cach lam theo Hermes Agent (Nous Research, 02/2026): FTS5 tren du lieu SAN CO
-- + bo nho do chinh agent soan, thay vi vector va embedding. Khong them mot phu
-- thuoc nao — FTS5 da co san trong SQLite di kem Python.

-- ========== 1. Tim kiem toan van tren tin nhan cu ==========
--
-- external content: KHONG nhan doi noi dung tin nhan. Bang ao chi giu chi muc,
-- van ban that van nam o `messages`. Doi lai la BAT BUOC phai co trigger dong
-- bo — thieu mot cai thoi la chi muc lech va truy van tra ve rac im lang.
--
-- remove_diacritics 2: "my pham" tim ra "my pham" co dau va nguoc lai. Cung
-- nguyen tac voi tim_trang trong kho tri thuc — nguoi Viet go dien thoai
-- thuong bo dau.
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5 (
    text,
    content = 'messages',
    content_rowid = 'id',
    tokenize = "unicode61 remove_diacritics 2"
);

CREATE TRIGGER IF NOT EXISTS messages_fts_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts (rowid, text) VALUES (new.id, new.text);
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts (messages_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_au AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts (messages_fts, rowid, text) VALUES ('delete', old.id, old.text);
    INSERT INTO messages_fts (rowid, text) VALUES (new.id, new.text);
END;

-- Lap chi muc cho toan bo tin nhan da co. Doc thang tu bang `messages`, nen
-- khong can liet ke cot va khong sai duoc.
INSERT INTO messages_fts (messages_fts) VALUES ('rebuild');

-- ========== 2. Bo nho do agent tu soan ==========
--
-- Thay cho user_profiles + user_facts. Ca hai deu rong (khong code nao ghi vao)
-- nen xoa la an toan; giu lai chi de lan sau lai co nguoi tuong chung dang chay.
-- user_profiles con trung lap voi `leads` va `hoc_vien` — bo han.
DROP TABLE IF EXISTS user_facts;
DROP TABLE IF EXISTS user_profiles;

-- RANG BUOC AN TOAN NAM O SO DO, khong o prompt:
--
--   user_id  — moi ghi nho gan cung MOT nguoi. Cong cu ghi khong co tham so
--              "ghi cho ai", nen mot nguoi khong the nhoi vao dau bot ve nguoi
--              khac. Do la khac biet quan trong nhat so voi Hermes: Hermes la
--              agent ca nhan mot nguoi dung dang tin, bot nay noi chuyen voi
--              nguoi la.
--
--   nguon_role — vai cua nguoi noi ra dieu nay, ghi lai tai thoi diem ghi. Loi
--              hoc vien tu ke KHONG duoc trinh bay ngang hang voi ghi chu cua
--              doi ngu khi nap vao prompt.
--
--   UNIQUE (user_id, khoa) — ghi de thay vi chong chat. Khong co duong nao de
--              mot nguoi lam phinh bo nho cua chinh minh vo han.
CREATE TABLE IF NOT EXISTS bo_nho (
    id            INTEGER PRIMARY KEY,
    user_id       TEXT NOT NULL,
    khoa          TEXT NOT NULL,
    gia_tri       TEXT NOT NULL,
    nguon_role    TEXT NOT NULL DEFAULT 'student'
                  CHECK (nguon_role IN ('stranger', 'student', 'staff', 'owner')),
    nguon_chat_id TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    UNIQUE (user_id, khoa)
);
CREATE INDEX IF NOT EXISTS idx_bo_nho_user ON bo_nho (user_id, updated_at DESC);

-- `episodes` giu nguyen: van chua co code dung, nhung no danh cho viec tom tat
-- phien bang LLM — mot buoc di sau, khong phai so do trung lap nhu hai bang tren.
