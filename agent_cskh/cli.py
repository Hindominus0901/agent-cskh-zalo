"""Cong vao duy nhat: `agent-cskh <lenh>`. Giong het nhau tren Windows va macOS.

    agent-cskh chat    chat ngay trong terminal — KHONG can token, khong can key
    agent-cskh check   kiem tra cau hinh, in ra dung viec can lam tiep
    agent-cskh chay    chay bot that tren Zalo

`chat` la lenh quan trong nhat cua template nay. Nguoi vua nhan repo chua co
token Zalo va chua chac co API key. Neu buoc dau tien cua ho la "di lay token"
thi mot phan se dung lai o do. Voi `chat` + che do `tra_cuu`, buoc dau tien la
thay bot tra loi — trong vong vai phut, bang chinh kho tri thuc cua ho, khong
ton mot dong nao.
"""

from __future__ import annotations

import asyncio
import platform
import sys

MAC = platform.system() == "Darwin"


def _bat_utf8() -> None:
    """Ep console sang UTF-8 truoc khi in bat cu thu gi.

    MOI chuoi nguoi dung thay trong file nay deu la tieng Viet co dau. Console
    Windows mac dinh la cp1252, khong ma hoa duoc "ế", "ữ", "ộ" — nen `check` va
    `chat` CHET bang UnicodeEncodeError truoc khi in noi mot dong.

    Do duoc 11/08/2026 khi dua repo cho mot agent la chay thu tren console sach.
    Khong phat hien som hon vi console cua may dang phat trien da duoc dat UTF-8
    tu truoc — dung kieu loi chi hien ra o may nguoi khac.

    Hau qua neu khong sua: hoc vien khong biet lap trinh chay lenh dau tien cua
    ho va nhan lai mot traceback Python. Ho se khong doc no, ho se bo.

    `errors="replace"` chu khong phai "strict": console co font khong day du van
    in duoc, chi thay vai ky tu bang "?". Mat dau con hon mat ca chuong trinh.

    Bao boc trong try/except vi:
      - Tren macOS/Linux thuong da la UTF-8 san, goi nay vo hai
      - Trong test, stdout co the la StringIO — khong co `reconfigure`
    """
    for luong in (sys.stdout, sys.stderr, sys.stdin):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            # Khong ep duoc thi thoi — khong duoc lam hong ca chuong trinh chi
            # vi khong doi duoc bang ma.
            pass


def _in_dam(s: str) -> str:
    return f"\033[1m{s}\033[0m" if sys.stdout.isatty() else s


def _cach_cai(cai_gi: str) -> str:
    """Chi in lenh cua HE DIEU HANH DANG CHAY.

    In ca hai la cach nhanh nhat de mot nguoi dung Mac chep nham lenh PowerShell.
    """
    bang = {
        "uv": ("brew install uv", "winget install astral-sh.uv"),
    }
    mac, win = bang[cai_gi]
    return mac if MAC else win


