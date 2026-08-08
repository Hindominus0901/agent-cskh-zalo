"""Chia don cho tu van vien theo luot ("nhay don tu dong").

Van de goc: mot yeu cau ban giao roi vao kenh chung thi ba nguoi cung doc, va
"ai cung thay" nhanh chong thanh "ai cung tuong nguoi kia lam". Khach ngoi cho
trong khi khong ai thay minh co trach nhiem.

Sau tinh chat, moi cai ung voi mot cach hong da luong truoc:

  chia deu       — ba nguoi ba viec, khong ai om het
  dung mot nguoi — mot khach khong bao gio lam phien hai tu van vien cung luc
  nguoi moi vao  — duoc nhan don ngay, khong phai doi het mot vong
  nghi thi bo qua— tam nghi khong nhan don moi, nhung khong bi xoa
  khong ai thi van chay — danh sach rong -> quay ve bao kenh chung
  im lang thi leo — 2 lan khong nhan -> bao chu bot VA giao nguoi khac
"""

from __future__ import annotations

import pytest

from agent_cskh.config import Settings
from agent_cskh.health import Health
from agent_cskh.scheduler.runner import TOI_DA_NHAC_CHUNG, Scheduler
from agent_cskh.security import PrincipalResolver
from agent_cskh.store.repo.tu_van import TOI_DA_NHAC

CHU = "admin"


class ClientGia:
    def __init__(self) -> None:
        self.da_gui: list[tuple[str, str]] = []

    async def send_message(self, chat_id: str, text: str, **_kw) -> list[str]:
        self.da_gui.append((chat_id, text))
        return ["m1"]

    def toi(self, chat_id: str) -> list[str]:
        return [t for c, t in self.da_gui if c == chat_id]


async def _them_tvv(rig, ten: str, uid: str) -> None:
    """Ghi danh mot tu van vien VA cho ho vai staff.

    Vai staff la bat buoc, khong phai chi tiet trang tri: `la_kenh_noi_bo()` chan
    moi tin noi bo, va tin giao viec mang ten khach lan chat_id cua ho.
    """
    await rig["db"].execute(
        "INSERT INTO principals (user_id, display_name, role, created_at, updated_at) "
        "VALUES (?, ?, 'staff', '2026-01-01', '2026-01-01')",
        (uid, ten),
    )
    await rig["tu_van"].dang_ky(user_id=uid, chat_id=uid, ho_ten=ten)


async def _da_qua_30_phut(rig, chat_id: str) -> None:
    """Lui `giao_luc` ve qua khu. Job nhac chi dong toi viec da giao qua 30 phut —
    khong lui thi test dang kiem tra mot viec vua giao xong, va no im lang DUNG."""
    await rig["db"].execute(
        "UPDATE phan_cong SET giao_luc = '2020-01-01T00:00:00+00:00' WHERE chat_id = ?",
        (chat_id,),
    )


async def _handoff(rig, chat_id: str, tom_tat: str = "khách hỏi giá") -> int:
    return await rig["repo"].open_handoff(chat_id, reason="khong_chac", summary=tom_tat)


