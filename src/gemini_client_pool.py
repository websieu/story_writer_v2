# gemini_client_pool.py
# -*- coding: utf-8 -*-
"""
Client gom chuẩn: dùng requests + KeyPool + retry (429, net), fallback model.
API chính:
  - gemini_call_text_free(system_prompt, user_prompt, *, model="gemini-2.5-flash", temperature=0.3, ...)
  - gemini_call_json_free(system_prompt, user_prompt, *, model="gemini-2.5-flash", temperature=0.3, ...)
  - gemini_batch(calls=[...], model=..., temperature=..., keys=[...], ...)
"""

import os, json, time, math, random, threading, queue, unicodedata
import requests
import regex as re
from typing import Optional, Tuple, Any, Dict, List

try:
    from openai import OpenAI  # type: ignore
except ImportError:
    OpenAI = None  # type: ignore[assignment]

try:
    from Utils.read_config import DEEPSEEK_API as CONFIG_DEEPSEEK_API  # type: ignore
except Exception:
    CONFIG_DEEPSEEK_API = None

def _env_float(name: str, default: float) -> float:
    try:
        raw = os.getenv(name)
        return float(raw) if raw is not None else default
    except (TypeError, ValueError):
        return default

def _env_int(name: str, default: Optional[int] = None) -> Optional[int]:
    try:
        raw = os.getenv(name)
        return int(raw) if raw is not None else default
    except (TypeError, ValueError):
        return default

# =========================
# Config
# =========================
#MODEL_PRIMARY   = os.getenv("GEM_MODEL_PRIMARY",   "gemini-2.5-flash")
MODEL_PRIMARY   = os.getenv("GEM_MODEL_PRIMARY",   "gemma-3-27b-it")
MODEL_FALLBACK  = os.getenv("GEM_MODEL_FALLBACK",  "gemini-2.5-flash-lite")
MODEL_GEMMA_FBK = os.getenv("GEM_MODEL_GEMMAFBK",  "gemma-3-27b-it")  # optional

DEFAULT_PER_JOB_SLEEP = float(os.getenv("GEM_PER_JOB_SLEEP", "10"))  # giữa 2 job (giảm rate)
RETRY_429_LIMIT   = int(os.getenv("GEM_RETRY_429", "3"))
RETRY_OTHER_LIMIT = int(os.getenv("GEM_RETRY_OTHER", "3"))

TIMEOUT_S = int(os.getenv("GEM_TIMEOUT_S", "240"))

DEFAULT_PROVIDER = (os.getenv("FREE_CALL_PROVIDER") or "deepseek").strip().lower()
_raw_deepseek_model = os.getenv("DEEPSEEK_MODEL_PRIMARY") or os.getenv("DEEPSEEK_MODEL")
DEFAULT_DEEPSEEK_MODEL = (_raw_deepseek_model.strip() if _raw_deepseek_model else "deepseek-chat")
DEEPSEEK_DEFAULT_TEMPERATURE = _env_float("DEEPSEEK_TEMPERATURE", 0.7)
DEEPSEEK_DEFAULT_TOP_P = _env_float("DEEPSEEK_TOP_P", 0.95)
DEEPSEEK_DEFAULT_MAX_TOKENS = _env_int("DEEPSEEK_MAX_TOKENS")
DEEPSEEK_PER_JOB_SLEEP = _env_float("DEEPSEEK_PER_JOB_SLEEP", 0.0)

