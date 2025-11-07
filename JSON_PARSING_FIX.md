# JSON Parsing Fix - v1.3.1

## Vấn đề phát hiện

Khi chạy hệ thống sau khi refactor v1.3.0, gặp lỗi:
```
ERROR - JSON parsing error
```

### Root Cause

Gemini API trả về JSON được bao bọc trong markdown code block:
```json
[
  {...},
  {...}
]
```

Nhưng các parser trong code chỉ tìm JSON object `{...}`, không xử lý được:
- JSON array `[...]`
- Markdown code block wrapper

## Giải pháp

### 1. Thêm utility function chung

**File:** `src/utils.py`

Thêm function `parse_json_from_response()` xử lý tất cả các trường hợp:
- Plain JSON: `{...}` hoặc `[...]`
- Markdown wrapped: ` ```json\n{...}\n``` ` hoặc ` ```json\n[...]\n``` `
- Cả object và array

```python
def parse_json_from_response(response: str) -> Any:
    """
    Parse JSON from LLM response, handling markdown code blocks.
    
    Supports:
    - Plain JSON: {...} or [...]
    - Markdown wrapped: ```json\n{...}\n```
    - Both objects and arrays
    """
    # Try markdown code block first
    json_fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response, re.IGNORECASE)
    if json_fence_match:
        json_str = json_fence_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Try direct JSON parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON object {...}
    obj_match = re.search(r'\{[\s\S]*\}\s*$', response)
    if obj_match:
        return json.loads(obj_match.group(0))
    
    # Try to find JSON array [...]
    arr_match = re.search(r'\[[\s\S]*\]\s*$', response)
    if arr_match:
        return json.loads(arr_match.group(0))
    
    raise json.JSONDecodeError(f"Could not extract JSON from response", response, 0)
```

### 2. Sửa tất cả các parser

#### a. `src/entity_manager.py`

**Vấn đề:**
- Chỉ tìm object `{...}`, không xử lý array `[...]`
- Không có type mapping từ prompt types sang storage keys

**Sửa:**
```python
from src.utils import parse_json_from_response

def _parse_entity_response(self, response: str):
    entities = parse_json_from_response(response)
    
    # Map types: artifact→items, elixir→spiritual_herbs, character→characters
    type_mapping = {
        'character': 'characters',
        'beast': 'beasts',
        'faction': 'factions',
        'artifact': 'items',
        'location': 'locations',
        'technique': 'techniques',
        'elixir': 'spiritual_herbs',
        'other': 'other'
    }
    
    # Convert array to categorized dict
    categorized = {...}
    for entity in entities:
        storage_key = type_mapping.get(entity.get('type', 'other'), 'other')
        categorized[storage_key].append(entity)
    
    return categorized
```

#### b. `src/outline_generator.py`

**Sửa:**
```python
from src.utils import parse_json_from_response

def _parse_outline_response(self, response: str, batch_num: int):
    outline_data = parse_json_from_response(response)
    # Handle both list and object with 'chapters' key
    if isinstance(outline_data, list):
        return outline_data
    return outline_data.get('chapters', [])
```

#### c. `src/post_processor.py`

**Sửa 2 methods:**
```python
from src.utils import parse_json_from_response

def _parse_events_response(self, response: str, chapter_num: int):
    data = parse_json_from_response(response)
    # Handle both list and object with 'events' key
    if isinstance(data, list):
        events = data
    else:
        events = data.get('events', [])
    # Add chapter info...
    return events

def _parse_conflicts_response(self, response: str, chapter_num: int):
    data = parse_json_from_response(response)
    new_conflicts = data.get('new_conflicts', [])
    updated_conflicts = data.get('updated_conflicts', [])
    return new_conflicts, updated_conflicts
```

## Test Results

### Test 1: Parse markdown wrapped JSON array
```python
response = '''```json
[
  {"name": "Trần Phàm", "type": "character"},
  {"name": "Lạc Diệp Trấn", "type": "location"}
]
```'''

result = parse_json_from_response(response)
# ✓ Type: list
# ✓ Length: 2
```

### Test 2: Type mapping
```python
entities = [
  {"type": "character", "name": "Trần Phàm"},
  {"type": "artifact", "name": "Ngọc Bội"},
  {"type": "technique", "name": "Thái Cực Huyền Công"}
]

# After mapping:
# characters: ["Trần Phàm"]
# items: ["Ngọc Bội"]  (artifact → items)
# techniques: ["Thái Cực Huyền Công"]
```

### Test 3: Import all modules
```bash
python3 -c "from src.utils import parse_json_from_response; ..."
# ✓ All modules imported successfully
```

## Files Changed

1. ✅ `src/utils.py` - Added `parse_json_from_response()`
2. ✅ `src/entity_manager.py` - Updated `_parse_entity_response()` with type mapping
3. ✅ `src/outline_generator.py` - Updated `_parse_outline_response()`
4. ✅ `src/post_processor.py` - Updated `_parse_events_response()` and `_parse_conflicts_response()`

## Breaking Changes

Không có breaking changes. Các sửa đổi chỉ cải thiện khả năng parse JSON response.

## Migration Notes

Không cần migration. Code tự động xử lý cả format cũ và mới.

## Related Issues

- GitHub Issue: #N/A (internal fix)
- Reported by: User testing v1.3.0
- Fixed in: v1.3.1
- Date: 2024-11-07

## Next Steps

1. ✅ Test với real API response từ Gemini
2. ⏳ Chạy full pipeline để verify fix
3. ⏳ Monitor logs để ensure không có parsing errors

---

**Version:** 1.3.1  
**Status:** Fixed ✅  
**Author:** AI Assistant  
**Date:** 2024-11-07
