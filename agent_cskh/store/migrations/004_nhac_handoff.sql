-- Migration 007 — dem so lan da nhac mot yeu cau ban giao
--
-- Truoc migration nay, bo dem nam trong `Scheduler._da_nhac` — mot dict TRONG
-- BO NHO. Hai he qua, ca hai deu da xay ra that:
--
--   1. Khong co tran. Mot yeu cau treo tu 07/08 15:34 den 08/08 13:29 da sinh
--      ra hon chuc canh bao "CO 1 KHACH DANG CHO NGUOI", cach nhau 2 tieng, va
--      se tiep tuc mai mai. Canh bao lap lai ma khong ai xu ly duoc thi khong
--      con la canh bao — no thanh nhieu, va roi nguoi ta tat thong bao di.
--
--   2. Khoi dong lai la quen sach. Trong mot ngay sua nhieu, bot khoi dong lai
--      vai lan, va moi lan la mot canh bao nua ngay lap tuc.
--
-- Dem trong CSDL thi ca hai bien mat.
ALTER TABLE handoffs ADD COLUMN so_lan_nhac INTEGER NOT NULL DEFAULT 0;
ALTER TABLE handoffs ADD COLUMN nhac_cuoi_luc TEXT;

-- Cac yeu cau dang treo tu truoc deu da bi nhac qua nhieu roi. Dat thang len
-- tran de chung im ngay, thay vi duoc "tang" them ba lan nua.
UPDATE handoffs SET so_lan_nhac = 99 WHERE status = 'pending';
