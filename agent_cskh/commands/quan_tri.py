"""Lenh quan tri chay THANG TU ZALO — khong phai mo file tren may.

VI SAO CAN: sua kho tri thuc bang cach mo may, sua file, chay lenh la mot rao can
that. Chu bot dang o tren dien thoai, nghe hoc vien hoi mot cau ma kho chua co
cau tra loi — sua duoc ngay luc do thi trang do sinh ra. Con neu phai doi ve nha
mo may thi phan lon la khong bao gio sua.

Moi lenh o day deu GHI DU LIEU that va doi hanh vi cua bot voi moi nguoi, nen:
  - toi thieu vai `staff` (rieng dat kenh canh bao la `owner`)
  - moi thay doi deu ghi log va bao vao kenh canh bao
  - xoa va ghi de deu giu ban cu — go nham mot lenh tren dien thoai khong duoc
    phep lam mat vinh vien mot trang ai do soan ca buoi
"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from agent_cskh.harness.turn import TurnContext
from agent_cskh.logging_setup import get_logger
from agent_cskh.wiki.store import MUC_HIEN_THI

log = get_logger(__name__)

# Slug chi cho chu thuong, so va gach ngang. Chan luon duong dan tuong doi — bot
# khong bao gio duoc ghep duong dan tu dau vao nguoi dung.
_SLUG_HOP_LE = re.compile(r"^[a-z0-9][a-z0-9-]{1,60}$")

# Ten thiet bi danh rieng cua Windows. Chung bi cam KE CA khi co duoi file, nen
# `con.md` cung hong. Bot chay tren Windows va se len Linux — chan o ca hai cho
# de kho tri thuc chep qua lai duoc ma khong vo.
#
# Luu y: "con" la tu tieng Viet binh thuong, nen chi chan DUNG cac ten nay chu
# khong chan tu co chua chung — "cham-con" van hop le.
_TEN_CAM = (
    {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(10)} | {f"lpt{i}" for i in range(10)}
)


def _slug_hop_le(slug: str) -> bool:
    return bool(_SLUG_HOP_LE.match(slug)) and slug not in _TEN_CAM


def _duong_dan(ctx: TurnContext, muc: str, slug: str) -> Path:
    return ctx.settings.knowledge_dir / "wiki" / muc / f"{slug}.md"


def _ghi_dia(path: Path, van_ban: str) -> None:
    """Ham DONG BO, luon goi qua asyncio.to_thread."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(van_ban, encoding="utf-8")


def _sao_luu_roi_doi_ten(path: Path) -> Path:
    """Ham DONG BO. Doi duoi thanh .md.bak, tra ve duong dan moi.

    Dung os.replace chu khong Path.rename: tren Windows, rename NEM LOI khi
    dich da ton tai (WinError 183), con POSIX thi ghi de im lang. Xoa roi
    tao lai cung mot trang la viec binh thuong, khong duoc phep no.
    """
    moi = path.with_suffix(".md.bak")
    os.replace(path, moi)
    return moi


def _chep_ban_cu(path: Path) -> Path:
    """Ham DONG BO. Giu ban cu truoc khi ghi de."""
    moi = path.with_suffix(".md.bak")
    moi.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return moi


# ---------------------------------------------------------------- kenh canh bao


async def cmd_datkenhcanhbao(ctx: TurnContext) -> bool:
    """Dat CHINH chat dang chay lenh nay lam noi nhan canh bao noi bo."""
    if ctx.resolver is None:
        await ctx.reply("Chưa nối được phân quyền, chưa đặt được.")
        return True

    nhan = ctx.event.command_args.strip() or (ctx.principal.display_name or "")
    await ctx.resolver.dat_kenh_canh_bao(ctx.chat_id, nhan)
    log.info("dat_kenh_canh_bao", chat_id=ctx.chat_id[:8], by=ctx.principal.user_id[:8])

    await ctx.reply(
        "✅ Đã đặt cuộc trò chuyện này làm kênh cảnh báo nội bộ.\n\n"
        "Từ giờ những thứ sau sẽ gửi về ĐÂY:\n"
        "• Khách cần người tiếp quản — kèm tên và nội dung họ hỏi\n"
        "• Biên lai chờ đối soát\n"
        "• Học viên vừa vào lớp\n"
        "• Báo cáo hàng ngày lúc 20h\n"
        "• Cảnh báo khi bot hỏng\n\n"
        "⚠️ ĐỪNG đặt kênh này ở nhóm có học viên hoặc khách hàng. Nội dung trên "
        "có tên và thông tin của người khác — họ không được thấy.\n\n"
        "Nên dùng một nhóm riêng chỉ có bạn và nhân viên."
    )
    return True


