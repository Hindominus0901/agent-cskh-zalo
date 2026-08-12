"""Smoke test toan luong: su kien vao -> dieu phoi -> tra loi.

Chung minh phan noi day dung — dedup, rate limit, quota, phan quyen, im lang khi
handoff, va duong tra loi. Ha tang gia nam o conftest.py.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from agent_cskh.llm.base import LLMError, LLMResponse, ToolCall
from tests.conftest import make_event, run_one

# ---------------------------------------------------------------- test


class TestLuongCoBan:
    async def test_tin_nhan_thuong_duoc_tra_loi(self, rig) -> None:
        await run_one(rig, make_event("chào em"))
        assert rig["client"].texts == ["Dạ em nghe ạ."]

    async def test_co_bao_dang_nhap(self, rig) -> None:
        await run_one(rig, make_event())
        assert "typing" in rig["client"].actions

    async def test_luot_hien_tai_nam_cuoi_va_la_user(self, rig) -> None:
        await run_one(rig, make_event("báo giá thế nào"))
        messages = rig["provider"].calls[0]
        assert messages[-1].role == "user"
        assert messages[-1].text == "báo giá thế nào"

    async def test_nho_luot_truoc(self, rig) -> None:
        await run_one(rig, make_event("câu một", message_id="m1"))
        await run_one(rig, make_event("câu hai", message_id="m2"))
        messages = rig["provider"].calls[1]
        texts = [m.text for m in messages]
        assert "câu một" in texts
        assert texts[-1] == "câu hai"

    async def test_ghi_lai_ca_hai_chieu(self, rig) -> None:
        await run_one(rig, make_event())
        rows = await rig["db"].fetch_all("SELECT direction FROM messages ORDER BY id")
        assert [r["direction"] for r in rows] == ["in", "out"]


class TestIdempotency:
    async def test_cung_message_id_chi_xu_ly_mot_lan(self, rig) -> None:
        ev = make_event("xin chào", message_id="trung-lap")
        await run_one(rig, ev)
        await run_one(rig, ev)
        assert len(rig["client"].texts) == 1


class TestPhanQuyen:
    async def test_nguoi_la_khong_dung_duoc_lenh_noi_bo(self, rig) -> None:
        await run_one(rig, make_event("/trangthai"))
        # Roi xuong agent loop thay vi chay lenh -> nhan cau tra loi cua model.
        assert rig["client"].texts == ["Dạ em nghe ạ."]

    async def test_whoami_mo_cho_moi_nguoi(self, rig) -> None:
        await run_one(rig, make_event("/whoami"))
        out = rig["client"].texts[0]
        assert "user_id: u1" in out
        assert "chat_id: c1" in out

    async def test_prompt_cua_nguoi_la_khong_mo_kho_noi_bo(self, rig) -> None:
        """Bam vao BAO DAM, khong bam vao cau chu.

        Truoc day test nay tim dung mot cau — va no do ngay khi khoi `_STRANGER`
        duoc viet lai, du bao dam that van con nguyen. Test bam cau chu thi moi
        lan sua van phong deu thanh mot bao dong gia.
        """
        await run_one(rig, make_event("hỏi gì đó"))
        system = rig["provider"].systems[0]

        assert "Chỉ dùng thông tin công khai" in system
        assert "giá vốn" in system, "phai liet ke ro thu khong duoc tiet lo"
        # Khoi cua vai NOI BO khong duoc lot vao prompt cua nguoi la.
        assert "toàn bộ kho tri thức" not in system

    async def test_prompt_cua_nguoi_la_KHONG_bao_go_lenh(self, rig) -> None:
        """Bot khong bao gio duoc day khach go lenh — ho la khach hang."""
        await run_one(rig, make_event("hỏi gì đó"))
        assert "KHÔNG bảo ai gõ lệnh" in rig["provider"].systems[0]

    async def test_chu_bot_dung_duoc_lenh_noi_bo(self, rig, tmp_path, monkeypatch) -> None:
        rig["dispatcher"]._resolver._owners = {"u1"}  # noqa: SLF001
        await run_one(rig, make_event("/trangthai"))
        assert "Hạn mức Zalo" in rig["client"].texts[0]


class TestHandoff:
    async def test_bot_im_lang_khi_nguoi_that_tiep_quan(self, rig) -> None:
        await rig["repo"].ensure_conversation(make_event())
        await rig["repo"].set_state("c1", "HUMAN_ACTIVE")
        await run_one(rig, make_event("còn ai không"))
        assert rig["client"].texts == []

    async def test_van_ghi_lai_tin_khi_im_lang(self, rig) -> None:
        await rig["repo"].ensure_conversation(make_event())
        await rig["repo"].set_state("c1", "HUMAN_ACTIVE")
        await run_one(rig, make_event("còn ai không"))
        rows = await rig["db"].fetch_all("SELECT text FROM messages WHERE direction = 'in'")
        assert rows[-1]["text"] == "còn ai không"


class TestRateLimit:
    async def test_chan_khi_nhan_qua_nhanh(self, rig) -> None:
        for i in range(8):
            await run_one(rig, make_event(f"tin {i}", message_id=f"m{i}"))
        assert any("hơi nhanh" in t for t in rig["client"].texts)


class TestQuota:
    async def test_dem_ca_hai_chieu(self, rig) -> None:
        await run_one(rig, make_event())
        st = await rig["quota"].status()
        assert st.used == 2  # 1 vao + 1 ra

    async def test_mot_luot_dem_dung_hai_tin(self, rig) -> None:
        """Moi tin di chi duoc dem MOT lan, o ZaloClient.

        Bai hoc 07/08/2026: bon noi goi tu dem them ngoai callback cua
        ZaloClient, nen bo dem doc gap doi thuc te (sent=29 khi chi gui 13 tin).
        Phanh quota 80% vi the dap o ~40% that.
        """
        await run_one(rig, make_event())
        row = await rig["db"].fetch_one("SELECT sent, received FROM zalo_quota")

        assert len(rig["client"].sent) == 1, "chi co dung mot tin di"
        assert row["sent"] == 1, f"mot tin di phai dem 1, dang dem {row['sent']}"
        assert row["received"] == 1

    async def test_nhieu_luot_van_khong_troi_bo_dem(self, rig) -> None:
        for i in range(4):
            await run_one(rig, make_event(f"câu {i}", message_id=f"m{i}"))
        row = await rig["db"].fetch_one("SELECT sent FROM zalo_quota")

        assert row["sent"] == len(rig["client"].sent) == 4

    async def test_tu_choi_mem_khi_het_quota(self, rig) -> None:
        await rig["db"].execute(
            "INSERT INTO zalo_quota (period, sent, received) VALUES (?, 200, 0)",
            (datetime.now(tz=UTC).strftime("%Y-%m"),),
        )
        await run_one(rig, make_event("còn phục vụ không"))
        assert "quá tải" in rig["client"].texts[0]


class TestFileKhongHoTro:
    async def test_tra_loi_du_phong_khong_ton_token(self, rig) -> None:
        await run_one(rig, make_event(None, kind="unsupported"))
        assert "chưa nhận được file" in rig["client"].texts[0]
        assert rig["provider"].calls == []


class TestCongCu:
    """Vong lap tool chay that: model goi cong cu -> registry chay -> model tra loi."""

    async def test_nguoi_la_thay_dung_bo_cong_cu(self, rig) -> None:
        await run_one(rig, make_event("chào em"))
        assert set(rig["provider"].tools_seen[0]) == {
            "doc_trang",
            "tim_trang",
            # Quy trinh phuc vu khach la cong cu cua bot, khong phai bi mat noi
            # bo — va bot phai doc duoc no ngay tu luot dau voi nguoi la.
            "doc_skill",
            "chuyen_nguoi_that",
            "luu_lead",
            "trich_bien_lai",
            # Nguoi la tim lai duoc hoi thoai CUA CHINH HO, nhung khong ghi
            # nho duoc — ghi_nho bat dau tu vai student.
            "tim_hoi_thoai",
        }

    async def test_goi_cong_cu_khong_ton_tai_khong_lam_hong_luot(self, rig) -> None:
        rig["provider"].script = [[ToolCall(id="c1", name="khong_co_that", args={})]]
        await run_one(rig, make_event("hỏi gì đó"))
        assert rig["client"].texts == ["Dạ em nghe ạ."]

    async def test_luu_lead_ghi_vao_csdl(self, rig) -> None:
        rig["provider"].script = [
            [
                ToolCall(
                    id="c1",
                    name="luu_lead",
                    args={"ten": "Anh Minh", "sdt": "0901234567", "nhu_cau": "gói Standard"},
                )
            ]
        ]
        await run_one(rig, make_event("em tên Minh, sdt 0901234567"))
        rows = await rig["db"].fetch_all("SELECT name, phone, service, stage FROM leads")
        assert len(rows) == 1
        assert rows[0]["phone"] == "0901234567"
        assert rows[0]["stage"] == "moi"

    async def test_tu_choi_so_dien_thoai_sai_dinh_dang(self, rig) -> None:
        rig["provider"].script = [
            [ToolCall(id="c1", name="luu_lead", args={"ten": "X", "sdt": "12345"})]
        ]
        await run_one(rig, make_event("sdt em là 12345"))
        assert await rig["db"].fetch_val("SELECT count(*) FROM leads") == 0

    async def test_khong_luu_lead_khi_thieu_lien_he(self, rig) -> None:
        rig["provider"].script = [[ToolCall(id="c1", name="luu_lead", args={"ten": "Chỉ có tên"})]]
        await run_one(rig, make_event("em tên Minh"))
        assert await rig["db"].fetch_val("SELECT count(*) FROM leads") == 0

    async def test_lead_ghi_dung_chu_so_huu_cuoc_tro_chuyen(self, rig) -> None:
        """Model khong the ghi lead cho user khac — id lay tu ngu canh."""
        rig["provider"].script = [
            [
                ToolCall(
                    id="c1",
                    name="luu_lead",
                    args={"sdt": "0901234567", "user_id": "nguoi-khac", "chat_id": "chat-khac"},
                )
            ]
        ]
        await run_one(rig, make_event("sdt 0901234567", user_id="u1", chat_id="c1"))
        row = await rig["db"].fetch_one("SELECT user_id, chat_id FROM leads")
        assert row["user_id"] == "u1"
        assert row["chat_id"] == "c1"

    async def test_chuyen_nguoi_that_doi_trang_thai(self, rig) -> None:
        rig["provider"].script = [
            [
                ToolCall(
                    id="c1",
                    name="chuyen_nguoi_that",
                    args={"ly_do": "khach_yeu_cau", "tom_tat": "Khách xin gặp người tư vấn."},
                )
            ]
        ]
        await run_one(rig, make_event("cho em gặp người thật"))
        assert await rig["repo"].get_state("c1") == "HUMAN_PENDING"
        row = await rig["db"].fetch_one("SELECT reason, summary, status FROM handoffs")
        assert row["status"] == "pending"
        assert row["reason"] == "khach_yeu_cau"

    async def test_moi_lan_goi_cong_cu_deu_duoc_ghi_audit(self, rig) -> None:
        rig["provider"].script = [
            [ToolCall(id="c1", name="tim_trang", args={"tu_khoa": "bảng giá"})]
        ]
        await run_one(rig, make_event("bảng giá thế nào"))
        row = await rig["db"].fetch_one("SELECT tool_name, ok FROM tool_audit")
        assert row["tool_name"] == "tim_trang"
        assert row["ok"] == 1


class TestAnh:
    async def test_anh_duoc_dinh_kem_vao_luot(self, rig) -> None:
        await run_one(
            rig,
            make_event(None, kind="photo", photo_url="https://cdn.zalo.me/a.jpg"),
        )
        messages = rig["provider"].calls[0]
        assert messages[-1].image_urls == ["https://cdn.zalo.me/a.jpg"]


class TestNhipTimModel:
    """Vong lap phai bao cho scheduler biet model con song hay khong.

    Day la mat xich de dut nhat cua canh bao 07/08/2026: job canh model co viet
    dung den may cung vo dung neu vong lap khong bao gio cham vao health_model.
    """

    async def test_tra_loi_duoc_thi_nhip_tim_sach(self, rig) -> None:
        await run_one(rig, make_event("chào em"))
        assert rig["health_model"].so_loi_lien_tiep == 0
        assert rig["health_model"].lan_goi_cuoi_thanh_cong is not None

    async def test_model_hong_thi_dem_loi_va_giu_nguyen_nhan(self, rig) -> None:
        async def hong(*_a: Any, **_kw: Any) -> LLMResponse:
            raise LLMError("claude", "HTTP 401", retryable=False)

        rig["provider"].complete = hong
        await run_one(rig, make_event("chào em"))

        h = rig["health_model"]
        assert h.so_loi_lien_tiep == 1
        assert "401" in h.loi_cuoi

    async def test_khach_van_nhan_duoc_cau_du_phong(self, rig) -> None:
        """Model chet nhung khach khong duoc phep bi bo roi im lang."""

        async def hong(*_a: Any, **_kw: Any) -> LLMResponse:
            raise LLMError("claude", "HTTP 401", retryable=False)

        rig["provider"].complete = hong
        await run_one(rig, make_event("chào em"))

        assert rig["client"].sent, "khach khong nhan duoc gi ca"
        assert "trục trặc" in rig["client"].sent[-1][1]

    async def test_hong_roi_song_lai_thi_bo_dem_ve_khong(self, rig) -> None:
        goc = rig["provider"].complete

        async def hong(*_a: Any, **_kw: Any) -> LLMResponse:
            raise LLMError("claude", "HTTP 529", retryable=False)

        rig["provider"].complete = hong
        await run_one(rig, make_event("chào em", message_id="m1"))
        assert rig["health_model"].so_loi_lien_tiep == 1

        # message_id khac, neu khong lop chong trung se nuot luot thu hai.
        rig["provider"].complete = goc
        await run_one(rig, make_event("em ơi", message_id="m2"))
        assert rig["health_model"].so_loi_lien_tiep == 0


class TestKhongTuNhacChinhMinh:
    """Nguoi noi CHINH LA cho de leo thang — khong co ai o tren ho ca.

    Ngay 08/08/2026 chu bot hoi mot cau ngoai pham vi. Bot mo yeu cau ban giao,
    va canh bao "CO 1 KHACH DANG CHO NGUOI" duoc gui ve chinh chu bot, noi rang
    co khach dang cho — khach do la ho. Job nhac lap lai moi 2 tieng, hon chuc
    lan, va khong bao gio dung.
    """

    async def test_chu_bot_hoi_ngoai_pham_vi_thi_KHONG_sinh_yeu_cau_nao(self, rig) -> None:
        rig["provider"].script = [
            [
                ToolCall(
                    id="c1",
                    name="chuyen_nguoi_that",
                    args={"ly_do": "khong_chac", "tom_tat": "chủ bot hỏi cách chia sẻ bot"},
                )
            ]
        ]
        await run_one(rig, make_event("chia sẻ bot này cho người khác kiểu gì", user_id="admin"))

        assert await rig["db"].fetch_val("SELECT count(*) FROM handoffs", (), 0) == 0
        assert await rig["repo"].get_state("c1") == "BOT"

    async def test_khach_la_thi_VAN_sinh_yeu_cau_binh_thuong(self, rig) -> None:
        """Danh sach nay quan trong hon: sua mot lo hong ma bit luon duong chinh
        thi khach that se ngoi cho ma khong ai biet."""
        rig["provider"].script = [
            [
                ToolCall(
                    id="c1",
                    name="chuyen_nguoi_that",
                    args={"ly_do": "khach_yeu_cau", "tom_tat": "khách xin gặp người"},
                )
            ]
        ]
        await run_one(rig, make_event("cho em gặp người thật", user_id="khach_la"))

        assert await rig["db"].fetch_val("SELECT count(*) FROM handoffs", (), 0) == 1
        assert await rig["repo"].get_state("c1") == "HUMAN_PENDING"