# =========================
# Helpers
# =========================
def endpoint_for_model(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def _is_gemma(model: str) -> bool:
    return "gemma" in model

def _resolve_deepseek_api_key(explicit: Optional[str] = None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    for candidate in (os.getenv("DEEPSEEK_API_KEY"), os.getenv("deepseek_api"), CONFIG_DEEPSEEK_API):
        if candidate:
            return str(candidate).strip()
    raise RuntimeError("Thiếu DEEPSEEK_API_KEY/deepseek_api để sử dụng DeepSeek.")

def _get_deepseek_client(api_key: Optional[str] = None, base_url: Optional[str] = None):
    if OpenAI is None:
        raise RuntimeError("Thiếu thư viện openai; cần cài đặt để dùng DeepSeek.")
    key = _resolve_deepseek_api_key(api_key)
    url = (base_url or os.getenv("DEEPSEEK_API_BASE") or "https://api.deepseek.com").strip()
    return OpenAI(api_key=key, base_url=url)

def _deepseek_chat_once(client, system_prompt: str, user_prompt: str, *,
                        model: str, temperature: float, top_p: float,
                        max_tokens: Optional[int] = None) -> str:
    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": float(temperature),
        "top_p": float(top_p),
        "stream": False,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    resp = client.chat.completions.create(**payload)
    choice = (resp.choices or [None])[0]
    text = getattr(choice, "message", None)
    if text:
        content = getattr(text, "content", "") or ""
    else:
        content = ""
    return content.strip()

def _build_payload(system_prompt: Optional[str], user_prompt: str, *, temperature: float, model: str,
                   response_mime_type: Optional[str] = None) -> dict:
    # Giữ đúng cách gửi giống script dịch
    print(f"Building payload for model '{model}'")
    text = user_prompt
    if _is_gemma(model) and system_prompt:
        text = system_prompt + "\n\n" + user_prompt

    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {"temperature": float(temperature)},
    }
    #print(f"Building payload for model '{model}' with temperature {temperature}")
    if (not _is_gemma(model)) and system_prompt:
        payload["systemInstruction"] = {"role": "system", "parts": [{"text": system_prompt}]}
        payload['generationConfig'] = {  "thinkingConfig": { "thinkingBudget": -1 }
  }
    if response_mime_type:
        # Gemini tôn trọng response_mime_type ở generationConfig (v1beta)
        payload["generationConfig"]["response_mime_type"] = response_mime_type
    return payload

def _extract_text_from_gemini(resp_json: dict) -> Optional[str]:
    # giống script dịch
    try:
        for c in (resp_json.get("candidates") or []):
            parts = (c.get("content") or {}).get("parts") or []
            for p in parts:
                t = p.get("text")
                if isinstance(t, str):
                    return t
    except Exception:
        pass
    # prompt blocked?
    try:
        fb = resp_json.get("promptFeedback") or {}
        br = fb.get("blockReason")
        if br:
            return "blocked_content"
    except Exception:
        pass
    return None

# Bóc JSON từ text model trả về
JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
def _try_json_loads(s: str):
    try:
        return json.loads(s)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}\s*$", s)
    if m:
        return json.loads(m.group(0))
    m2 = re.search(r"\[[\s\S]*\]\s*$", s)
    if m2:
        return json.loads(m2.group(0))
    raise

def parse_json_from_model(text: str):
    if not text:
        raise RuntimeError("Empty model text")
    fences = JSON_FENCE_RE.findall(text)
    for block in fences:
        block = block.strip()
        if not block:
            continue
        try:
            return json.loads(block)
        except Exception:
            return _try_json_loads(block)
    return _try_json_loads(text)

# =========================
# KeyPool
# =========================
class KeyPool:
    def __init__(self, keys: List[str]):
        rnd = list(dict.fromkeys([k.strip() for k in keys if k.strip()]))
        random.SystemRandom().shuffle(rnd)
        self._avail = queue.Queue()
        for k in rnd:
            self._avail.put(k)
        self._dead = set()
        self._lock = threading.Lock()

    def get_key(self, block=True, timeout=None) -> Optional[str]:
        try:
            return self._avail.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def return_key(self, key: str):
        with self._lock:
            if key in self._dead:
                return
        self._avail.put(key)

    def disable_key(self, key: str):
        with self._lock:
            self._dead.add(key)

def _get_config_keys_path() -> Optional[str]:
    """Load keys file path from config.yaml."""
    try:
        import yaml
        config_path = "config/config.yaml"
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                keys_file = config.get("default_llm", {}).get("keys_file")
                if keys_file:
                    return keys_file
    except Exception as exc:
        print(f"Warning: Failed to load keys path from config: {exc}")
    return None

