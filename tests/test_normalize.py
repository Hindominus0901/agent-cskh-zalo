"""Kiem tra normalize() — tuyen phong thu duy nhat truoc thay doi schema cua Zalo.

Mau `TEXT_PRIVATE` la vi du NGUYEN VAN duy nhat Zalo cong bo (docs/webhook).
Cac mau con lai la gia dinh, se duoc thay bang fixture that sau khi chay
scripts/dump_update.py.
"""

from __future__ import annotations

from agent_cskh.transport.base import InboundEvent
from agent_cskh.transport.normalize import normalize
from agent_cskh.transport.zalo_client import split_text

TEXT_PRIVATE = {
    "ok": True,
    "result": {
        "message": {
            "from": {"id": "6ede9afa66b88fe6d6a9", "display_name": "Ted", "is_bot": False},
            "chat": {"id": "6ede9afa66b88fe6d6a9", "chat_type": "PRIVATE"},
            "text": "Xin chao",
            "message_id": "2d758cb5e222177a4e35",
            "date": 1750316131602,
        },
        "event_name": "message.text.received",
    },
}


def _ev(payload: dict) -> InboundEvent:
    event = normalize(payload)
    assert event is not None
    return event


class TestTextMessage:
    def test_mau_chinh_thuc(self) -> None:
        e = _ev(TEXT_PRIVATE)
        assert e.event_id == "2d758cb5e222177a4e35"
        assert e.kind == "text"
        assert e.chat_id == "6ede9afa66b88fe6d6a9"
        assert e.user_id == "6ede9afa66b88fe6d6a9"
        assert e.display_name == "Ted"
        assert e.text == "Xin chao"
        assert e.is_bot is False

    def test_chat_type_dung_khoa_chat_type_khong_phai_type(self) -> None:
        e = _ev(TEXT_PRIVATE)
        assert e.chat_type == "private"
        assert e.is_private

    def test_date_la_mili_giay(self) -> None:
        # 1750316131602 ms -> 2025-06-19, KHONG phai nam 57398
        e = _ev(TEXT_PRIVATE)
        assert e.sent_at is not None
        assert e.sent_at.year == 2025

    def test_giu_raw_de_debug(self) -> None:
        assert _ev(TEXT_PRIVATE).raw == TEXT_PRIVATE


class TestAnh:
    """Docs ghi `photo`, SDK TS doc `photo_url` — phai chap nhan CA HAI."""

    def _payload(self, field: str) -> dict:
        return {
            "ok": True,
            "result": {
                "event_name": "message.image.received",
                "message": {
                    "from": {"id": "u1", "display_name": "Minh", "is_bot": False},
                    "chat": {"id": "u1", "chat_type": "PRIVATE"},
                    field: "https://cdn.zalo.me/abc.jpg",
                    "caption": "bien lai cua em",
                    "message_id": "m1",
                    "date": 1750316131602,
                },
            },
        }

    def test_truong_photo(self) -> None:
        e = _ev(self._payload("photo"))
        assert e.kind == "photo"
        assert e.photo is not None
        assert e.photo.url == "https://cdn.zalo.me/abc.jpg"

    def test_truong_photo_url(self) -> None:
        e = _ev(self._payload("photo_url"))
        assert e.photo is not None
        assert e.photo.url == "https://cdn.zalo.me/abc.jpg"

    def test_caption_thanh_text_de_agent_doc_duoc(self) -> None:
        e = _ev(self._payload("photo"))
        assert e.text == "bien lai cua em"
        assert e.photo is not None
        assert e.photo.caption == "bien lai cua em"


class TestNhom:
    def test_chat_type_group(self) -> None:
        payload = {
            "ok": True,
            "result": {
                "event_name": "message.text.received",
                "message": {
                    "from": {"id": "u2", "display_name": "Lan", "is_bot": False},
                    "chat": {"id": "g99", "chat_type": "GROUP"},
                    "text": "@bot bao gia the nao",
                    "message_id": "m2",
                    "date": 1750316131602,
                },
            },
        }
        e = _ev(payload)
        assert e.chat_type == "group"
        assert not e.is_private
        # Trong nhom, chat_id KHAC user_id — tra loi phai gui vao chat_id.
        assert e.chat_id == "g99"
        assert e.user_id == "u2"


