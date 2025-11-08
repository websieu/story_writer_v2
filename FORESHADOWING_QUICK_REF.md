# Foreshadowing Section - Quick Reference

## Tóm Tắt

Đã thêm **Foreshadowing (Cài cắm)** section vào chapter writing prompt để LLM biết các setup details cần plant trong chapter.

## Changes

### 1. Thêm Method Format
```python
def _format_foreshadowing(self, foreshadowing: List[Dict[str, Any]]) -> str:
    # Format: - (tiết lộ c{N}) {detail} (quan trọng: {score})
```

### 2. Update Prompt Template
```
Mâu thuẫn: ...
Foreshadowing (Cài cắm):   ← NEW
- (tiết lộ c3) [detail] (quan trọng: 0.9)
- (tiết lộ c2) [detail] (quan trọng: 0.8)
Địa điểm: ...
```

## Files Modified
- ✅ `src/chapter_writer.py` - Added `_format_foreshadowing()` + updated prompt
- ✅ `test_foreshadowing.py` - Test suite (all passed)
- ✅ `FORESHADOWING_SECTION_UPDATE.md` - Full documentation

## Testing
```bash
python test_foreshadowing.py
# All tests ✅ PASSED
```

## Verify
Generate new chapter và check log file:
```bash
python main.py
cat projects/story_001/logs/llm_requests/chapter_writing_*.txt | grep "Foreshadowing"
```

Should see:
```
Foreshadowing (Cài cắm):
- (tiết lộ c3) Khi trúng độc, Lăng Thiên nhận ra 'Cửu Chuyển Phệ Hồn Tán' có một mùi hương Bạch Ngọc Lan rất nhạt... (quan trọng: 0.9)
```

## How It Works

```mermaid
Outline JSON
    ↓ (foreshadowing array)
_format_foreshadowing()
    ↓ (formatted string)
Prompt Template
    ↓
LLM receives foreshadowing instructions
    ↓
LLM plants setup details in chapter
```

## Example Flow

**Chapter 1 Outline:**
```json
"foreshadowing": [{
  "detail": "Mùi hương Bạch Ngọc Lan từ độc",
  "reveal_chapter": 3,
  "importance": 0.9
}]
```

**Chapter 1 Prompt:**
```
Foreshadowing (Cài cắm):
- (tiết lộ c3) Mùi hương Bạch Ngọc Lan từ độc (quan trọng: 0.9)
```

**Chapter 1 Content:**
```
Lăng Thiên ngửi thấy mùi hương nhạt... "Bạch Ngọc Lan?"...
```

**Chapter 3 Payoff:**
```
"Hóa ra độc có Bạch Ngọc Lan!" Lăng Thiên nhớ lại mùi hương lúc trước...
```

## Status
✅ Implementation complete
✅ Tests passing
✅ Documentation complete
✅ Ready to use

Next: Generate chapters và verify foreshadowing xuất hiện trong log/content!
