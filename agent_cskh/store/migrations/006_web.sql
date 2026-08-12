-- Kenh web (widget tren website/landing page).
--
-- Vi sao can bang rieng, khong dung `zalo_quota`: hai kenh co ban chat rui ro
-- KHAC HAN nhau. Zalo co tuong chan tu nhien — khach phai co tai khoan Zalo,
-- goi Basic chi 50 nguoi va 3000 tin/thang, nen chi phi API bi chan cung boi
-- chinh nen tang.
--
-- Website thi mo thang ra internet: khong dang nhap, khong gioi han nguoi, va
-- mot con bot cao co the goi lien tuc ca dem. O che do `ai` dieu do la TIEN
-- THAT chay ra khoi tai khoan chu shop. Nen kenh web phai co tran rieng, tinh
-- theo NGAY (khong phai thang) de neu bi cao thi thiet hai dung lai sau mot
-- ngay chu khong keo ca thang.

CREATE TABLE IF NOT EXISTS web_quota (
    ngay    TEXT PRIMARY KEY,           -- 'YYYY-MM-DD' theo UTC
    so_luot INTEGER NOT NULL DEFAULT 0  -- so luot khach gui, dem ca luot bi tu choi
);

-- Phien cua khach web. Khach vo danh: khong co user_id on dinh nhu Zalo, nen ta
-- tu sinh mot id va gui trong cookie.
--
-- Luu xuong dia (khong giu trong RAM) de khach quay lai sau khi khoi dong lai
-- may chu van con lich su, va de bao cao 20h dem duoc so khach web that.
CREATE TABLE IF NOT EXISTS web_phien (
    phien_id  TEXT PRIMARY KEY,
    tao_luc   TEXT NOT NULL,
    gap_cuoi  TEXT NOT NULL,
    ip_dau    TEXT,          -- chi de dieu tra lam dung; khong dung de nhan dang khach
    trang     TEXT           -- URL trang khach dang xem luc mo chat
);