def _chat() -> int:
    from agent_cskh.config import get_settings
    from agent_cskh.security.whitelist import _scope_for
    from agent_cskh.wiki import WikiStore

    s = get_settings()
    s.ensure_dirs()

    wiki = WikiStore(s)
    so_trang = wiki.reload()

    print()
    print(_in_dam(f"  Chat thu — chế độ {s.che_do}"))
    print(f"  Kho tri thức: {so_trang} trang")
    if so_trang == 0:
        print()
        print("  Kho đang TRỐNG nên bot chưa trả lời được gì.")
        print("  Thêm trang vào knowledge/wiki/public/ rồi chạy lại.")
        print("  Chưa có nội dung thì đọc HUONG-DAN-AGENT.md — phần phỏng vấn.")
    print()
    print("  Gõ câu hỏi như một khách hàng. Ctrl+C để thoát.")
    print("  Đổi vai: /vai stranger | /vai student | /vai staff")
    print()

    if s.che_do == "ai":
        print("  CHE_DO=ai chưa dùng được trong `chat` — hiện chỉ chạy `tra_cuu`.")
        print("  Muốn thử chế độ ai thì nối Zalo (xem docs/01-noi-zalo.md).")
        print()

    from agent_cskh.tra_cuu import DinhTuyenTraCuu

    dinh_tuyen = DinhTuyenTraCuu(wiki)
    vai = "stranger"
    thieu: list[str] = []

    try:
        while True:
            try:
                cau = input(_in_dam("khách> ")).strip()
            except EOFError:
                break
            if not cau:
                continue
            if cau.startswith("/vai "):
                moi = cau.split(maxsplit=1)[1].strip()
                if moi not in ("stranger", "student", "staff", "owner"):
                    print("  Vai phải là: stranger | student | staff | owner\n")
                    continue
                vai = moi
                print(f"  → đang đóng vai: {vai}\n")
                continue

            kq = dinh_tuyen.tra_loi(cau, chat_id="cli", scope=_scope_for(vai))  # type: ignore[arg-type]
            print()
            print(f"bot> {kq.text}")
            if kq.can_nguoi_that:
                print("     [bot đã chuyển cho người thật]")
            if kq.cau_hoi_thieu:
                thieu.append(kq.cau_hoi_thieu)
            print()
    except KeyboardInterrupt:
        print()

    if thieu:
        print()
        print(_in_dam(f"  {len(thieu)} câu bot KHÔNG trả lời được:"))
        for c in thieu:
            print(f"    • {c}")
        print()
        print("  Đây chính là danh sách trang cần viết thêm. Khi chạy thật trên")
        print("  Zalo, những câu này tự vào bảng `thieu_trang` và lên báo cáo 20h.")
        print()
    return 0


