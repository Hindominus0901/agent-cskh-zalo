"""Doc anh: tu tai byte, khong dua URL cho model tu tai.

BOT CHUA BAO GIO DOC DUOC ANH cho toi 08/08/2026. Khong ai biet, vi khong co
test nao cham vao duong nay va CSDL that khong co lay mot tam anh.

Kiem chung truc tiep tren API:

    URL httpbin      -> HTTP 400 "Unable to download the file"
    URL Wikipedia    -> HTTP 400 "Unable to download the file"
    URL placehold.co -> HTTP 400 "disallowed by the website's robots.txt"
    Cung tam anh, gui base64 -> HTTP 200, model doc dung chu trong anh

Cau bao loi cua placehold.co la manh moi: bo tai cua Anthropic TON TRONG
robots.txt. CDN Zalo chan crawler va URL anh co chu ky het han, nen duong
`source.type = "url"` khong phai thinh thoang hong — no khong bao gio chay.

Hau qua truoc ban va: doc bien lai chuyen khoan, xem anh san pham, cham bai tu
anh chup man hinh — tat ca deu hong, va dau vet duy nhat la cau du phong "he
thong dang truc trac".
"""

from __future__ import annotations

import base64

import pytest

from agent_cskh.llm.anh import TOI_DA_BYTE, khoi_anh, xoa_dem

# PNG 1x1 hop le, nho nhat co the.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
GIF = b"GIF89a" + b"\x00" * 20
WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 12
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20


@pytest.fixture(autouse=True)
def _sach():
    xoa_dem()
    yield
    xoa_dem()


class _PhanHoi:
    def __init__(self, noi_dung: bytes, ct: str = "image/png", ma: int = 200) -> None:
        self.content = noi_dung
        self.headers = {"content-type": ct}
        self._ma = ma

    def raise_for_status(self) -> None:
        if self._ma >= 400:
            import httpx

            raise httpx.HTTPStatusError("loi", request=None, response=None)  # type: ignore[arg-type]


def _gia_lap(monkeypatch, phan_hoi) -> None:
    """Thay httpx.AsyncClient de khong goi mang trong test."""
    import agent_cskh.llm.anh as mod

    class ClientGia:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, **kw):
            if isinstance(phan_hoi, Exception):
                raise phan_hoi
            return phan_hoi

    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda **kw: ClientGia())


class TestGuiByteChuKhongGuiURL:
    async def test_tra_ve_khoi_base64(self, monkeypatch) -> None:
        """`source.type` PHAI la base64. Doi lai thanh "url" la quay ve dung cai
        loi da lam bot mu suot tu dau."""
        _gia_lap(monkeypatch, _PhanHoi(PNG))
        khoi = await khoi_anh("https://vidu.com/a.png")

        assert khoi is not None
        assert khoi["source"]["type"] == "base64"
        assert khoi["source"]["media_type"] == "image/png"
        assert base64.standard_b64decode(khoi["source"]["data"]) == PNG

    @pytest.mark.parametrize(
        ("du_lieu", "mong_doi"),
        [(PNG, "image/png"), (GIF, "image/gif"), (WEBP, "image/webp"), (JPEG, "image/jpeg")],
    )
    async def test_nhan_dang_bang_BYTE_dau_file(self, monkeypatch, du_lieu, mong_doi) -> None:
        """Zalo tra `application/octet-stream` cho anh kha thuong xuyen. Tin vao
        content-type thi mot phan anh bi tu choi oan."""
        _gia_lap(monkeypatch, _PhanHoi(du_lieu, ct="application/octet-stream"))
        khoi = await khoi_anh("https://vidu.com/a")
        assert khoi is not None
        assert khoi["source"]["media_type"] == mong_doi

    async def test_dinh_dang_khong_phai_anh_thi_tu_choi(self, monkeypatch) -> None:
        _gia_lap(monkeypatch, _PhanHoi(b"%PDF-1.4 khong phai anh", ct="application/pdf"))
        assert await khoi_anh("https://vidu.com/a.pdf") is None

    async def test_anh_qua_nang_thi_tu_choi(self, monkeypatch) -> None:
        """Vuot tran cua Anthropic thi API tu choi CA yeu cau — mat luon phan chu."""
        _gia_lap(monkeypatch, _PhanHoi(PNG + b"\x00" * (TOI_DA_BYTE + 1)))
        assert await khoi_anh("https://vidu.com/to.png") is None

    async def test_tai_hong_thi_tra_None_chu_khong_no(self, monkeypatch) -> None:
        import httpx

        _gia_lap(monkeypatch, httpx.ConnectError("khong noi duoc"))
        assert await khoi_anh("https://vidu.com/a.png") is None

    @pytest.mark.parametrize("u", ["", "khong-phai-url", "file:///etc/passwd", "ftp://a/b.png"])
    async def test_chi_nhan_http(self, u: str) -> None:
        assert await khoi_anh(u) is None


class TestBoNhoDem:
    """Cua so hoi thoai 12 tin duoc dung LAI o moi luot.

    Khong nho thi mot tam anh 3MB bi tai lai moi luot — cham va ton bang thong,
    va voi URL Zalo co chu ky thi lan sau con co the da het han.
    """

    async def test_lan_hai_khong_tai_lai(self, monkeypatch) -> None:
        so_lan = {"n": 0}
        import agent_cskh.llm.anh as mod

        class ClientGia:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, url, **kw):
                so_lan["n"] += 1
                return _PhanHoi(PNG)

        monkeypatch.setattr(mod.httpx, "AsyncClient", lambda **kw: ClientGia())

        for _ in range(4):
            await khoi_anh("https://vidu.com/a.png")
        assert so_lan["n"] == 1

    async def test_dem_co_tran(self, monkeypatch) -> None:
        """Khong co tran thi mot cuoc tro chuyen dai lam phinh bo nho vo han."""
        from agent_cskh.llm.anh import TOI_DA_DEM, _dem

        _gia_lap(monkeypatch, _PhanHoi(PNG))
        for i in range(TOI_DA_DEM + 5):
            await khoi_anh(f"https://vidu.com/{i}.png")
        assert len(_dem) == TOI_DA_DEM
