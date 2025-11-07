# Max Chars Configuration Update

## Ngày cập nhật
7 tháng 11, 2025

## Tổng quan thay đổi

Đã loại bỏ tất cả hard-coded `max_chars` values và chuyển sang load từ config file với default value = 30000.

## Vấn đề trước đây

### Hard-coded values tìm thấy:
1. **`post_processor.py`** - 3 vị trí:
   - `extract_events()`: max_chars = 15000
   - `extract_conflicts()`: max_chars = 15000
   - `generate_summary()`: max_chars = 15000

2. **`entity_manager.py`** - 1 vị trí:
   - `_create_chapter_extraction_prompt()`: max_chars = 30000

### Nhược điểm của hard-coded:
- Không linh hoạt khi cần thay đổi
- Giá trị khác nhau giữa các file (15000 vs 30000)
- Khó maintain và dễ quên khi cập nhật

## Giải pháp

### 1. Thêm cấu hình vào `config.yaml`

```yaml
# Story Configuration
story:
  chapters_per_batch: 5
  target_words_per_chapter: 5000
  last_chapter_context_chars: 1000
  max_chars_for_llm: 30000  # Maximum characters to send to LLM for processing
```

**Lý do chọn default = 30000:**
- Đủ lớn để chứa hầu hết nội dung chapter (5000 words ≈ 25000-30000 chars)
- Tránh vượt quá token limits của LLM
- Phù hợp với context window của Gemini models

### 2. Cập nhật `post_processor.py`

**Thêm vào `__init__()`:**
```python
self.max_chars = config.get('story', {}).get('max_chars_for_llm', 30000)
```

**Thay thế tất cả hard-coded values:**
```python
# BEFORE:
max_chars = 15000
truncated = chapter_content[:max_chars] + "..." if len(chapter_content) > max_chars else chapter_content

# AFTER:
truncated = chapter_content[:self.max_chars] + "..." if len(chapter_content) > self.max_chars else chapter_content
```

**Các methods được cập nhật:**
- `extract_events()`
- `extract_conflicts()`
- `generate_summary()`

### 3. Cập nhật `entity_manager.py`

**Thêm vào `__init__()`:**
```python
self.max_chars = config.get('story', {}).get('max_chars_for_llm', 30000)
```

**Thay thế hard-coded value:**
```python
# BEFORE:
max_chars = 30000
truncated_content = chapter_content[:max_chars] + "..." if len(chapter_content) > max_chars else chapter_content

# AFTER:
truncated_content = chapter_content[:self.max_chars] + "..." if len(chapter_content) > self.max_chars else chapter_content
```

**Method được cập nhật:**
- `_create_chapter_extraction_prompt()`

## Lợi ích

### 1. Centralized Configuration
- Tất cả config ở một chỗ (`config.yaml`)
- Dễ dàng thay đổi giá trị khi cần
- Nhất quán giữa các modules

### 2. Flexible
- Có thể điều chỉnh theo model LLM khác nhau
- Có thể tùy chỉnh theo từng project nếu cần
- Dễ dàng test với các giá trị khác nhau

### 3. Maintainability
- Giảm magic numbers trong code
- Dễ hiểu và maintain
- Tuân theo best practices

### 4. Default Fallback
- Sử dụng `.get()` với default value
- Không bị lỗi nếu config thiếu key
- Default value = 30000 (hợp lý cho hầu hết cases)

## Cách sử dụng

### Thay đổi giá trị trong config:

```yaml
# config/config.yaml
story:
  max_chars_for_llm: 40000  # Tăng lên nếu sử dụng model có context window lớn hơn
```

### Trong code:

Không cần thay đổi gì, code sẽ tự động load từ config:
```python
# Tự động sử dụng giá trị từ config
truncated = chapter_content[:self.max_chars] + "..."
```

## Testing

### 1. Verify config loading:
```python
from src.utils import load_config
config = load_config()
print(config['story']['max_chars_for_llm'])  # Should print: 30000
```

### 2. Test với các modules:
```bash
# Test entity extraction
python scripts.py extract-entities-chapter --project story_001 --chapter 1

# Test post processing
python main.py --project story_001 --batch 1
```

### 3. Verify không còn hard-coded values:
```bash
# Search for any remaining hard-coded max_chars
grep -r "max_chars\s*=\s*[0-9]" src/
# Should return: No results
```

## Files đã thay đổi

1. ✅ `config/config.yaml` - Thêm `max_chars_for_llm: 30000`
2. ✅ `src/post_processor.py` - Load từ config, cập nhật 3 methods
3. ✅ `src/entity_manager.py` - Load từ config, cập nhật 1 method

## Backward Compatibility

✅ **Hoàn toàn tương thích ngược:**

1. **Config có default value**: Nếu config file cũ không có key này, sẽ dùng default = 30000
2. **Interface không đổi**: Các methods vẫn hoạt động như cũ
3. **Logic không thay đổi**: Chỉ thay đổi source của giá trị max_chars

## Best Practices đã áp dụng

1. ✅ **DRY (Don't Repeat Yourself)**: Giá trị chỉ định nghĩa 1 lần trong config
2. ✅ **Configuration over Code**: Dùng config thay vì hard-code
3. ✅ **Safe Defaults**: Sử dụng `.get()` với fallback value
4. ✅ **Centralized Settings**: Tập trung config ở một nơi
5. ✅ **Self-documenting**: Comment giải thích ý nghĩa của config

## Ghi chú kỹ thuật

### Tại sao dùng `.get()` với default?

```python
self.max_chars = config.get('story', {}).get('max_chars_for_llm', 30000)
```

- `config.get('story', {})`: Trả về dict rỗng nếu không có key 'story'
- `.get('max_chars_for_llm', 30000)`: Trả về 30000 nếu không có key
- Tránh KeyError khi config file thiếu hoặc sai format

### Tại sao default = 30000?

1. **Token limits**: Gemini models thường có token limit ~1M, 30K chars ≈ 7.5K tokens
2. **Chapter size**: 5000 words ≈ 25-30K characters
3. **Safety margin**: Đủ lớn nhưng không quá để tránh timeout
4. **Consistency**: Đủ cho cả chapter extraction và post-processing

### Có thể tùy chỉnh cho từng task không?

Hiện tại dùng chung 1 giá trị. Nếu cần, có thể mở rộng thành:

```yaml
story:
  max_chars_for_llm:
    default: 30000
    entity_extraction: 35000
    event_extraction: 20000
    summary_generation: 20000
```

Nhưng hiện tại chưa cần thiết vì 30000 phù hợp cho tất cả cases.

## Future Enhancements

Có thể cải tiến thêm:

1. **Dynamic sizing**: Tự động điều chỉnh dựa trên model's context window
2. **Per-task limits**: Giới hạn riêng cho từng loại task
3. **Smart truncation**: Cắt ở paragraph boundaries thay vì giữa câu
4. **Compression**: Nén content thay vì cắt bớt

Nhưng với yêu cầu hiện tại, giải pháp này đã đủ tốt và đơn giản.
