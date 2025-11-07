# AI Story Generation System

Hệ thống tự động sinh truyện tu tiên sử dụng AI với khả năng quản lý checkpoint, tracking chi phí, và xử lý phức tạp.

## 🌟 Tính năng chính

- ✅ **Checkpoint & Resume**: Có thể tiếp tục từ bất kỳ bước nào bị gián đoạn
- 📊 **Logging chi tiết**: Lưu tất cả prompt, response, token usage, và chi phí
- 🎯 **Cấu hình linh hoạt**: Mỗi task có thể dùng model LLM khác nhau
- 🔄 **Batch processing**: Tạo truyện theo batch 5 chương
- 🏗️ **Modular**: Chạy độc lập từng bước hoặc toàn bộ pipeline
- 💰 **Cost tracking**: Theo dõi chi phí và token usage

## 📁 Cấu trúc dự án

```
test_writer/
├── config/
│   └── config.yaml           # Cấu hình LLM, paths, logging
├── data/
│   └── motif.json            # Motif truyện (input)
├── src/
│   ├── utils.py              # Utilities, Logger, CostTracker
│   ├── checkpoint.py         # Checkpoint manager
│   ├── llm_client.py         # LLM API wrapper
│   ├── motif_loader.py       # Load motif từ JSON
│   ├── outline_generator.py  # Tạo outline cho batch
│   ├── entity_manager.py     # Quản lý entities
│   ├── chapter_writer.py     # Viết nội dung chapter
│   └── post_processor.py     # Xử lý sau khi viết chapter
├── output/
│   ├── chapters/             # Nội dung các chapter
│   ├── outlines/             # Outline các batch
│   ├── entities/             # Entities database (JSON)
│   ├── events/               # Events database (JSON)
│   ├── conflicts/            # Conflicts database (JSON)
│   └── summaries/            # Summaries database (JSON)
├── checkpoints/              # Checkpoint files
├── logs/                     # Log files
├── main.py                   # Main orchestrator
├── scripts.py                # Individual step scripts
└── requirements.txt          # Dependencies
```

## 🚀 Cài đặt

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 2. Cấu hình Gemini API keys

**Cách 1: Sử dụng file keys (Khuyến nghị)**

Tạo file `auth_files/keys.txt` và thêm API keys (mỗi key một dòng):

```bash
mkdir -p auth_files
cat > auth_files/keys.txt << EOF
AIzaSyAbc123...key1
AIzaSyDef456...key2
AIzaSyGhi789...key3
EOF
```

**Cách 2: Sử dụng biến môi trường**

```bash
export GOOGLE_API_KEYS="key1,key2,key3"
```

**Lấy Gemini API key:** https://aistudio.google.com/app/apikey

### 3. Chỉnh sửa cấu hình (tuỳ chọn)

Mở `config/config.yaml` để:
- Thay đổi model LLM cho từng task
- Điều chỉnh temperature, max_tokens
- Cập nhật pricing cho cost tracking

## 📖 Cách sử dụng

### Chạy toàn bộ pipeline

Tạo 1 batch (5 chapters):
```bash
python main.py --story-id my_story --batches 1
```

Tạo nhiều batch:
```bash
python main.py --story-id my_story --batches 3
```

Chỉ định motif cụ thể:
```bash
python main.py --story-id my_story --batches 1 --motif-id motif_001
```

Lọc theo thể loại:
```bash
python main.py --story-id my_story --batches 1 --genre "tu tiên"
```

### Chạy từng bước riêng lẻ

#### 1. Tạo outline cho batch

Batch đầu tiên:
```bash
python scripts.py outline --batch 1 --story-id my_story --motif-id motif_001
```

Batch tiếp theo (có user input):
```bash
python scripts.py outline --batch 2 --story-id my_story --user-input "Tập trung vào phát triển võ công"
```

#### 2. Trích xuất entities từ outline

```bash
python scripts.py entities --batch 1 --story-id my_story
```

#### 3. Viết một chapter cụ thể

```bash
python scripts.py chapter --chapter 1 --story-id my_story
```

#### 4. Post-process một chapter

```bash
python scripts.py process --chapter 1 --story-id my_story
```

#### 5. Tạo toàn bộ batch

```bash
python scripts.py batch --batch 1 --story-id my_story
```

## 📊 Luồng hoạt động

### Batch 1 (5 chapters đầu tiên)

1. **Load motif** từ `data/motif.json`
2. **Tạo outline** cho 5 chapters với:
   - Key events, nhân vật, mâu thuẫn
   - Foreshadowing
   - Timeline cho conflicts
3. **Trích xuất entities** từ outline:
   - Characters, locations, items, spiritual herbs, beasts, techniques, factions
4. **Viết từng chapter** (5000 từ/chapter) với context:
   - Outline của chapter đó
   - Entities liên quan
   - Motif ban đầu
   - 1000 ký tự cuối chapter trước
5. **Post-processing** mỗi chapter:
   - Trích xuất entities mới
   - Trích xuất events quan trọng (importance 0-1)
   - Trích xuất conflicts mới
   - Tạo summary chapter
   - Update super summary

### Batch 2+ (các batch tiếp theo)

1. **Tạo outline** với context mở rộng:
   - Super summary từ đầu đến giờ
   - Summary chương gần nhất
   - Danh sách entities, characters liên quan
   - Events quan trọng
   - **Conflicts chưa giải quyết** (ưu tiên theo timeline)
   - User suggestions
2. **Lựa chọn conflicts** cần giải quyết:
   - Immediate: Giải quyết ngay
   - Batch: Giải quyết trong batch này
   - Short/Medium/Long-term: Tiến triển dần