class TestFailSoft:
    """Bot khong duoc chet vi mot tin nhan la."""

    def test_long_poll_rong_tra_ve_none(self) -> None:
        assert normalize({"ok": True}) is None

    def test_body_rac_tra_ve_none(self) -> None:
        assert normalize({}) is None
        assert normalize({"khong": "lien quan"}) is None

    def test_thieu_chat_id_thi_bo_qua(self) -> None:
        assert normalize({"ok": True, "result": {"message": {"text": "hi"}}}) is None

    def test_truong_la_van_xu_ly_duoc(self) -> None:
        payload = {
            "ok": True,
            "result": {
                "event_name": "message.text.received",
                "message": {
                    "from": {"id": "u3", "is_bot": False},
                    "chat": {"id": "u3", "chat_type": "PRIVATE"},
                    "text": "hi",
                    "message_id": "m3",
                    "date": 1750316131602,
                    "truong_zalo_moi_them": {"gi_do": 1},
                },
            },
        }
        assert _ev(payload).text == "hi"

    def test_chat_type_la_thi_thanh_unknown(self) -> None:
        payload = {
            "ok": True,
            "result": {
                "message": {
                    "from": {"id": "u4", "is_bot": False},
                    "chat": {"id": "u4", "chat_type": "CHANNEL"},
                    "text": "hi",
                    "message_id": "m4",
                    "date": 1750316131602,
                }
            },
        }
        assert _ev(payload).chat_type == "unknown"

    def test_file_khong_ho_tro(self) -> None:
        payload = {
            "ok": True,
            "result": {
                "event_name": "message.unsupported.received",
                "message": {
                    "from": {"id": "u5", "is_bot": False},
                    "chat": {"id": "u5", "chat_type": "PRIVATE"},
                    "message_id": "m5",
                    "date": 1750316131602,
                },
            },
        }
        assert _ev(payload).kind == "unsupported"


class TestLenh:
    def _cmd(self, text: str) -> InboundEvent:
        return _ev(
            {
                "ok": True,
                "result": {
                    "message": {
                        "from": {"id": "u6", "is_bot": False},
                        "chat": {"id": "u6", "chat_type": "PRIVATE"},
                        "text": text,
                        "message_id": "m6",
                        "date": 1750316131602,
                    }
                },
            }
        )

    def test_nhan_dien_lenh(self) -> None:
        e = self._cmd("/baogia goi Standard")
        assert e.is_command
        assert e.command == "baogia"
        assert e.command_args == "goi Standard"

    def test_text_thuong_khong_phai_lenh(self) -> None:
        e = self._cmd("cho em hoi bao gia")
        assert not e.is_command
        assert e.command is None


class TestSplitText:
    """Zalo cat cung o 2000 ky tu va khong co editMessageText."""

    def test_tin_ngan_giu_nguyen(self) -> None:
        assert split_text("xin chao") == ["xin chao"]

    def test_tin_rong(self) -> None:
        assert split_text("") == []
        assert split_text("   ") == []

    def test_cat_theo_gioi_han(self) -> None:
        parts = split_text("a" * 5000, limit=2000)
        assert len(parts) == 3
        assert all(len(p) <= 2000 for p in parts)

    def test_uu_tien_cat_o_ranh_gioi_doan(self) -> None:
        text = ("x" * 1500) + "\n\n" + ("y" * 1000)
        parts = split_text(text, limit=2000)
        assert parts[0] == "x" * 1500
        assert parts[1] == "y" * 1000

    def test_khong_mat_chu(self) -> None:
        text = " ".join(f"tu{i}" for i in range(800))
        joined = " ".join(split_text(text, limit=2000))
        assert joined.replace("  ", " ") == text