class TestChiaTheoLuot:
    async def test_ba_nguoi_ba_viec(self, rig) -> None:
        for i, ten in enumerate(("An", "Bình", "Cường")):
            await _them_tvv(rig, ten, f"tvv{i}")

        giao = []
        for i in range(3):
            h = await _handoff(rig, f"khach{i}")
            nguoi = await rig["tu_van"].giao_viec(handoff_id=h, chat_id=f"khach{i}")
            giao.append(nguoi.ho_ten)

        assert sorted(giao) == ["An", "Bình", "Cường"], f"chia lệch: {giao}"

    async def test_vong_thu_hai_quay_lai_tu_dau(self, rig) -> None:
        for i, ten in enumerate(("An", "Bình")):
            await _them_tvv(rig, ten, f"tvv{i}")

        giao = []
        for i in range(4):
            h = await _handoff(rig, f"khach{i}")
            giao.append((await rig["tu_van"].giao_viec(handoff_id=h, chat_id=f"khach{i}")).ho_ten)

        assert giao[0] != giao[1]
        assert giao[2] == giao[0]
        assert giao[3] == giao[1]

    async def test_nguoi_moi_vao_duoc_nhan_ngay(self, rig) -> None:
        """Khong phai doi het mot vong. Nguoi moi vao ma ngoi khong ba ngay thi
        ho se nghi he thong quen mat minh."""
        await _them_tvv(rig, "An", "tvv0")
        for i in range(3):
            h = await _handoff(rig, f"cu{i}")
            await rig["tu_van"].giao_viec(handoff_id=h, chat_id=f"cu{i}")

        await _them_tvv(rig, "Mới", "tvv_moi")
        h = await _handoff(rig, "khach_moi")
        assert (await rig["tu_van"].giao_viec(handoff_id=h, chat_id="khach_moi")).ho_ten == "Mới"

    async def test_tam_nghi_thi_khong_nhan_don_moi(self, rig) -> None:
        await _them_tvv(rig, "An", "tvv0")
        await _them_tvv(rig, "Bình", "tvv1")
        await rig["tu_van"].dat_dang_nhan("tvv0", bat=False)

        for i in range(3):
            h = await _handoff(rig, f"khach{i}")
            assert (
                await rig["tu_van"].giao_viec(handoff_id=h, chat_id=f"khach{i}")
            ).ho_ten == "Bình"

    async def test_tam_nghi_khong_phai_la_xoa(self, rig) -> None:
        await _them_tvv(rig, "An", "tvv0")
        await rig["tu_van"].dat_dang_nhan("tvv0", bat=False)
        assert len(await rig["tu_van"].danh_sach()) == 1
        await rig["tu_van"].dat_dang_nhan("tvv0", bat=True)
        h = await _handoff(rig, "k")
        assert await rig["tu_van"].giao_viec(handoff_id=h, chat_id="k") is not None

    async def test_MOT_khach_chi_lam_phien_MOT_nguoi(self, rig) -> None:
        """Job nhac chay 15 phut mot lan va co the chay chong len nhau."""
        await _them_tvv(rig, "An", "tvv0")
        await _them_tvv(rig, "Bình", "tvv1")

        h = await _handoff(rig, "khach")
        assert await rig["tu_van"].giao_viec(handoff_id=h, chat_id="khach") is not None
        assert await rig["tu_van"].giao_viec(handoff_id=h, chat_id="khach") is None

    async def test_chua_ai_dang_ky_thi_he_thong_van_chay(self, rig) -> None:
        """Danh sach rong tra ve None — nguoi goi quay ve bao kenh chung.
        Mot tinh nang chua duoc cau hinh khong duoc lam do he thong."""
        h = await _handoff(rig, "khach")
        assert await rig["tu_van"].giao_viec(handoff_id=h, chat_id="khach") is None


class TestNhanViec:
    async def test_go_nhan_thi_dong_phan_cong(self, rig) -> None:
        await _them_tvv(rig, "An", "tvv0")
        h = await _handoff(rig, "khach")
        await rig["tu_van"].giao_viec(handoff_id=h, chat_id="khach")

        assert await rig["tu_van"].danh_dau_da_nhan("khach") == 1
        assert await rig["tu_van"].dang_cho() == []

    async def test_ai_go_nhan_cung_duoc(self, rig) -> None:
        """Dong nghiep di ngang qua va nhan ho thi viec cung phai dong.
        Nhac tiep se day nguoi thu hai vao cung mot cuoc tro chuyen."""
        await _them_tvv(rig, "An", "tvv0")
        await _them_tvv(rig, "Bình", "tvv1")
        h = await _handoff(rig, "khach")
        await rig["tu_van"].giao_viec(handoff_id=h, chat_id="khach")

        await rig["tu_van"].danh_dau_da_nhan("khach")
        assert "khach" not in await rig["tu_van"].chat_dang_giao()