async def cmd_kenhcanhbao(ctx: TurnContext) -> bool:
    """Xem kenh canh bao dang tro vao dau."""
    if ctx.resolver is None:
        return False

    hien_tai = await ctx.resolver.alert_chat_id()
    if not hien_tai:
        await ctx.reply(
            "Chưa đặt kênh cảnh báo — bot hỏng sẽ không báo cho ai.\n\n"
            "Mở cuộc trò chuyện muốn nhận cảnh báo rồi gõ /datkenhcanhbao."
        )
        return True

    o_day = " — chính là đây" if hien_tai == ctx.chat_id else ""
    await ctx.reply(
        f"Kênh cảnh báo hiện tại: {hien_tai}{o_day}\n\n"
        "Đổi bằng cách gõ /datkenhcanhbao ở nơi muốn chuyển tới."
    )
    return True


# ---------------------------------------------------------------- kho tri thuc


async def cmd_themtrang(ctx: TurnContext) -> bool:
    """/themtrang <muc> <slug> rồi xuống dòng viết nội dung."""
    dong_dau, _, noi_dung = ctx.event.command_args.partition("\n")
    phan = dong_dau.split()

    if len(phan) < 2 or not noi_dung.strip():
        await ctx.reply(
            "Cú pháp: /themtrang <mức> <tên-trang>\n"
            "rồi xuống dòng và viết nội dung.\n\n"
            f"Mức: {' · '.join(MUC_HIEN_THI)}\n\n"
            "Ví dụ:\n"
            "/themtrang public bang-gia-2026\n"
            "Bảng giá 2026\n"
            "Gói cơ bản dành cho người mới bắt đầu...\n\n"
            "Dòng đầu của nội dung sẽ thành tiêu đề."
        )
        return True

    muc, slug = phan[0].lower(), phan[1].lower()
    if muc not in MUC_HIEN_THI:
        await ctx.reply(f"Mức '{muc}' không có. Chọn một trong: {' · '.join(MUC_HIEN_THI)}")
        return True
    if not _slug_hop_le(slug):
        await ctx.reply("Tên trang chỉ dùng chữ thường, số và gạch ngang. Ví dụ: bang-gia-2026")
        return True

    path = _duong_dan(ctx, muc, slug)
    if path.exists():
        await ctx.reply(f"Trang '{slug}' đã có rồi. Dùng /suatrang nếu muốn ghi đè.")
        return True

    await _ghi_trang(ctx, path, slug, noi_dung)
    await ctx.reply(
        f"✅ Đã thêm [[{slug}]] vào mức {muc}.\n\n"
        f"Bot đọc được ngay. Gõ /xemtrang {slug} để kiểm lại."
    )
    await _bao_thay_doi(ctx, "Thêm", slug, muc)
    return True


async def cmd_suatrang(ctx: TurnContext) -> bool:
    """/suatrang <muc> <slug> rồi xuống dòng viết nội dung mới. GHI ĐÈ toàn bộ."""
    dong_dau, _, noi_dung = ctx.event.command_args.partition("\n")
    phan = dong_dau.split()

    if len(phan) < 2 or not noi_dung.strip():
        await ctx.reply(
            "Cú pháp: /suatrang <mức> <tên-trang>\n"
            "rồi xuống dòng và viết nội dung mới.\n\n"
            "Lệnh này GHI ĐÈ toàn bộ trang, không phải sửa một phần."
        )
        return True

    muc, slug = phan[0].lower(), phan[1].lower()
    if muc not in MUC_HIEN_THI or not _slug_hop_le(slug):
        await ctx.reply("Mức hoặc tên trang không hợp lệ.")
        return True

    path = _duong_dan(ctx, muc, slug)
    if not path.exists():
        await ctx.reply(f"Chưa có trang '{slug}' ở mức {muc}. Dùng /themtrang để tạo mới.")
        return True

    # Ghi de tu dien thoai rat de go nham, va khong co Ctrl+Z. Giu ban cu lai.
    sao_luu = await asyncio.to_thread(_chep_ban_cu, path)

    await _ghi_trang(ctx, path, slug, noi_dung)
    await ctx.reply(f"✅ Đã ghi đè [[{slug}]].\n\nBản cũ giữ lại ở {sao_luu.name} phòng khi cần.")
    await _bao_thay_doi(ctx, "Ghi đè", slug, muc)
    return True


