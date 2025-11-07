# Quick Start Guide

## Bắt đầu nhanh trong 5 phút ⚡

### Bước 1: Cài đặt (1 phút)

```bash
# Cài đặt dependencies
pip install -r requirements.txt

# Tạo thư mục auth_files
mkdir -p auth_files

# Thêm Gemini API keys (lấy từ https://aistudio.google.com/app/apikey)
cat > auth_files/keys.txt << EOF
AIzaSyAbc123...your-key-1
AIzaSyDef456...your-key-2
EOF
```

### Bước 2: Tạo truyện đầu tiên (3 phút)

```bash
# Tạo 1 batch (5 chapters) với motif ngẫu nhiên
python main.py --story-id my_first_story --batches 1
```

### Bước 3: Xem kết quả (1 phút)

```bash
# Xem các chapter đã tạo
ls output/chapters/

# Đọc chapter 1
cat output/chapters/chapter_001.txt

# Xem chi phí
cat output/cost_summary.json
```

## 🎯 Các lệnh thường dùng

### Tạo truyện với motif cụ thể

```bash
python main.py --story-id my_story --batches 1 --motif-id motif_001
```

### Tạo nhiều batch cùng lúc

```bash
python main.py --story-id my_story --batches 3
```

### Chạy từng bước riêng

```bash
# Bước 1: Tạo outline
python scripts.py outline --batch 1 --story-id my_story

# Bước 2: Trích xuất entities
python scripts.py entities --batch 1 --story-id my_story

# Bước 3: Viết chapter
python scripts.py chapter --chapter 1 --story-id my_story

# Bước 4: Post-process
python scripts.py process --chapter 1 --story-id my_story
```

### Tiếp tục từ checkpoint

Nếu quá trình bị gián đoạn, chỉ cần chạy lại lệnh cũ:

```bash
python main.py --story-id my_story --batches 3
# Hệ thống tự động tiếp tục từ bước cuối cùng
```

## 📊 Kiểm tra tiến độ

```bash
# Xem checkpoint hiện tại
cat checkpoints/my_story_checkpoint.json

# Xem logs
tail -f logs/StoryGenerator_*.log

# Đếm chapters đã tạo
ls output/chapters/*.txt | wc -l
```

## ⚙️ Tùy chỉnh cơ bản

### Thay đổi số từ mỗi chapter

Mở `config/config.yaml`:

```yaml
story:
  target_words_per_chapter: 3000  # Thay đổi từ 5000 thành 3000
```

### Thay đổi model LLM

```yaml
task_configs:
  chapter_writing:
    model: "gpt-3.5-turbo"  # Rẻ hơn
    temperature: 0.85
```

### Thêm motif mới

Mở `data/motif.json` và thêm:

```json
{
  "id": "motif_my_custom",
  "title": "Motif của tôi",
  "description": "Mô tả...",
  "genre": "tu tiên",
  "themes": ["theme1", "theme2"],
  "keywords": ["key1", "key2"]
}
```

## 🐛 Xử lý lỗi thường gặp

### Lỗi: Module not found

```bash
pip install -r requirements.txt
```

### Lỗi: API key not set

```bash
# Tạo file keys
mkdir -p auth_files
nano auth_files/keys.txt
# Thêm keys, mỗi key một dòng

# Hoặc dùng biến môi trường
export GOOGLE_API_KEYS="key1,key2,key3"
```

### Lỗi: Checkpoint corrupt

```python
# Xóa checkpoint và chạy lại
rm checkpoints/my_story_checkpoint.json
python main.py --story-id my_story --batches 1
```

## 📖 Ví dụ workflow hoàn chỉnh

```bash
# 1. Tạo truyện mới
python main.py --story-id epic_story --batches 1 --genre "tu tiên"

# 2. Kiểm tra kết quả
cat output/chapters/chapter_001.txt

# 3. Xem entities đã trích xuất
cat output/entities/entities.json | jq '.characters[].name'

# 4. Xem conflicts chưa giải quyết
cat output/conflicts/conflicts.json | jq '.[] | select(.status=="active")'

# 5. Tiếp tục batch 2 với gợi ý
python scripts.py batch --batch 2 --story-id epic_story \
  --user-input "Nhân vật chính khám phá hang động bí mật"

# 6. Tạo thêm nhiều batch
python main.py --story-id epic_story --batches 10

# 7. Xem tổng chi phí
cat output/cost_summary.json | jq '.total_cost'
```

## 💡 Tips

1. **Bắt đầu nhỏ**: Test với 1 batch trước khi tạo nhiều batch
2. **Theo dõi chi phí**: Check `cost_summary.json` thường xuyên
3. **Backup output**: Copy folder `output/` định kỳ
4. **Đọc logs**: Logs chứa thông tin debug hữu ích
5. **Thử nghiệm prompts**: Sửa prompts trong `src/*.py` để cải thiện chất lượng

## 🎨 Nâng cao

### Tạo motif động từ user input

```python
# Thêm vào data/motif.json
{
  "id": "motif_custom",
  "title": "Ý tưởng của bạn",
  "description": "...",
  "genre": "tu tiên",
  "themes": ["..."],
  "keywords": ["..."]
}
```

### Chạy parallel nhiều story

```bash
# Terminal 1
python main.py --story-id story_1 --batches 5

# Terminal 2
python main.py --story-id story_2 --batches 5
```

### Export sang PDF/EPUB

```bash
# Nối tất cả chapters
cat output/chapters/chapter_*.txt > full_story.txt

# Sử dụng pandoc để convert
pandoc full_story.txt -o story.pdf
```

---

**Bắt đầu ngay!** 🚀

```bash
python main.py --story-id my_first_story --batches 1
```
