"""
Step 2: Outline generator - Generate chapter outlines
"""
import os
from typing import Dict, Any, List, Optional
from src.utils import save_json, load_json


class OutlineGenerator:
    """Generate chapter outlines for story batches."""
    
    def __init__(self, llm_client, checkpoint_manager, logger, config):
        self.llm_client = llm_client
        self.checkpoint = checkpoint_manager
        self.logger = logger
        self.config = config
        self.chapters_per_batch = config['story']['chapters_per_batch']
    
    def generate_initial_outline(self, motif: Dict[str, Any], batch_num: int = 1) -> List[Dict[str, Any]]:
        """
        Generate outline for the first 5 chapters from motif.
        
        Returns list of chapter outlines with key events, characters, conflicts, and foreshadowing.
        """
        step_name = "outline_generation"
        
        # Check checkpoint
        if self.checkpoint.is_step_completed(step_name, batch=batch_num):
            self.logger.info(f"Outline for batch {batch_num} already exists, loading from file")
            return self._load_outline(batch_num)
        
        self.logger.info(f"Generating outline for batch {batch_num} from motif")
        
        # Create prompt for initial outline
        prompt = self._create_initial_outline_prompt(motif)
        
        system_message = """Bạn là một tác giả truyện tu tiên chuyên nghiệp, có khả năng tạo ra các cốt truyện hấp dẫn, 
        phức tạp với các tình tiết đan xen khéo léo. Nhiệm vụ của bạn là tạo outline chi tiết cho 5 chương đầu tiên."""
        
        # Call LLM
        result = self.llm_client.call(
            prompt=prompt,
            task_name=step_name,
            system_message=system_message
        )
        
        # Parse outline from response
        outlines = self._parse_outline_response(result['response'], batch_num)
        
        # Save outline
        self._save_outline(outlines, batch_num)
        
        # Mark as completed
        self.checkpoint.mark_step_completed(
            step_name, 
            batch=batch_num,
            metadata={'num_chapters': len(outlines)}
        )
        
        return outlines
    
    def generate_continuation_outline(self, batch_num: int, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate outline for next 5 chapters with context from previous chapters.
        
        Args:
            batch_num: Batch number
            context: Dictionary containing:
                - super_summary: Brief summary of entire story so far
                - recent_summary: Summary of most recent chapter
                - characters: List of relevant characters
                - entities: List of relevant entities
                - events: List of important events
                - unresolved_conflicts: List of conflicts not yet resolved
                - user_suggestions: Optional user input
        """
        step_name = "outline_generation"
        
        # Check checkpoint
        if self.checkpoint.is_step_completed(step_name, batch=batch_num):
            self.logger.info(f"Outline for batch {batch_num} already exists, loading from file")
            return self._load_outline(batch_num)
        
        self.logger.info(f"Generating continuation outline for batch {batch_num}")
        
        # Create prompt for continuation outline
        prompt = self._create_continuation_outline_prompt(batch_num, context)
        
        system_message = """Bạn là một tác giả truyện tu tiên chuyên nghiệp. Nhiệm vụ của bạn là tiếp tục phát triển 
        cốt truyện một cách hợp lý, giải quyết các mâu thuẫn hiện có đồng thời mở ra hướng phát triển mới."""
        
        # Call LLM
        result = self.llm_client.call(
            prompt=prompt,
            task_name=step_name,
            system_message=system_message
        )
        
        # Parse outline from response
        outlines = self._parse_outline_response(result['response'], batch_num)
        
        # Save outline
        self._save_outline(outlines, batch_num)
        
        # Mark as completed
        self.checkpoint.mark_step_completed(
            step_name,
            batch=batch_num,
            metadata={'num_chapters': len(outlines)}
        )
        
        return outlines
    
    def _create_initial_outline_prompt(self, motif: Dict[str, Any]) -> str:
        """Create prompt for initial outline generation."""
        prompt = f"""Dựa trên motif sau, hãy tạo outline chi tiết cho 5 chương đầu tiên:

**MOTIF:**
- Tiêu đề: {motif.get('title')}
- Mô tả: {motif.get('description')}
- Thể loại: {motif.get('genre')}
- Chủ đề: {', '.join(motif.get('themes', []))}
- Từ khóa: {', '.join(motif.get('keywords', []))}

**YÊU CẦU:**

1. Mỗi chương cần có:
   - Tiêu đề chương
   - Tóm tắt nội dung chính (200-300 từ)
   - Các sự kiện quan trọng (key events) - ít nhất 3-5 sự kiện
   - Nhân vật xuất hiện và vai trò của họ
   - Mâu thuẫn được thiết lập hoặc phát triển
   - Bối cảnh, địa điểm
   - Mục đích và động cơ của nhân vật chính
   - Foreshadowing (nếu có) - các chi tiết nhỏ sẽ quan trọng sau này

2. Yêu cầu về cốt truyện:
   - Chương 1: Giới thiệu nhân vật chính, bối cảnh, và sự kiện khởi đầu
   - Chương 2-4: Phát triển xung đột, giới thiệu thêm nhân vật và thế lực
   - Chương 5: Cao trào nhỏ đầu tiên, mở ra hướng phát triển cho batch tiếp theo
   
3. Cài cắm tình tiết:
   - Một chi tiết nhỏ ở chương 2 sẽ trở thành điểm bất ngờ ở chương 5
   - Ít nhất 2-3 điểm foreshadowing cho các batch sau

4. Định nghĩa các mâu thuẫn theo timeline:
   - Immediate (1 chapter): Cần giải quyết ngay
   - Batch (5 chapters): Giải quyết trong batch này
   - Short-term (10 chapters): Giải quyết trong 10 chương
   - Medium-term (30 chapters): Cốt truyện trung hạn
   - Long-term (100 chapters): Cốt truyện dài hạn
   - Epic (300 chapters): Mâu thuẫn xuyên suốt toàn bộ truyện

**ĐỊNH DẠNG OUTPUT (JSON):**

```json
{{
  "batch": 1,
  "chapters": [
    {{
      "chapter_number": 1,
      "title": "Tên chương",
      "summary": "Tóm tắt nội dung chính...",
      "key_events": [
        {{"event": "Mô tả sự kiện 1", "importance": 0.9}},
        {{"event": "Mô tả sự kiện 2", "importance": 0.7}}
      ],
      "characters": [
        {{
          "name": "Tên nhân vật",
          "role": "Vai trò trong chương này",
          "motivation": "Mục đích, động cơ"
        }}
      ],
      "conflicts": [
        {{
          "description": "Mô tả mâu thuẫn",
          "type": "internal/external/philosophical",
          "timeline": "batch",
          "status": "introduced/developing/resolved"
        }}
      ],
      "settings": ["Địa điểm 1", "Địa điểm 2"],
      "foreshadowing": [
        {{"detail": "Chi tiết cài cắm", "reveal_chapter": 5, "importance": 0.8}}
      ]
    }}
  ]
}}
```

Hãy tạo outline theo đúng định dạng JSON trên."""
        
        return prompt
    
    def _create_continuation_outline_prompt(self, batch_num: int, context: Dict[str, Any]) -> str:
        """Create prompt for continuation outline generation."""
        start_chapter = (batch_num - 1) * self.chapters_per_batch + 1
        end_chapter = start_chapter + self.chapters_per_batch - 1
        
        prompt = f"""Hãy tạo outline cho 5 chương tiếp theo (Chương {start_chapter}-{end_chapter}) dựa trên ngữ cảnh sau:

**NGỮ CẢNH HIỆN TẠI:**

**Tóm tắt toàn bộ truyện:**
{context.get('super_summary', 'Chưa có')}

**Tóm tắt chương gần nhất:**
{context.get('recent_summary', 'Chưa có')}

**Nhân vật liên quan:**
{self._format_characters(context.get('characters', []))}

**Entity liên quan:**
{self._format_entities(context.get('entities', []))}

**Sự kiện quan trọng:**
{self._format_events(context.get('events', []))}

**Mâu thuẫn chưa giải quyết:**
{self._format_conflicts(context.get('unresolved_conflicts', []))}

**Gợi ý từ người dùng:**
{context.get('user_suggestions', 'Không có')}

**YÊU CẦU:**

1. Phải giải quyết ít nhất 1-2 mâu thuẫn có timeline phù hợp với batch này
2. Mở ra ít nhất 1-2 mâu thuẫn mới cho các batch sau
3. Sử dụng các nhân vật và entity đã có một cách hợp lý
4. Tạo sự liên kết chặt chẽ giữa các chương
5. Cài cắm foreshadowing cho các batch sau
6. Xác định rõ mục đích, động cơ của nhân vật chính trong mỗi chương

**ĐỊNH DẠNG OUTPUT (JSON):**

```json
{{
  "batch": {batch_num},
  "chapters": [
    {{
      "chapter_number": {start_chapter},
      "title": "Tên chương",
      "summary": "Tóm tắt nội dung chính...",
      "key_events": [
        {{"event": "Mô tả sự kiện", "importance": 0.9}}
      ],
      "characters": [
        {{
          "name": "Tên nhân vật",
          "role": "Vai trò trong chương này",
          "motivation": "Mục đích, động cơ"
        }}
      ],
      "conflicts": [
        {{
          "description": "Mô tả mâu thuẫn",
          "type": "internal/external/philosophical",
          "timeline": "batch",
          "status": "introduced/developing/resolved"
        }}
      ],
      "settings": ["Địa điểm"],
      "foreshadowing": [
        {{"detail": "Chi tiết cài cắm", "reveal_chapter": null, "importance": 0.8}}
      ],
      "resolved_conflicts": ["ID hoặc mô tả mâu thuẫn đã giải quyết"],
      "new_conflicts": [
        {{
          "description": "Mâu thuẫn mới",
          "timeline": "long-term"
        }}
      ]
    }}
  ]
}}
```

Hãy tạo outline theo đúng định dạng JSON trên."""
        
        return prompt
    
    def _format_characters(self, characters: List[Dict]) -> str:
        """Format characters for prompt."""
        if not characters:
            return "Chưa có"
        return "\n".join([f"- {c.get('name', 'Unknown')}: {c.get('description', '')[:100]}" 
                         for c in characters[:10]])
    
    def _format_entities(self, entities: List[Dict]) -> str:
        """Format entities for prompt."""
        if not entities:
            return "Chưa có"
        return "\n".join([f"- {e.get('name', 'Unknown')} ({e.get('type', 'unknown')}): {e.get('description', '')[:100]}" 
                         for e in entities[:20]])
    
    def _format_events(self, events: List[Dict]) -> str:
        """Format events for prompt."""
        if not events:
            return "Chưa có"
        sorted_events = sorted(events, key=lambda x: x.get('importance', 0), reverse=True)
        return "\n".join([f"- [{e.get('importance', 0):.1f}] {e.get('description', '')}" 
                         for e in sorted_events[:15]])
    
    def _format_conflicts(self, conflicts: List[Dict]) -> str:
        """Format conflicts for prompt."""
        if not conflicts:
            return "Chưa có"
        return "\n".join([f"- [{c.get('timeline', 'unknown')}] {c.get('description', '')}" 
                         for c in conflicts])
    
    def _parse_outline_response(self, response: str, batch_num: int) -> List[Dict[str, Any]]:
        """Parse LLM response to extract outline."""
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                self.logger.error("Failed to extract JSON from response")
                raise ValueError("Could not parse outline from LLM response")
        
        try:
            outline_data = json.loads(json_str)
            return outline_data.get('chapters', [])
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            raise
    
    def _save_outline(self, outlines: List[Dict[str, Any]], batch_num: int):
        """Save outline to file."""
        output_dir = self.config['paths']['output_dir']
        file_path = os.path.join(output_dir, 'outlines', f'batch_{batch_num}_outline.json')
        save_json({'batch': batch_num, 'chapters': outlines}, file_path)
        self.logger.info(f"Saved outline for batch {batch_num} to {file_path}")
    
    def _load_outline(self, batch_num: int) -> List[Dict[str, Any]]:
        """Load outline from file."""
        output_dir = self.config['paths']['output_dir']
        file_path = os.path.join(output_dir, 'outlines', f'batch_{batch_num}_outline.json')
        data = load_json(file_path)
        return data.get('chapters', [])