def _check() -> int:
    """Preflight. In ra dung viec can lam tiep, theo dung he dieu hanh dang chay."""
    from agent_cskh.config import get_settings
    from agent_cskh.wiki import WikiStore

    s = get_settings()
    s.ensure_dirs()
    xanh, do = [], []

    def ok(msg: str) -> None:
        xanh.append(f"  [ok]    {msg}")

    def loi(msg: str, sua: str) -> None:
        do.append(f"  [THIẾU] {msg}\n          → {sua}")

    # --- moi truong ---
    v = sys.version_info
    if (v.major, v.minor) == (3, 12):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        loi(f"Python {v.major}.{v.minor} (cần 3.12)", f"cài uv rồi `uv sync`: {_cach_cai('uv')}")

    # --- do dai duong dan (chi Windows) ---
    #
    # Windows chan duong dan qua 260 ky tu tru khi bat LongPathsEnabled. Thu vien
    # `anthropic` co mot file ten dai 77 ky tu, nam sau
    # `.venv\\Lib\\site-packages\\anthropic\\types\\beta\\` — cong lai khoang 121
    # ky tu. Thu muc du an dai qua ~130 la file do khong import duoc.
    #
    # Do duoc 10/08/2026: clone vao mot duong dan 260 ky tu -> `uv sync` bao
    # thanh cong, roi `pytest` chet bang
    #   ModuleNotFoundError: No module named
    #   'anthropic.types.beta.beta_managed_agents_session_resource_not_found_...'
    # Khong ai doan duoc tu thong bao do rang van de la DUONG DAN QUA DAI. Bat
    # o day de bien no thanh mot cau doc duoc.
    if not MAC and sys.platform == "win32":
        from agent_cskh.config import ROOT

        do_dai = len(str(ROOT))
        if do_dai > 130:
            loi(
                f"Đường dẫn thư mục dài {do_dai} ký tự — Windows sẽ lỗi khi cài thư viện",
                "chuyển cả thư mục ra chỗ ngắn hơn, ví dụ C:\\agent-cskh, rồi `uv sync` lại",
            )
        elif do_dai > 100:
            xanh.append(
                f"  [ ]     Đường dẫn dài {do_dai} ký tự — còn chạy được, "
                f"nhưng nên chuyển ra chỗ ngắn hơn cho chắc"
            )

    # --- che do ---
    ok(f"CHE_DO={s.che_do}" + ("  (0 đồng, không cần API key)" if s.che_do == "tra_cuu" else ""))
    if s.che_do == "ai" and not s.anthropic_api_key.get_secret_value():
        loi(
            "CHE_DO=ai nhưng chưa có ANTHROPIC_API_KEY",
            "lấy key tại console.anthropic.com, hoặc đổi về CHE_DO=tra_cuu",
        )

    # --- persona ---
    persona = s.knowledge_dir / "persona.md"
    if not persona.exists():
        loi("Chưa có knowledge/persona.md", "đọc HUONG-DAN-AGENT.md rồi PHONG-VAN.md")
    else:
        noi_dung = persona.read_text(encoding="utf-8")
        # Dem `[CHỜ HỌC VIÊN:` CO DAU HAI CHAM, khong dem `[CHỜ HỌC VIÊN]`.
        #
        # Cho trong that luon co dau hai cham roi den cau hoi cu the. Con dang
        # khong dau hai cham chi xuat hien trong doan huong dan o dau file, va
        # doan do khong bao gio bien mat.
        #
        # Dem ca hai dang thi `check` KHONG BAO GIO XANH duoc, du hoc vien da
        # dien het — phat hien luc di thu tron duong cua hoc vien. Mot preflight
        # khong bao gio xanh thi chi vai ngay la khong ai nhin no nua.
        con_lai = noi_dung.count("[CHỜ HỌC VIÊN:")
        if con_lai:
            loi(
                f"persona.md còn {con_lai} chỗ [CHỜ HỌC VIÊN] chưa điền",
                "phỏng vấn chủ doanh nghiệp rồi điền — KHÔNG được tự bịa",
            )
        else:
            ok("persona.md đã điền xong")

    # --- kho tri thuc ---
    wiki = WikiStore(s)
    so = wiki.reload()
    moi_muc = frozenset({"public", "hocvien", "internal"})
    trang = wiki.visible(moi_muc)
    if so == 0:
        loi("Kho tri thức trống", "phỏng vấn 10 câu khách hay hỏi rồi tạo trang trong knowledge/wiki/public/")
    elif so < 5:
        loi(f"Kho tri thức mới có {so} trang", "nên có ít nhất 5 trang trước khi đưa lên Zalo")
    else:
        ok(f"Kho tri thức: {so} trang")

    thieu_tu_khoa = [p.slug for p in trang if not p.tu_khoa]
    if thieu_tu_khoa:
        loi(
            f"{len(thieu_tu_khoa)} trang chưa có `tu_khoa`: {', '.join(thieu_tu_khoa[:5])}",
            "thêm `tu_khoa: [...]` vào frontmatter — chế độ tra_cuu dựa hẳn vào nó",
        )
    elif trang:
        ok("Mọi trang đều có `tu_khoa`")

    qua_dai = [p.slug for p in trang if len(p.body) > 1400]
    if qua_dai:
        loi(
            f"{len(qua_dai)} trang dài quá 1400 ký tự: {', '.join(qua_dai[:5])}",
            "bot cắt ở 1400 — phần sau không tới được khách. Tách thành nhiều trang.",
        )

    # --- ky nang ---
    from agent_cskh.skills import KhoSkill

    kho_skill = KhoSkill(s)
    kho_skill.nap()
    duoc_nap = kho_skill.duoc_nap()
    cho_duyet = kho_skill.cho_duyet()
    if duoc_nap:
        ok(f"Kỹ năng: {len(duoc_nap)} cái đang dùng")
    else:
        xanh.append("  [ ]     Chưa có kỹ năng nào — không bắt buộc")
    if cho_duyet:
        # KHONG phai loi. Skill cho duyet la he thong dang lam dung viec cua no.
        # Nhung phai hien ra, vi mot skill nam mai o trang thai `nhap` thi khong
        # ai biet no dang doi.
        xanh.append(
            f"  [ ]     {len(cho_duyet)} kỹ năng chờ duyệt: "
            f"{', '.join(x.ten for x in cho_duyet[:3])}"
        )

    # Skill khai mot cong cu KHONG TON TAI.
    #
    # Truong `tools:` truoc day chi la trang tri, nen khong ai phat hien khi no
    # sai. Gio no hien ra trong muc luc prompt, va mot cai ten sai o do la mot
    # loi hua voi model ve nang luc khong co.
    # PHAI phan biet hai truong hop, neu khong se bao dong gia:
    #   - Ten go sai, khong ton tai o dau ca        -> loi that
    #   - Ton tai trong ma nguon nhung dang TAT      -> binh thuong, chi ghi chu
    #     (nhom don hang tat khi chua co data/don_hang.csv)
    #
    # Khong tach hai truong hop nay thi mot shop khong ban hang vat ly se KHONG
    # BAO GIO xanh duoc — va mot preflight khong bao gio xanh thi vai ngay la
    # khong ai nhin no nua.
    from agent_cskh.tools import DON_HANG_TOOLS, default_registry

    dang_bat = {t.name for t in default_registry(s)._tools.values()}  # noqa: SLF001
    co_the_bat = {t.name for t in DON_HANG_TOOLS}
    moi_ten = dang_bat | co_the_bat

    dang_tat_bi_dung: set[str] = set()
    for sk in duoc_nap:
        khong_co = [c for c in sk.cong_cu if c not in moi_ten]
        if khong_co:
            loi(
                f"Kỹ năng “{sk.ten}” khai công cụ KHÔNG TỒN TẠI: {', '.join(khong_co)}",
                f"gõ sai tên? sửa trường `tools:` trong skills/{sk.ten}/SKILL.md",
            )
        dang_tat_bi_dung |= {c for c in sk.cong_cu if c in co_the_bat and c not in dang_bat}

    if dang_tat_bi_dung:
        xanh.append(
            "  [ ]     Nhóm công cụ đơn hàng đang TẮT (chưa có data/don_hang.csv) — "
            "bình thường nếu bạn không bán hàng vật lý"
        )

    # --- zalo (khong bat buoc) ---
    if not s.token:
        xanh.append("  [ ]     Chưa nối Zalo — chạy `agent-cskh chat` để thử trước")
    elif ":" not in s.token:
        loi("ZALO_BOT_TOKEN sai định dạng", "phải có dạng <số>:<chuỗi> — Zalo nhắn tin cho bạn, xem docs/01-noi-zalo.md")
    else:
        ok("ZALO_BOT_TOKEN có định dạng đúng")
        if not s.owner_user_ids:
            loi(
                "Chưa có OWNER_USER_IDS",
                "chạy bot, nhắn “id của tôi” cho nó, dán user_id vào .env",
            )
        else:
            ok(f"OWNER_USER_IDS: {len(s.owner_user_ids)} người")

    print()
    for d in xanh:
        print(d)
    if do:
        print()
        for d in do:
            print(d)
        print()
        print(f"  Còn {len(do)} việc. Xong hết rồi hãy nói là đã dựng xong.")
        print()
        return 1
    print()
    print("  Xanh hết. Chạy `uv run agent-cskh chat` để thử.")
    print()
    return 0


async def _chay() -> int:
    from agent_cskh.app import Application
    from agent_cskh.config import get_settings
    from agent_cskh.logging_setup import setup_logging

    s = get_settings()
    van_de = s.problems()
    if van_de:
        print("Chưa chạy được trên Zalo:")
        for v in van_de:
            print(f"  - {v}")
        print("\nChạy `agent-cskh check` để xem chi tiết.")
        return 1
    setup_logging(s)
    return await Application(s).run()


def main() -> int:
    # PHAI goi truoc moi lenh print. Xem docstring cua `_bat_utf8`.
    _bat_utf8()
    lenh = sys.argv[1] if len(sys.argv) > 1 else "help"
    if lenh == "chat":
        return _chat()
    if lenh == "check":
        return _check()
    if lenh in ("chay", "run"):
        return asyncio.run(_chay())
    print(__doc__)
    return 0 if lenh in ("help", "-h", "--help") else 1


if __name__ == "__main__":
    raise SystemExit(main())