class TestLeoThang:
    """Nguoi duoc giao im lang thi khach van phai co nguoi."""

    def _sched(self, rig, client) -> Scheduler:
        return Scheduler(
            Settings(_env_file=None, owner_user_ids=[CHU], alert_chat_id=CHU),
            client=client,
            repo=rig["repo"],
            quota=rig["quota"],
            health=Health(ten="Zalo"),
            resolver=PrincipalResolver(Settings(_env_file=None, owner_user_ids=[CHU]), rig["db"]),
            tu_van=rig["tu_van"],
        )

    async def test_nhac_dung_nguoi_duoc_giao_chu_khong_keu_kenh_chung(self, rig) -> None:
        await _them_tvv(rig, "An", "tvv0")
        h = await _handoff(rig, "khach")
        await rig["tu_van"].giao_viec(handoff_id=h, chat_id="khach")
        await _da_qua_30_phut(rig, "khach")

        client = ClientGia()
        await self._sched(rig, client)._nhac_nguoi_duoc_giao()  # noqa: SLF001

        assert any("NHẮC LẦN 1" in t for t in client.toi("tvv0"))
        assert client.toi(CHU) == []
        # Ngay 08/08/2026 truy van `dang_cho` viet `pc.chat_id, tv.*` — hai bang
        # deu co cot `chat_id` va sqlite3.Row tra ve cai dau tien khop, nen tin
        # nhac viec (kem ten khach, kem chat_id) suyt di thang toi CHINH khach.
        assert client.toi("khach") == [], "tin noi bo gui nham cho khach"

    async def test_qua_nguong_thi_bao_chu_bot_VA_giao_nguoi_khac(self, rig) -> None:
        await _them_tvv(rig, "An", "tvv0")
        await _them_tvv(rig, "Bình", "tvv1")
        h = await _handoff(rig, "khach")
        dau = await rig["tu_van"].giao_viec(handoff_id=h, chat_id="khach")
        await _da_qua_30_phut(rig, "khach")

        client = ClientGia()
        sched = self._sched(rig, client)
        for _ in range(TOI_DA_NHAC + 1):
            await sched._nhac_nguoi_duoc_giao()  # noqa: SLF001

        # Chu bot duoc bao.
        assert any("KHÔNG PHẢN HỒI" in t for t in client.toi(CHU))
        # Va viec da sang nguoi khac — bao chu ma khong giao lai thi khach van
        # khong co ai, chu bot chi biet them mot tin xau.
        sau = "tvv1" if dau.user_id == "tvv0" else "tvv0"
        assert any("CHUYỂN SANG" in t for t in client.toi(sau))
        assert "khach" in await rig["tu_van"].chat_dang_giao()

    async def test_khong_con_ai_thi_van_bao_chu_bot(self, rig) -> None:
        """Mot nguoi duy nhat, im lang. Khong con ai de giao — nhung im lang
        luon la lua chon te nhat."""
        await _them_tvv(rig, "An", "tvv0")
        h = await _handoff(rig, "khach")
        await rig["tu_van"].giao_viec(handoff_id=h, chat_id="khach")
        await _da_qua_30_phut(rig, "khach")

        client = ClientGia()
        sched = self._sched(rig, client)
        for _ in range(TOI_DA_NHAC + 1):
            await sched._nhac_nguoi_duoc_giao()  # noqa: SLF001

        assert any("KHÔNG còn tư vấn viên nào rảnh" in t for t in client.toi(CHU))

    async def test_nhac_chung_BO_QUA_viec_da_co_nguoi_cam(self, rig) -> None:
        """Thieu buoc nay thi mot khach sinh ra hai tin — dung cai canh 'ai cung
        thay nen khong ai lam' ma ca tinh nang nay sinh ra de bo."""
        await _them_tvv(rig, "An", "tvv0")
        h = await _handoff(rig, "khach")
        await rig["tu_van"].giao_viec(handoff_id=h, chat_id="khach")
        # Day thoi diem yeu cau lui ve qua khu de job nhac chung thay no "treo lau".
        await rig["db"].execute(
            "UPDATE handoffs SET requested_at = '2020-01-01T00:00:00+00:00' WHERE id = ?", (h,)
        )

        client = ClientGia()
        await self._sched(rig, client)._nhac_handoff()  # noqa: SLF001

        assert not any("CÓ 1 KHÁCH ĐANG CHỜ" in t for t in client.toi(CHU))


