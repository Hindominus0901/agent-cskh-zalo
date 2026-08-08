-- Migration 008 — ghi lai nhung cau bot KHONG tra loi duoc
--
-- Kho tri thuc hien co 9 trang noi dung khoa. Hoi ngoai do thi bot tu choi —
-- dung nhu thiet ke — nhung KHONG GHI LAI GI CA. Nghia la chu bot khong bao gio
-- biet hoc vien dang hoi nhung gi ma bot khong dap duoc.
--
-- Do la nut that lon nhat cua ca he thong: bot huu ich dung bang do phu cua
-- kho, va khong ai biet cho nao con thieu.
--
-- Bang nay bien moi lan tu choi thanh MOT DONG TRONG DANH SACH VIEC. Bao cao
-- 20:00 doc no ra, gop cac cau giong nhau, va noi thang: "hom nay tu choi 6 cau,
-- 3 nguoi cung hoi ve buoi 7".
CREATE TABLE IF NOT EXISTS thieu_trang (
    id         INTEGER PRIMARY KEY,
    chat_id    TEXT NOT NULL,
    user_id    TEXT,
    -- Cau hoi NGUYEN VAN. Khong tom tat, khong dien giai: chu bot can doc dung
    -- chu hoc vien viet thi moi biet nen dat ten trang moi la gi.
    cau_hoi    TEXT NOT NULL,
    -- Bot doan chu de. Chi de gom nhom, khong phai su that.
    chu_de     TEXT,
    -- Da bo sung trang chua. Nguoi that danh dau, khong phai bot.
    da_xu_ly   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_thieu_trang_moi ON thieu_trang (da_xu_ly, created_at DESC);
