# Quick Summary - Version 1.2.0 Update

## Thay đổi chính

### Mục đích
Mỗi lần gọi API Gemini sẽ sử dụng một API key ngẫu nhiên khác nhau để:
- Phân tán tải đều trên tất cả các keys
- Giảm nguy cơ bị rate limit
- Tự động loại bỏ keys đã bị disable

### Các file đã thay đổi

#### 1. `src/gemini_client_pool.py`
- ✅ Thêm `_get_config_keys_path()` - load path từ config.yaml
- ✅ Cập nhật `load_keys()` - tự động load từ config, shuffle ngẫu nhiên
- ✅ Đơn giản hóa `gemini_call_text_free()` - loại bỏ params keys, keys_file, keys_env
- ✅ Đơn giản hóa `gemini_call_json_free()` - loại bỏ params keys, keys_file, keys_env  
- ✅ Đơn giản hóa `gemini_batch()` - loại bỏ params keys, keys_file, keys_env
- ✅ Mỗi lần gọi API sẽ `load_keys()` mới → shuffle → chọn random key

#### 2. `src/llm_client.py`
- ✅ Loại bỏ `load_keys` import
- ✅ Loại bỏ `self.api_keys` trong `__init__()`
- ✅ Loại bỏ tham số `keys=self.api_keys` khi gọi gemini functions
- ✅ Keys giờ được load tự động trong mỗi lần call

#### 3. Documentation
- ✅ `REFACTORING_NOTES.md` - chi tiết kỹ thuật về thay đổi
- ✅ `CHANGELOG.md` - thêm version 1.2.0
- ✅ `test_random_keys.py` - script test random key selection

### Breaking Changes ⚠️

**Không còn hoạt động:**
```python
# ❌ Truy cập client.api_keys
client = LLMClient(config, logger, cost_tracker)
my_keys = client.api_keys  # AttributeError!

# ❌ Truyền keys vào gemini functions
response = gemini_call_text_free(
    system_prompt="...",
    user_prompt="...",
    keys=my_keys,  # TypeError!
    keys_file="..."  # TypeError!
)
```

**Cách sử dụng mới:**
```python
# ✅ Không cần làm gì với keys
client = LLMClient(config, logger, cost_tracker)

# ✅ Keys tự động load từ config
response = client.call(
    prompt="...",
    task_name="chapter_writing"
)

# ✅ Hoặc gọi trực tiếp
response = gemini_call_text_free(
    system_prompt="...",
    user_prompt="..."
    # Keys tự động load
)
```

### Cách hoạt động

```
Luồng cũ (v1.1):
LLMClient.__init__() 
  → load_keys() once
  → cache trong self.api_keys
  → mỗi call dùng lại cache
  → luôn dùng key đầu tiên trong pool

Luồng mới (v1.2):
Mỗi API call
  → load_keys() fresh
  → load từ config/config.yaml -> default_llm.keys_file
  → shuffle ngẫu nhiên
  → loại bỏ disabled keys (dưới 5h)
  → tạo KeyPool mới
  → lấy key ngẫu nhiên
  → call API
```

### Configuration

Trong `config/config.yaml`:
```yaml
default_llm:
  provider: "gemini"
  model: "gemini-2.5-flash"
  keys_file: "auth_files/keys.txt"  # ← Path này được dùng tự động
```

Trong `auth_files/keys.txt`:
```
AIzaSyAbc123...
AIzaSyDef456...
AIzaSyGhi789...
```

### Testing

Chạy test:
```bash
python test_random_keys.py
```

Test sẽ verify:
- ✅ Keys load được từ config
- ✅ Mỗi API call hoạt động độc lập
- ✅ Keys được chọn ngẫu nhiên

### Benefits

1. **Load Distribution** - Mỗi call dùng key khác nhau → phân tán tải tốt hơn
2. **Auto-Refresh** - Keys tự động refresh mỗi call → không cần restart
3. **Simpler Code** - Ít state, ít bugs, dễ maintain
4. **Config-Driven** - Thay đổi keys path dễ dàng qua config

### Files Overview

```
Các file đã sửa:
- src/gemini_client_pool.py  (27K) - Core changes
- src/llm_client.py          (5.8K) - Simplified 
- CHANGELOG.md               (7.2K) - Version 1.2.0
- REFACTORING_NOTES.md       (6.6K) - Technical details

Các file mới:
- test_random_keys.py        (2.4K) - Test script
- QUICK_SUMMARY_v1.2.md      (này)  - Quick reference

Không đổi:
- main.py, scripts.py, config.yaml
- Tất cả các file khác
```

### Next Steps

1. **Đảm bảo có keys**: Tạo `auth_files/keys.txt` với ít nhất 1 key
2. **Test**: Chạy `python test_random_keys.py`
3. **Sử dụng bình thường**: Code hiện tại vẫn hoạt động, chỉ đơn giản hơn

### Questions?

Xem chi tiết trong `REFACTORING_NOTES.md`