class TestKhongGuiCuaKhachChoDiaChiLa:
    async def test_tu_van_vien_khong_phai_kenh_noi_bo_thi_khong_gui(self, rig) -> None:
        """Ban ghi cu — nguoi da nghi viec, hoac chat_id go nham — khong duoc
        thanh duong ro. Tin giao viec mang ten khach va chat_id cua ho."""
        # Ghi danh THANG vao repo, bo qua buoc cho vai staff.
        await rig["tu_van"].dang_ky(user_id="nguoi_la", chat_id="nguoi_la", ho_ten="Người lạ")
        h = await _handoff(rig, "khach")

        client = ClientGia()
        sched = Scheduler(
            Settings(_env_file=None, owner_user_ids=[CHU], alert_chat_id=CHU),
            client=client,
            repo=rig["repo"],
            quota=rig["quota"],
            health=Health(ten="Zalo"),
            resolver=PrincipalResolver(Settings(_env_file=None, owner_user_ids=[CHU]), rig["db"]),
            tu_van=rig["tu_van"],
        )
        await rig["tu_van"].giao_viec(handoff_id=h, chat_id="khach")
        await _da_qua_30_phut(rig, "khach")
        await sched._nhac_nguoi_duoc_giao()  # noqa: SLF001

        assert client.toi("nguoi_la") == []


@pytest.mark.parametrize("lenh", ["nhantuvan", "nghituvan", "dstuvan", "xoatuvan"])
def test_lenh_tu_van_deu_la_noi_bo(lenh: str) -> None:
    """Khong lenh nao trong nhom nay duoc mo cho hoc vien hay nguoi la."""
    from agent_cskh.commands.router import COMMANDS

    assert COMMANDS[lenh][1] in ("staff", "owner")


class TestTranNhacChung:
    """Nhac phai co tran, va tran phai song qua khoi dong lai.

    Truoc 08/08/2026 bo dem nam trong `Scheduler._da_nhac` — mot dict TRONG BO
    NHO. Hai he qua, ca hai deu da xay ra that:

      Khong co tran. Mot yeu cau treo tu 07/08 15:34 den 08/08 13:29 sinh ra hon
      chuc canh bao giong het nhau, va se tiep tuc mai mai.

      Khoi dong lai la quen sach. Trong mot ngay sua nhieu, bot khoi dong lai
      vai lan, moi lan mot canh bao nua ngay lap tuc.

    Canh bao lap lai ma khong ai xu ly duoc thi khong con la canh bao — no thanh
    nhieu, roi nguoi ta tat thong bao di, ke ca nhung canh bao that su quan trong.
    """

    def _sched(self, rig, client) -> Scheduler:
        """Dung MOT Scheduler MOI moi lan — mo phong dung viec khoi dong lai bot."""
        return Scheduler(
            Settings(_env_file=None, owner_user_ids=[CHU], alert_chat_id=CHU),
            client=client,
            repo=rig["repo"],
            quota=rig["quota"],
            health=Health(ten="Zalo"),
            resolver=PrincipalResolver(Settings(_env_file=None, owner_user_ids=[CHU]), rig["db"]),
        )

    async def _treo_tu_lau(self, rig, chat_id: str = "khach") -> int:
        h = await rig["repo"].open_handoff(chat_id, reason="khong_chac", summary="khách hỏi giá")
        await rig["db"].execute(
            "UPDATE handoffs SET requested_at = '2020-01-01T00:00:00+00:00' WHERE id = ?", (h,)
        )
        return h

    async def _het_gian_cach(self, rig) -> None:
        """Xoa moc nhac cuoi de lan chay sau khong bi gian cach 2 tieng chan lai."""
        await rig["db"].execute("UPDATE handoffs SET nhac_cuoi_luc = NULL")

    async def test_nhac_dung_ba_lan_roi_thoi(self, rig) -> None:
        await self._treo_tu_lau(rig)
        client = ClientGia()

        for _ in range(8):
            # Scheduler MOI moi vong: neu bo dem con nam trong bo nho thi vong
            # nao cung se nhac lai, va test nay se do.
            await self._sched(rig, client)._nhac_handoff()  # noqa: SLF001
            await self._het_gian_cach(rig)

        assert len(client.toi(CHU)) == TOI_DA_NHAC_CHUNG

    async def test_lan_cuoi_noi_ro_la_se_thoi_nhac(self, rig) -> None:
        """Im lang dot ngot khong khac gi hong. Phai noi thang la thoi."""
        await self._treo_tu_lau(rig)
        client = ClientGia()
        for _ in range(TOI_DA_NHAC_CHUNG + 2):
            await self._sched(rig, client)._nhac_handoff()  # noqa: SLF001
            await self._het_gian_cach(rig)

        cuoi = client.toi(CHU)[-1]
        assert "LẦN NHẮC CUỐI" in cuoi
        assert "sẽ không nhắc việc này nữa" in cuoi

    async def test_gian_cach_hai_tieng_van_duoc_giu(self, rig) -> None:
        """Job chay moi 15 phut. Khong co gian cach thi mot yeu cau se an het
        tran trong 45 phut."""
        await self._treo_tu_lau(rig)
        client = ClientGia()
        for _ in range(4):
            await self._sched(rig, client)._nhac_handoff()  # noqa: SLF001

        assert len(client.toi(CHU)) == 1

    async def test_yeu_cau_moi_thi_chua_nhac_voi(self, rig) -> None:
        await rig["repo"].open_handoff("khach", reason="khong_chac", summary="vừa mới")
        client = ClientGia()
        await self._sched(rig, client)._nhac_handoff()  # noqa: SLF001
        assert client.toi(CHU) == []

    async def test_don_yeu_cau_treo_qua_bay_ngay(self, rig) -> None:
        """`/baocao` va bang theo doi deu dem 'khach dang cho nguoi'. Mot xac
        chet ba tuan tuoi lam ca con so do mat nghia."""
        await self._treo_tu_lau(rig, "cu")
        await rig["repo"].open_handoff("moi", reason="khong_chac", summary="mới hôm nay")

        assert await rig["repo"].dong_handoff_qua_han() == 1
        con_lai = await rig["repo"].pending_handoffs()
        assert [h["chat_id"] for h in con_lai] == ["moi"]