def load_keys(keys_file: Optional[str] = None, keys_env: Optional[str] = None) -> List[str]:
    """
    Load Gemini API keys from file or environment.
    If keys_file is None, try to load from config.yaml first, then fallback to auth_files/keys.txt.
    """
    print("Loading Gemini API keys...")
    keys: List[str] = []
    
    # Determine keys file path
    if keys_file is None:
        # Try to get from config first
        keys_file = _get_config_keys_path()
        # Fallback to default
        if keys_file is None:
            keys_file = "auth_files/keys.txt"
    
    # Load from file
    if keys_file and os.path.exists(keys_file):
        with open(keys_file, "r", encoding="utf-8") as f:
            for line in f:
                k = line.strip()
                if k:
                    keys.append(k)
    
    # Load from environment
    env = keys_env or os.getenv("GOOGLE_API_KEYS") or ""
    for k in env.split(","):
        k = k.strip()
        if k:
            keys.append(k)
    
    # unique-preserving
    keys = list(dict.fromkeys(keys))

    # Đảo trộn ngẫu nhiên
    random.SystemRandom().shuffle(keys)
    print(f"Loaded {len(keys)} Gemini API keys from {keys_file}.")
    
    # Loại bỏ các key đã bị disable trong vòng 5 giờ qua
    disable_log_path = "auth_files/disable_log.json"
    disabled_keys = set()
    now = time.time()
    if os.path.exists(disable_log_path):
        try:
            with open(disable_log_path, "r", encoding="utf-8") as f:
                log_data = json.load(f)
            for entry in log_data:
                key = entry.get("key")
                disabled_at_str = entry.get("disabled_at")
                if key and disabled_at_str:
                    try:
                        # Chuyển disabled_at sang timestamp
                        disabled_at_ts = time.mktime(time.strptime(disabled_at_str, "%Y-%m-%d %H:%M:%S"))
                        # Nếu bị disable dưới 5h thì loại bỏ
                        if now - disabled_at_ts < 5 * 3600:
                            disabled_keys.add(key)
                    except Exception:
                        continue
        except Exception as exc:
            print(f"Warning: Failed to read disable_log.json: {exc}")

    # Giữ lại các key chưa bị disable hoặc đã bị disable trên 5h
    keys = [k for k in keys if k not in disabled_keys]
    print(f"After filtering disabled keys: {len(keys)} active keys.")
    return keys

# =========================
# Low-level single request
# =========================

def _request_once(session: requests.Session, key: str, model: str, payload: dict) -> str:
    headers = {"Content-Type": "application/json", "x-goog-api-key": key}
    url = endpoint_for_model(model)
    proxies = {
        "http": 'ipv6vn3.id.proxyxoay.net:8826:gscl4f2j:gSCL4f2J',
        
    }
    resp = session.post(url, headers=headers, json=payload, timeout=TIMEOUT_S, proxies=proxies)
    if resp.status_code >= 400:
        raise requests.HTTPError(resp.text, response=resp)
    out = _extract_text_from_gemini(resp.json())
    return out or ""

# =========================
# Public: single-call text / json
# =========================

