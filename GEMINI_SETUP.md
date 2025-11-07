# Gemini API Setup Guide

## Hướng dẫn cấu hình Gemini API

Hệ thống sử dụng Google Gemini API với khả năng rotation nhiều API keys để tối ưu hiệu suất và tránh rate limit.

## 🔑 Lấy API Keys

1. Truy cập: https://aistudio.google.com/app/apikey
2. Đăng nhập bằng Google Account
3. Click "Create API Key"
4. Copy API key (dạng: `AIzaSy...`)

**Lưu ý:** 
- Gemini API có free tier rất generous
- Khuyến nghị tạo 3-5 keys để rotation
- Mỗi key có rate limit riêng

## 📝 Cấu hình Keys

### Cách 1: Sử dụng file (Khuyến nghị)

Tạo file `auth_files/keys.txt`:

```bash
mkdir -p auth_files
cat > auth_files/keys.txt << EOF
AIzaSyAbc123...key1
AIzaSyDef456...key2
AIzaSyGhi789...key3
EOF
```

**Format:**
- Mỗi key một dòng
- Không có khoảng trắng thừa
- Có thể thêm comment bằng #

Ví dụ:
```
# Key cho testing
AIzaSyAbc123def456ghi789
# Key chính
AIzaSyXyz987uvw654rst321
# Key backup
AIzaSyMno147pqr258stu369
```

### Cách 2: Biến môi trường

```bash
export GOOGLE_API_KEYS="key1,key2,key3"
```

Hoặc trong `.env`:
```
GOOGLE_API_KEYS=key1,key2,key3
```

## ⚙️ Model Configuration

Hệ thống hỗ trợ các model:

### Gemini 2.5 Pro
- **Sử dụng cho:** Chapter writing (nội dung quan trọng)
- **Chi phí:** $1.25/1M input tokens, $5.00/1M output tokens
- **Ưu điểm:** Chất lượng cao, reasoning tốt
- **Config:** `model: "gemini-2.5-pro"`

### Gemini 2.5 Flash (Default)
- **Sử dụng cho:** Outline, entity extraction, summaries
- **Chi phí:** $0.075/1M input tokens, $0.30/1M output tokens
- **Ưu điểm:** Nhanh, rẻ, chất lượng tốt
- **Config:** `model: "gemini-2.5-flash"`

### Gemini 2.5 Flash Lite
- **Sử dụng cho:** Fallback khi Flash bị lỗi
- **Chi phí:** $0.0375/1M input tokens, $0.15/1M output tokens
- **Ưu điểm:** Rất rẻ, nhanh
- **Config:** `model: "gemini-2.5-flash-lite"`

### Gemma 3 27B IT
- **Sử dụng cho:** Testing, experimental
- **Chi phí:** Free
- **Lưu ý:** Open source model, có thể không ổn định
- **Config:** `model: "gemma-3-27b-it"`

## 🔧 Cấu hình chi tiết

Trong `config/config.yaml`:

```yaml
# Default LLM Settings
default_llm:
  provider: "gemini"
  model: "gemini-2.5-flash"
  temperature: 0.7
  keys_file: "auth_files/keys.txt"

# Task-specific
task_configs:
  chapter_writing:
    model: "gemini-2.5-pro"  # Dùng Pro cho viết chapter
    temperature: 0.85
    
  outline_generation:
    model: "gemini-2.5-flash"
    temperature: 0.8
    
  entity_extraction:
    model: "gemini-2.5-flash"
    temperature: 0.3
```

## 🔄 Key Rotation & Error Handling

Hệ thống tự động:

1. **Load keys** từ file hoặc env
2. **Shuffle ngẫu nhiên** để phân phối load
3. **Rotate keys** khi gặp HTTP 429 (rate limit)
4. **Disable keys** bị lỗi liên tục
5. **Log disabled keys** với timestamp
6. **Auto-enable** sau 5 giờ

### Disable Log

File `auth_files/disable_log.json` lưu keys bị disable:

```json
[
  {
    "key": "AIzaSy...abc",
    "disabled_at": "2025-01-07 14:30:22"
  }
]
```

Keys tự động được enable lại sau 5 giờ.

## 🛡️ Rate Limiting

Gemini API có rate limits:

- **Free tier:** 15 requests/minute, 1,500 requests/day
- **Paid tier:** Cao hơn nhiều

**Chiến lược:**
- Dùng nhiều keys (3-5 keys)
- Tự động rotation khi 429
- Sleep giữa các requests
- Retry logic thông minh

## 💰 Chi phí ước tính

Cho một truyện 50 chapters (5000 từ/chapter):

### Sử dụng Gemini 2.5 Pro cho tất cả:
- Input: ~2.5M tokens × $1.25/1M = $3.13
- Output: ~10M tokens × $5.00/1M = $50.00
- **Tổng: ~$53**

### Sử dụng Pro (chapter) + Flash (khác):
- Chapter writing: ~$40
- Other tasks: ~$1-2
- **Tổng: ~$42**

### Sử dụng chỉ Flash:
- Tất cả tasks: ~$3-5
- **Tổng: ~$5**

**Khuyến nghị:** Dùng Pro cho chapter writing, Flash cho các task khác.

## 🐛 Troubleshooting

### Lỗi: No API keys found

```bash
# Kiểm tra file
cat auth_files/keys.txt

# Hoặc check env
echo $GOOGLE_API_KEYS

# Tạo file mới
mkdir -p auth_files
nano auth_files/keys.txt
```

### Lỗi: HTTP 429 (Rate Limit)

Hệ thống tự động xử lý:
1. Retry 3 lần
2. Rotate sang key khác
3. Sleep 30s giữa các retry

Nếu vẫn lỗi:
- Thêm nhiều keys hơn
- Tăng `per_job_sleep` trong config
- Dùng paid tier

### Lỗi: HTTP 503 (Service Unavailable)

```bash
# Retry 3 lần với sleep 60s
# Nếu vẫn lỗi, đợi một lúc và thử lại
```

### Keys bị disable liên tục

```bash
# Xem log
cat auth_files/disable_log.json

# Xóa log để force enable
rm auth_files/disable_log.json

# Hoặc đợi 5 giờ để auto-enable
```

## 📊 Monitoring

Kiểm tra usage:

```bash
# Xem cost summary
cat output/cost_summary.json

# Xem logs
tail -f logs/StoryGenerator_*.log

# Xem disabled keys
cat auth_files/disable_log.json
```

## 🔐 Security Best Practices

1. **Không commit keys** vào git
   - `auth_files/keys.txt` đã có trong `.gitignore`
   
2. **Rotation định kỳ**
   - Tạo keys mới mỗi tháng
   
3. **Monitoring**
   - Theo dõi usage qua Google AI Studio
   - Check cost summary thường xuyên

4. **Restrict keys**
   - Set IP restrictions nếu có IP tĩnh
   - Enable usage limits

## 📚 Tài liệu tham khảo

- Gemini API Docs: https://ai.google.dev/docs
- Pricing: https://ai.google.dev/pricing
- API Keys: https://aistudio.google.com/app/apikey
- Rate Limits: https://ai.google.dev/docs/rate_limits

---

**Happy Writing!** 🚀📖