class TestChiaLuotTatDinh:
    """Chia luot phai TAT DINH, khong phu thuoc dong ho.

    Ngay 08/08/2026 `_nguoi_toi_luot` xep theo `lan_cuoi_giao` — mot moc thoi
    gian. Tren Windows `datetime.now()` chi phan giai khoang 15ms, nen hai lan
    giao sat nhau nhan dung cung mot moc, thu tu sup ve `id ASC`, va nguoi co id
    nho nhat duoc giao lien tiep.

    Test cu bat duoc no nhung chi khoang 40% so lan chay. Mot test chap chon o
    day khong phai test hong — no la HE THONG khong tat dinh, va tren may that
    thi hai khach nhan tin cach nhau vai mili giay se cung roi vao mot nguoi.
    """

    async def test_chia_deu_ke_ca_khi_dong_ho_dung_yen(self, rig) -> None:
        """Ep MOI ban ghi ve cung mot moc thoi gian — mo phong dong ho tho.

        Truoc khi sua, test nay do 100%.
        """
        for i, ten in enumerate(("An", "Bình", "Cường")):
            await _them_tvv(rig, ten, f"tvv{i}")

        giao = []
        for i in range(6):
            h = await _handoff(rig, f"khach{i}")
            nguoi = await rig["tu_van"].giao_viec(handoff_id=h, chat_id=f"khach{i}")
            giao.append(nguoi.ho_ten)
            # Dong ho dung yen: moi nguoi deu co lan_cuoi_giao y het nhau.
            await rig["db"].execute(
                "UPDATE tu_van_vien SET lan_cuoi_giao = '2026-01-01T00:00:00+00:00' "
                "WHERE lan_cuoi_giao IS NOT NULL"
            )

        from collections import Counter

        assert Counter(giao) == {"An": 2, "Bình": 2, "Cường": 2}, f"chia lệch: {giao}"

    async def test_luot_thu_luon_tang(self, rig) -> None:
        """Bo dem phai lon hon MOI so da cap, khong chi lon hon so cua chinh no."""
        for i, ten in enumerate(("An", "Bình")):
            await _them_tvv(rig, ten, f"tvv{i}")
        for i in range(4):
            h = await _handoff(rig, f"k{i}")
            await rig["tu_van"].giao_viec(handoff_id=h, chat_id=f"k{i}")

        so = [
            r["luot_thu"]
            for r in await rig["db"].fetch_all("SELECT luot_thu FROM tu_van_vien ORDER BY luot_thu")
        ]
        assert so == sorted(set(so)), f"số lượt trùng nhau: {so}"