async def cmd_xemtrang(ctx: TurnContext) -> bool:
    """/xemtrang <slug> — đọc toàn văn, theo đúng quyền của người gọi."""
    slug = ctx.event.command_args.strip().lower()
    if not slug:
        await ctx.reply("Cú pháp: /xemtrang <tên-trang>")
        return True

    page = ctx.wiki.read(slug, ctx.principal.visibility_scope)
    if page is None:
        await ctx.reply(f"Không có trang '{slug}', hoặc nó ngoài quyền của bạn.")
        return True
    await ctx.reply(page.render())
    return True


async def cmd_xoatrang(ctx: TurnContext) -> bool:
    """/xoatrang <muc> <slug> — đổi đuôi thành .md.bak, KHÔNG xoá hẳn."""
    phan = ctx.event.command_args.split()
    if len(phan) < 2:
        await ctx.reply("Cú pháp: /xoatrang <mức> <tên-trang>")
        return True

    muc, slug = phan[0].lower(), phan[1].lower()
    if muc not in MUC_HIEN_THI or not _slug_hop_le(slug):
        await ctx.reply("Mức hoặc tên trang không hợp lệ.")
        return True

    path = _duong_dan(ctx, muc, slug)
    if not path.exists():
        await ctx.reply(f"Không có trang '{slug}' ở mức {muc}.")
        return True

    # Doi ten chu khong xoa han.
    await asyncio.to_thread(_sao_luu_roi_doi_ten, path)
    await asyncio.to_thread(ctx.wiki.reload)
    log.info("wiki_xoa_tu_zalo", slug=slug, by=ctx.principal.user_id[:8])
    await ctx.reply(f"✅ Đã gỡ [[{slug}]] khỏi kho.\n\nFile vẫn còn trên đĩa dạng .md.bak.")
    await _bao_thay_doi(ctx, "Gỡ", slug, muc)
    return True


async def cmd_dstrang(ctx: TurnContext) -> bool:
    """Danh sách trang người gọi đọc được."""
    trang = ctx.wiki.visible(ctx.principal.visibility_scope)
    if not trang:
        await ctx.reply("Kho tri thức đang trống.")
        return True

    theo_muc: dict[str, list[str]] = {}
    for p in sorted(trang, key=lambda x: (x.visibility, x.slug)):
        theo_muc.setdefault(p.visibility, []).append(p.slug)

    dong = [f"📚 {len(trang)} trang"]
    for muc, ds in theo_muc.items():
        dong.append(f"\n{muc} ({len(ds)}):")
        dong += [f"• {s}" for s in ds]
    await ctx.reply("\n".join(dong))
    return True


# ---------------------------------------------------------------- tien ich


async def _ghi_trang(ctx: TurnContext, path: Path, slug: str, noi_dung: str) -> None:
    """Ghi file kèm frontmatter. Dòng đầu của nội dung thành tiêu đề.

    `summary` quan trọng hơn vẻ ngoài của nó: đây là thứ quyết định bot có TÌM
    THẤY trang này hay không, vì danh mục trong system prompt chỉ có dòng đó.
    """
    dong = [d for d in noi_dung.strip().split("\n") if d.strip()]
    tieu_de = dong[0].strip().lstrip("#").strip()[:120] if dong else slug
    tom_tat = " ".join(d.strip() for d in dong[1:4])[:200] or tieu_de
    van_ban = (
        f"---\ntitle: {tieu_de}\nsummary: {tom_tat}\n"
        f"updated: {datetime.now(tz=UTC).date()}\n---\n\n{noi_dung.strip()}\n"
    )

    # Ghi dia la viec CHAN. Nho den may cung khong duoc chay thang tren event
    # loop — cung nguyen tac da dat o dispatcher.
    await asyncio.to_thread(_ghi_dia, path, van_ban)
    await asyncio.to_thread(ctx.wiki.reload)
    log.info("wiki_sua_tu_zalo", slug=slug, muc=path.parent.name, by=ctx.principal.user_id[:8])


async def _bao_thay_doi(ctx: TurnContext, viec: str, slug: str, muc: str) -> None:
    """Bao vao kenh canh bao. Kho tri thuc doi la bot noi khac voi MOI nguoi —
    khong duoc phep xay ra ma khong ai hay."""
    await ctx.notify_staff(
        f"📝 KHO TRI THỨC VỪA ĐỔI\n\n"
        f"{viec}: {slug} (mức {muc})\n"
        f"Bởi: {ctx.principal.display_name or ctx.principal.user_id}"
    )