def gemini_call_text_free(system_prompt: str, user_prompt: str, *,
                     model: Optional[str] = None,
                     temperature: float = 0.3,
                     response_mime_type: Optional[str] = None,
                     per_job_sleep: float = DEFAULT_PER_JOB_SLEEP) -> str:
    """
    Trả về string (không ép JSON). Tự xoay key khi 429, fallback model nếu non-429.
    Mỗi lần gọi sẽ load lại keys từ config để sử dụng key ngẫu nhiên.
    """
    _model = model or MODEL_PRIMARY
    # Load keys mới mỗi lần gọi để sử dụng key ngẫu nhiên
    _keys = load_keys()
    if not _keys:
        raise RuntimeError("No API keys provided.")
    pool = KeyPool(_keys)

    session = requests.Session()
    key = pool.get_key(block=False)
    if key is None:
        raise RuntimeError("Key pool empty.")

    try_count_429 = 0
    try_count_other = 0
    cur_model = _model

    while True:
        try:
            payload = _build_payload(system_prompt, user_prompt,
                                     temperature=temperature, model=cur_model,
                                     response_mime_type=response_mime_type)
            print(f"[gemini_call_text_free] Requesting model '{cur_model}' with key '{key}'")
            text = _request_once(session, key, cur_model, payload)

            # Nếu model trả "blocked_content" coi như empty
            if not text or text == "blocked_content":
                # cho retry nhẹ nhàng 2 lần
                try_count_other += 1
                if try_count_other <= RETRY_OTHER_LIMIT:
                    time.sleep(2.0)
                    continue
            time.sleep(per_job_sleep)
            return text

        except requests.HTTPError as err:
            status = getattr(err, "response", None).status_code if getattr(err, "response", None) is not None else -1
            if status == 429:
                try_count_429 += 1
                if try_count_429 < RETRY_429_LIMIT:
                    print(f"[gemini_call_text_free] HTTP 429 received, retrying... (attempt {try_count_429}/{RETRY_429_LIMIT})")
                    time.sleep(30.0); continue
                # disable key và lấy key mới
                pool.disable_key(key)
                # Log disabled key with timestamp
                try:
                    log_path = "auth_files/disable_log.json"
                    os.makedirs(os.path.dirname(log_path), exist_ok=True)
                    log_entry = {"key": key, "disabled_at": time.strftime("%Y-%m-%d %H:%M:%S")}
                    if os.path.exists(log_path):
                        with open(log_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if not isinstance(data, list):
                            data = []
                    else:
                        data = []
                    data.append(log_entry)
                    with open(log_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception as log_exc:
                    print(f"Warning: Failed to log disabled key: {log_exc}")
                new_key = pool.get_key(block=False)
                if not new_key:
                    raise
                key = new_key
                try_count_429 = 0
                continue
            elif status == 503:
               
                try_count_other += 1
                if try_count_other < RETRY_OTHER_LIMIT:
                    print(f"[gemini_call_text_free] HTTP 503 received, retrying... (attempt {try_count_other}/{RETRY_OTHER_LIMIT})")
                    time.sleep(60); continue
                raise
                
            else:
                # non-429 → thử fallback model
                if cur_model != MODEL_FALLBACK:
                    cur_model = MODEL_FALLBACK
                    print(f"[gemini_call_text_free] Fallback sang model '{cur_model}' do HTTP {status}")
                    time.sleep(3.0)
                    continue
                try_count_other += 1
                if try_count_other < RETRY_OTHER_LIMIT:
                    time.sleep(5.0); continue
                raise

        except (requests.ConnectionError, requests.Timeout):
            try_count_other += 1
            if try_count_other < RETRY_OTHER_LIMIT:
                time.sleep(5.0); continue
            raise

def gemini_call_json_free(system_prompt: str, user_prompt: str, *,
                     model: Optional[str] = None,
                     temperature: float = 0.3,
                     per_job_sleep: float = DEFAULT_PER_JOB_SLEEP) -> Any:
    """
    Gọi model và bóc JSON an toàn.
    Mỗi lần gọi sẽ load lại keys từ config để sử dụng key ngẫu nhiên.
    """
    txt = gemini_call_text_free(system_prompt, user_prompt,
                           model=model,
                           temperature=temperature,
                           response_mime_type="application/json",
                           per_job_sleep=per_job_sleep)
    # Một số model vẫn có thể trả text lẫn -> vẫn bóc thông minh
    try:
        return parse_json_from_model(txt)
    except Exception:
        # cố thêm 1 lần không đặt response_mime_type
        print(f"[gemini_call_json_free] Thử lại không đặt response_mime_type")
        txt2 = gemini_call_text_free(system_prompt, user_prompt,
                                model=model,
                                temperature=temperature,
                                response_mime_type=None,
                                per_job_sleep=per_job_sleep)
        return parse_json_from_model(txt2)

# =========================
# Public: batch (multi-thread)
# =========================
def gemini_batch(
    calls: List[Dict[str, Any]],
    *,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_workers: Optional[int] = None,
    per_job_sleep: float = DEFAULT_PER_JOB_SLEEP,
) -> List[Dict[str, Any]]:
    """
    Batch nhiều yêu cầu song song.
    calls: [{ "type": "json"/"text", "system": "...", "user": "...", "meta": {...}}, ...]
    Trả: list kết quả có cùng thứ tự: {"ok": True/False, "result": <obj or str>, "error": str|None, "meta": {...}}
    Mỗi lần gọi sẽ load lại keys từ config để sử dụng key ngẫu nhiên.
    """
    # Load keys mới mỗi lần gọi để sử dụng key ngẫu nhiên
    _keys = load_keys()
    if not _keys: 
        raise RuntimeError("No API keys provided.")
    pool = KeyPool(_keys)
    session = requests.Session()

    n_workers = max_workers if max_workers is not None else len(_keys)
    n_workers = max(1, min(n_workers, len(_keys)))

    job_q: "queue.Queue[Tuple[int, Dict[str, Any]]]" = queue.Queue()
    for i, c in enumerate(calls):
        job_q.put((i, c))
    results: List[Dict[str, Any]] = [None] * len(calls)  # type: ignore
    lock = threading.Lock()

    def _worker():
        key = pool.get_key(block=False)
        if key is None:
            return
        while True:
            try:
                idx, call = job_q.get_nowait()
            except queue.Empty:
                pool.return_key(key); return

            system = call.get("system") or ""
            user   = call.get("user") or ""
            typ    = (call.get("type") or "text").lower()
            meta   = call.get("meta")

            cur_model = model or MODEL_PRIMARY
            try_429 = 0
            try_other = 0

            while True:
                try:
                    payload = _build_payload(system, user, temperature=temperature, model=cur_model,
                                             response_mime_type=("application/json" if typ=="json" else None))
                    print(f"[gemini_batch] Worker processing job {idx} with key '{key}'")
                    text = _request_once(session, key, cur_model, payload)
                    if not text or text == "blocked_content":
                        try_other += 1
                        if try_other <= RETRY_OTHER_LIMIT:
                            time.sleep(2.0); continue

                    if typ == "json":
                        try:
                            data = parse_json_from_model(text)
                        except Exception:
                            # thêm 1 lần không response_mime_type
                            payload2 = _build_payload(system, user, temperature=temperature, model=cur_model)
                            text2 = _request_once(session, key, cur_model, payload2)
                            data = parse_json_from_model(text2)
                        with lock:
                            results[idx] = {"ok": True, "result": data, "error": None, "meta": meta}
                    else:
                        with lock:
                            results[idx] = {"ok": True, "result": text, "error": None, "meta": meta}

                    time.sleep(per_job_sleep)
                    job_q.task_done()
                    break

                except requests.HTTPError as err:
                    status = getattr(err, "response", None).status_code if getattr(err, "response", None) is not None else -1
                    if status == 429:
                        try_429 += 1
                        if try_429 < RETRY_429_LIMIT:
                            print(f"[gemini_batch] Retry {try_429}/{RETRY_429_LIMIT} for 429")
                            time.sleep(20.0); continue
                        pool.disable_key(key)
                        new_key = pool.get_key(block=False)
                        if not new_key:
                            with lock:
                                results[idx] = {"ok": False, "result": None, "error": f"429 with no key left", "meta": meta}
                            job_q.task_done(); return
                        key = new_key
                        try_429 = 0
                        continue
                    
                    else:
                        print(f"[gemini_batch] HTTP error {err} on model '{cur_model}'")
                        if cur_model != MODEL_FALLBACK:
                            cur_model = MODEL_FALLBACK
                            print(f"[gemini_batch] Fallback sang model '{cur_model}' do HTTP {status}")
                            time.sleep(3.0); continue
                        try_other += 1
                        if try_other < RETRY_OTHER_LIMIT:
                            time.sleep(5.0); continue
                        with lock:
                            results[idx] = {"ok": False, "result": None, "error": f"HTTP {status}", "meta": meta}
                        job_q.task_done(); break

                except (requests.ConnectionError, requests.Timeout) as e:
                    try_other += 1
                    if try_other < RETRY_OTHER_LIMIT:
                        time.sleep(5.0); continue
                    with lock:
                        results[idx] = {"ok": False, "result": None, "error": f"Net {type(e).__name__}", "meta": meta}
                    job_q.task_done(); break

    threads = []
    for _ in range(n_workers):
        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    # fill any None (shouldn't) with error
    for i in range(len(results)):
        if results[i] is None:
            results[i] = {"ok": False, "result": None, "error": "unknown", "meta": calls[i].get("meta")}
    return results

# =========================
# Public: DeepSeek batch (sequential)
# =========================
def deepseek_batch(
    calls: List[Dict[str, Any]],
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    max_tokens: Optional[int] = None,
    per_job_sleep: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Sequential batch helper for DeepSeek chat completions.
    Mirrors gemini_batch return schema for a drop-in swap.
    """
    if not calls:
        return []

    client = _get_deepseek_client(api_key=api_key, base_url=base_url)
    _model = (model or DEFAULT_DEEPSEEK_MODEL or "deepseek-chat").strip()
    _temp = DEEPSEEK_DEFAULT_TEMPERATURE if temperature is None else float(temperature)
    _top_p = DEEPSEEK_DEFAULT_TOP_P if top_p is None else float(top_p)
    _max_tokens = DEEPSEEK_DEFAULT_MAX_TOKENS if max_tokens is None else max_tokens
    sleep_time = DEEPSEEK_PER_JOB_SLEEP if per_job_sleep is None else float(per_job_sleep)

    results: List[Dict[str, Any]] = []
    for call in calls:
        system = call.get("system") or ""
        user = call.get("user") or ""
        typ = (call.get("type") or "text").lower()
        meta = call.get("meta")
        try:
            text = _deepseek_chat_once(
                client,
                system,
                user,
                model=_model,
                temperature=_temp,
                top_p=_top_p,
                max_tokens=_max_tokens,
            )
            if not text:
                raise RuntimeError("DeepSeek trả về nội dung rỗng.")

            if typ == "json":
                parsed = parse_json_from_model(text)
                results.append({"ok": True, "result": parsed, "error": None, "meta": meta})
            else:
                results.append({"ok": True, "result": text, "error": None, "meta": meta})
        except Exception as exc:
            results.append({"ok": False, "result": None, "error": str(exc), "meta": meta})
        if sleep_time > 0:
            time.sleep(sleep_time)
    return results

# =========================
# Dispatcher
# =========================
def multimodel_batch(
    calls: List[Dict[str, Any]],
    *,
    provider: Optional[str] = None,
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """
    Selects DeepSeek or Gemini implementation based on provider.
    - provider: overrides FREE_CALL_PROVIDER env (default "deepseek").
    Remaining kwargs are forwarded to the underlying batch helper.
    """
    provider_norm = (provider or DEFAULT_PROVIDER or "deepseek").strip().lower()

    if any(tag in provider_norm for tag in ("gemini", "gemma", "google")):
        return gemini_batch(calls, **kwargs)
    if "deepseek" in provider_norm:
        return deepseek_batch(calls, **kwargs)
    raise ValueError(f"Unsupported provider: {provider}")

if __name__ == "__main__":
    # Simple test
    system = ""
    user = "Hãy viết bố cục cho 5 chương truyện tiên hiệp. MC là đại đế vĩ đại bị phản bội, phong ấn ngàn năm vừa thức tỉnh, mục tiêu của MC là khôi phục kinh mạch, thăng tiến cảnh giới từ phàm thể lên Kim Đan. Đạt được 1 bảo vật để hỗ trợ tu luyện, trải qua 3 cuộc chiến thể hiện sự bá đạo, tài trí, diệt kẻ tiểu nhân. MC tuy mất hết tu vi nhưng vẫn mang trong mình sức mạnh cường đại và kinh nghiệm của đại đế. Yêu cầu bố cục logic, các chương có sự liên kết chặt chẽ với nhau, k kết chương mà cần có vấn đề mở để phát triển tiếp."
    while True:
        print("=== Gemini Text ===")
        gemini_text = gemini_call_text_free(system, user, model="gemini-2.5-pro", temperature=1)
        print(gemini_text)
        time.sleep(30)
        print("sleep 30s... done, next call.")
    