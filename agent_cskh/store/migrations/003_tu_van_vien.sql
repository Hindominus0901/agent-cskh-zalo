-- Migration 006 — chia don cho tu van vien theo luot ("nhay don tu dong")
--
-- Truoc migration nay, moi yeu cau ban giao deu roi vao MOT kenh canh bao chung.
-- Ba nguoi cung doc, va "ai cung thay" nhanh chong thanh "ai cung tuong nguoi
-- kia lam". Khach ngoi cho trong khi khong ai thay minh co trach nhiem.
--
-- Cach chua: moi yeu cau co DUNG MOT nguoi duoc giao, co ten, va co dong ho.

-- ========== Tu van vien ==========
--
-- Dang ky bang /nhantuvan chay TRONG CHAT RIENG cua chinh nguoi do — cung khuon
-- voi /datkenhcanhbao. Ly do khong cho chu bot them ho bang user_id: nen tang
-- Zalo khong tra chat_id tu user_id, nen mot ban ghi them tay se co chat_id
-- doan mo, va tin dau tien gui di se roi vao hu vo (hoac te hon, vao nham chat).
-- Bat ho tu go mot lenh la cach duy nhat CHUNG MINH duoc dia chi nhan.
CREATE TABLE IF NOT EXISTS tu_van_vien (
    id            INTEGER PRIMARY KEY,
    user_id       TEXT NOT NULL UNIQUE,
    chat_id       TEXT NOT NULL,
    ho_ten        TEXT NOT NULL,
    -- 0 = tam nghi, khong nhan don moi. Nghi phep khong phai la nghi viec, nen
    -- tat tam thoi phai de hon xoa han.
    dang_nhan     INTEGER NOT NULL DEFAULT 1,
    -- Chia theo luot duoc thuc hien bang "AI LAU NHAT CHUA DUOC GIAO", khong
    -- phai bang bo dem chia du. Bo dem se lech ngay khi co nguoi vao, nguoi ra,
    -- hoac nguoi xin nghi mot buoi; cach nay tu chinh lai.
    lan_cuoi_giao TEXT,
    so_da_giao    INTEGER NOT NULL DEFAULT 0,

    -- CHIA LUOT BANG BO DEM, KHONG BANG DONG HO.
    --
    -- Neu xep thu tu theo `lan_cuoi_giao` (mot moc ISO) thi tren Windows,
    -- `datetime.now()` chi phan giai khoang 15ms — hai lan giao sat nhau nhan
    -- DUNG CUNG MOT moc. Luc do thu tu sup ve `id ASC`, va nguoi co id nho nhat
    -- duoc giao lien tiep: round-robin bien thanh "ai vao truoc om het".
    --
    -- Phat hien bang mot test chap chon, do khoang 40% so lan chay. Test chap
    -- chon o day khong phai test hong, ma la HE THONG khong tat dinh — va no se
    -- hong y het tren may that khi hai khach nhan tin cach nhau vai mili giay.
    --
    -- Bo dem thi khong co do phan giai: moi lan giao la mot so nguyen moi, lon
    -- hon moi so da cap. Khong phu thuoc dong ho, khong phu thuoc he dieu hanh.
    --
    -- NULL = chua bao gio duoc giao, va `luot_thu IS NOT NULL` trong ORDER BY
    -- dat ho len dau — nguoi moi vao doi nhan don ngay, khong phai doi het vong.
    luot_thu      INTEGER,

    created_at    TEXT NOT NULL
);

-- ========== Phan cong ==========
CREATE TABLE IF NOT EXISTS phan_cong (
    id             INTEGER PRIMARY KEY,
    handoff_id     INTEGER NOT NULL,
    tu_van_vien_id INTEGER NOT NULL REFERENCES tu_van_vien (id),
    chat_id        TEXT NOT NULL,
    giao_luc       TEXT NOT NULL,
    nhac_lan       INTEGER NOT NULL DEFAULT 0,
    trang_thai     TEXT NOT NULL DEFAULT 'da_giao'
                   CHECK (trang_thai IN ('da_giao', 'da_nhan', 'leo_thang', 'huy')),
    nhan_luc       TEXT
);

-- Mot yeu cau ban giao chi duoc giao cho MOT nguoi TAI MOT THOI DIEM. Job nhac
-- chay 15 phut mot lan va co the chay chong len nhau — thieu rang buoc nay thi
-- mot khach se lam phien ba tu van vien cung luc.
--
-- Index TUNG PHAN (chi tren 'da_giao') chu khong phai tren ca bang: khi nguoi
-- dau khong phan hoi, dong cu chuyen sang 'leo_thang' va roi khoi index, nho
-- vay giao lai cho nguoi khac duoc ma khong phai xoa lich su.
CREATE UNIQUE INDEX IF NOT EXISTS idx_phan_cong_dang_giao
    ON phan_cong (handoff_id) WHERE trang_thai = 'da_giao';
CREATE INDEX IF NOT EXISTS idx_phan_cong_mo ON phan_cong (trang_thai, giao_luc);
