# Ảnh gốc

Bỏ ảnh gốc (JPG/PNG, càng nét càng tốt) vào thư mục này, đặt tên đúng như sau:

| Tên file | Dùng cho |
|---|---|
| `hero.jpg` | Ảnh lớn đầu trang (ngang, tỉ lệ 16:10) |
| `seller.jpg` | Ảnh chân dung (sẽ cắt hình vuông) |
| `vf-2.jpg`, `vf-3.jpg`, `vf-5.jpg`, `vf-6.jpg`, `vf-7.jpg`, `vf-8.jpg`, `vf-9.jpg`, `vf-mpv-7.jpg`, `limo-green.jpg` | Ảnh từng mẫu xe (ngang, 16:10) |
| `og.jpg` (không bắt buộc) | Ảnh xem trước khi gửi link qua Zalo/Facebook. Không có thì lấy ảnh `hero`. |

Sau đó chạy ở thư mục gốc của repo:

```
python3 scripts/optimize_images.py
```

Script sẽ cắt, nén sang WebP và ghi đè ảnh trong `assets/img/`. Chỉ cần commit thư mục `assets/img/`. Ảnh gốc trong thư mục này không được đưa lên web (bị bỏ qua bởi git).