3. **Tiếp tục** các bước như Batch 1

## 🗂️ Conflict Timeline

Hệ thống quản lý conflicts theo timeline:

- `immediate` (1 chapter): Phải giải quyết ngay
- `batch` (5 chapters): Giải quyết trong batch hiện tại
- `short_term` (10 chapters): Giải quyết trong 10 chương
- `medium_term` (30 chapters): Cốt truyện trung hạn
- `long_term` (100 chapters): Cốt truyện dài hạn
- `epic` (300 chapters): Mâu thuẫn xuyên suốt toàn bộ truyện

## 📝 Output Files

### Chapters
- `output/chapters/chapter_001.txt`: Nội dung chapter
- `output/chapters/chapter_001_meta.json`: Metadata (word count, etc.)

### Outlines
- `output/outlines/batch_1_outline.json`: Outline cho batch 1

### Entities
- `output/entities/entities.json`: Tất cả entities (characters, locations, items, etc.)

### Events
- `output/events/events.json`: Tất cả events quan trọng với importance score

### Conflicts
- `output/conflicts/conflicts.json`: Tất cả conflicts với status tracking

### Summaries
- `output/summaries/summaries.json`: Summaries của các chapters

### Cost Summary
- `output/cost_summary.json`: Chi tiết chi phí và token usage

## 🔄 Checkpoint & Resume

Hệ thống tự động lưu checkpoint sau mỗi bước. Nếu quá trình bị gián đoạn:

```bash
# Chỉ cần chạy lại lệnh cũ, hệ thống sẽ tự động resume
python main.py --story-id my_story --batches 3
```

Checkpoint file: `checkpoints/my_story_checkpoint.json`

### Reset checkpoint

Nếu muốn bắt đầu lại từ đầu:

```python
from src.checkpoint import CheckpointManager

checkpoint = CheckpointManager('checkpoints', 'my_story')
checkpoint.reset()
```

## 📊 Logs

Mỗi run sẽ tạo log file trong `logs/`:
- Timestamp mỗi bước
- Prompts gửi đến LLM
- Responses nhận về
- Token usage
- Chi phí ước tính
- Duration

Ví dụ: `logs/StoryGenerator_20250107_143022.log`

## ⚙️ Cấu hình nâng cao

### Thay đổi model cho từng task

Trong `config/config.yaml`:

```yaml
task_configs:
  outline_generation:
    model: "gemini-2.5-flash"
    temperature: 0.8
    
  chapter_writing:
    model: "gemini-2.5-pro"  # Dùng Pro cho viết chapter
    temperature: 0.85
    max_tokens: 8000
    
  entity_extraction:
    model: "gemini-2.5-flash"  # Dùng Flash cho extraction
    temperature: 0.3
```

### Điều chỉnh độ dài chapter

```yaml
story:
  chapters_per_batch: 5
  target_words_per_chapter: 5000  # Thay đổi số từ
  last_chapter_context_chars: 1000
```

### Bật/tắt logging

```yaml
logging:
  level: "INFO"  # DEBUG để chi tiết hơn
  log_prompts: true
  log_responses: true
  log_tokens: true
  log_cost: true
```

## 🎨 Tùy chỉnh Motif

Thêm motif mới vào `data/motif.json`:

```json
{
  "motifs": [
    {
      "id": "motif_005",
      "title": "Tên motif của bạn",
      "description": "Mô tả chi tiết",
      "genre": "tu tiên",
      "themes": ["chủ đề 1", "chủ đề 2"],
      "keywords": ["keyword1", "keyword2"]
    }
  ]
}
```

## 🐛 Troubleshooting

### Lỗi: No Gemini API keys found

```bash
# Tạo file keys
mkdir -p auth_files
nano auth_files/keys.txt
# Thêm API keys, mỗi key một dòng
```

Hoặc:

```bash
export GOOGLE_API_KEYS="key1,key2,key3"
```

### Lỗi: Module not found

```bash
pip install -r requirements.txt
```

### Lỗi: JSON parsing failed

Kiểm tra logs để xem response từ LLM. Có thể cần điều chỉnh prompt hoặc tăng max_tokens.

### Chapter quá ngắn/dài

Điều chỉnh `target_words_per_chapter` trong config và thêm nhấn mạnh trong system message.

## 📚 Ví dụ workflow

### Tạo truyện mới hoàn chỉnh

```bash
# 1. Tạo batch 1
python main.py --story-id kungfu_story --batches 1 --genre "tu tiên"

# 2. Xem kết quả
ls output/chapters/

# 3. Kiểm tra chi phí
cat output/cost_summary.json

# 4. Tiếp tục batch 2 với gợi ý
python scripts.py batch --batch 2 --story-id kungfu_story --user-input "Nhân vật chính gặp sư phụ mới"

# 5. Tạo thêm nhiều batch
python main.py --story-id kungfu_story --batches 5
```

### Viết lại một chapter cụ thể

```bash
# 1. Xóa checkpoint cho chapter đó
# (Cần implement function hoặc edit checkpoint file manually)

# 2. Chạy lại
python scripts.py chapter --chapter 3 --story-id kungfu_story
```

## 🤝 Đóng góp

Hệ thống được thiết kế modular, dễ dàng mở rộng:

- Thêm entity types mới: Sửa `entity_manager.py`
- Thêm LLM provider: Mở rộng `llm_client.py`
- Thêm conflict types: Cập nhật `post_processor.py`
- Custom prompt: Sửa trong các `*_generator.py` files

## 📄 License

MIT License

## 🙏 Credits

Được xây dựng với:
- OpenAI GPT-4
- Python 3.8+
- Love for storytelling ❤️

---

**Happy Story Writing! 📖✨**
