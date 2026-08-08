"""Loi cua harness va cac cau tra loi du phong (tieng Viet, gui thang cho nguoi dung)."""

from __future__ import annotations


class HarnessError(RuntimeError):
    """Goc cua moi loi trong mot luot."""


class TurnTimeout(HarnessError):
    pass


class MaxIterations(HarnessError):
    pass


class ToolDenied(HarnessError):
    def __init__(self, tool_name: str, reason: str) -> None:
        super().__init__(f"tu choi tool {tool_name}: {reason}")
        self.tool_name = tool_name
        self.reason = reason


# --- Cau tra loi du phong. Khong bao gio lo chi tiet ky thuat cho khach. ---

MSG_LOI_HE_THONG = (
    "Dạ hệ thống của em đang gặp trục trặc một chút ạ. "
    "Em đã báo cho anh/chị phụ trách rồi, sẽ phản hồi lại sớm nhất."
)

MSG_QUA_LAU = (
    "Dạ câu này em cần thêm thời gian để kiểm tra kỹ. "
    "Em chuyển sang anh/chị phụ trách để trả lời chính xác cho mình ạ."
)

MSG_QUA_NHIEU_BUOC = (
    "Dạ câu này hơi phức tạp, em chưa xử lý gọn được. "
    "Em chuyển cho anh/chị phụ trách hỗ trợ mình trực tiếp ạ."
)

MSG_QUA_NHANH = "Dạ anh/chị nhắn hơi nhanh, em xử lý chưa kịp. Mình chờ em một chút nhé ạ."

MSG_KHONG_DOC_DUOC_FILE = (
    "Dạ Zalo Bot chưa nhận được file tài liệu ạ. "
    "Anh/chị chụp màn hình gửi ảnh, hoặc gõ nội dung ra giúp em nhé."
)

MSG_DANG_CHO_NGUOI = "Dạ anh/chị phụ trách đang xem tin của mình ạ, mình chờ chút nhé."
