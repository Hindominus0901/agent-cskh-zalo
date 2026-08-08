# Dành cho coding agent (Cursor, Codex, và các agent khác)

Hướng dẫn đầy đủ nằm ở **[CLAUDE.md](CLAUDE.md)**. Đọc file đó rồi làm theo.

Đây không phải một dự án cần bạn sửa code. Đây là template — việc của bạn là
**phỏng vấn người đang ngồi cạnh** rồi dựng con bot của chính họ.

Ba điều tuyệt đối không được làm, nhắc lại ở đây vì chúng quan trọng nhất:

1. **Không bịa nội dung kinh doanh.** Trang trong `knowledge/` chỉ được viết từ
   câu trả lời nguyên văn của chủ doanh nghiệp. Chưa hỏi thì ghi
   `[CHỜ HỌC VIÊN: ...]` rồi hỏi. Không có "giá tham khảo".
2. **Không bỏ bước phỏng vấn**, và hỏi **từng câu một** — hỏi gộp thì luôn nhận
   về câu trả lời bỏ mất ý khó nhất.
3. **Không tự ý bật `CHE_DO=ai`.** Mặc định `tra_cuu` chạy 0 đồng, không cần API
   key. Chỉ đổi khi chủ nói rõ họ có key và chấp nhận trả tiền.

Không nhân bản nội dung của `CLAUDE.md` vào đây — hai file lệch nhau là nguồn lỗi.
