"""
Step 2: Outline generator - Generate chapter outlines (Updated version with conflict-driven logic)
"""
import os
from typing import Dict, Any, List, Optional
from src.utils import save_json, load_json, parse_json_from_response


class OutlineGenerator:
    """Generate chapter outlines for story batches."""
    
    def __init__(self, llm_client, checkpoint_manager, logger, config, paths):
        self.llm_client = llm_client
        self.checkpoint = checkpoint_manager
        self.logger = logger
        self.config = config
        self.paths = paths
        self.chapters_per_batch = config['story']['chapters_per_batch']
        # Will be injected by main.py
        self.entity_manager = None
        self.post_processor = None
    
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
        
        # Call LLM with batch_id
        result = self.llm_client.call(
            prompt=prompt,
            task_name=step_name,
            system_message=system_message,
            batch_id=batch_num
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
                - active_conflicts: List of active conflicts from previous batch
                - related_characters: Characters related to active conflicts
                - related_entities: Entities related to active conflicts
                - related_events: Events related to characters/entities
                - user_suggestions: Optional user input
        """
        step_name = "outline_generation"
        
        # Check checkpoint
        if self.checkpoint.is_step_completed(step_name, batch=batch_num):
            self.logger.info(f"Outline for batch {batch_num} already exists, loading from file")
            return self._load_outline(batch_num)
        
        self.logger.info(f"Generating continuation outline for batch {batch_num}")
        
        # Step 1: Analyze conflicts and determine which to resolve/develop
        conflict_plan = self._analyze_conflicts_for_batch(batch_num, context)
        
        # Step 2: Create prompt for continuation outline with conflict plan
        prompt = self._create_continuation_outline_prompt(batch_num, context, conflict_plan)
        
        system_message = """Bạn là một tác giả truyện tu tiên chuyên nghiệp. Nhiệm vụ của bạn là tiếp tục phát triển 
        cốt truyện một cách hợp lý, giải quyết các mâu thuẫn hiện có đồng thời mở ra hướng phát triển mới."""
        
        # Call LLM with batch_id
        result = self.llm_client.call(
            prompt=prompt,
            task_name=step_name,
            system_message=system_message,
            batch_id=batch_num
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
    
    def _analyze_conflicts_for_batch(self, batch_num: int, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze active conflicts and determine which should be resolved or developed in this batch.
        
        Returns:
            Dictionary with conflict planning information
        """
        self.logger.info(f"Analyzing conflicts for batch {batch_num}")
        
        active_conflicts = context.get('active_conflicts', [])
        
        if not active_conflicts:
            return {
                'conflicts_to_resolve': [],
                'conflicts_to_develop': [],
                'conflicts_to_introduce': []
            }
        
        # Create prompt to ask LLM about conflict planning
        prompt = f"""Dựa vào các mâu thuẫn đang hoạt động từ batch trước, hãy xác định:
1. Mâu thuẫn nào NÊN ĐƯỢC GIẢI QUYẾT trong batch {batch_num} này (5 chương tiếp theo)
2. Mâu thuẫn nào NÊN TIẾP TỤC PHÁT TRIỂN (chưa giải quyết)
3. Gợi ý về mâu thuẫn mới có thể xuất hiện

**MÂU THUẪN ĐANG HOẠT ĐỘNG:**
{self._format_conflicts_detailed(active_conflicts)}

**NGUYÊN TẮC XẾP LOẠI:**
- immediate (1 chapter): BẮT BUỘC giải quyết ngay
- batch (5 chapters): NÊN giải quyết trong batch này
- short_term (10 chapters): CÓ THỂ giải quyết hoặc tiếp tục phát triển
- medium_term, long_term, epic: TIẾP TỤC PHÁT TRIỂN, chưa giải quyết

**YÊU CẦU OUTPUT (JSON):**

```json
{{
  "conflicts_to_resolve": [
    {{
      "conflict_id": "id của conflict cần giải quyết",
      "expected_resolution_chapter": <số chương dự kiến giải quyết trong batch>,
      "resolution_approach": "cách tiếp cận giải quyết"
    }}
  ],
  "conflicts_to_develop": [
    {{
      "conflict_id": "id của conflict tiếp tục phát triển",
      "development_direction": "hướng phát triển"
    }}
  ],
  "conflicts_to_introduce": [
    {{
      "description": "mô tả mâu thuẫn mới gợi ý",
      "timeline": "batch/short_term/medium_term",
      "reason": "lý do cần thiết lập mâu thuẫn này"
    }}
  ]
}}
```

Hãy phân tích và trả về JSON."""
        
        result = self.llm_client.call(
            prompt=prompt,
            task_name="conflict_analysis",
            system_message="Bạn là chuyên gia phân tích cốt truyện và xung đột trong văn học.",
            batch_id=batch_num
        )
        
        try:
            conflict_plan = parse_json_from_response(result['response'])
            return conflict_plan
        except Exception as e:
            self.logger.warning(f"Failed to parse conflict analysis: {str(e)}")
            return {
                'conflicts_to_resolve': [],
                'conflicts_to_develop': [],
                'conflicts_to_introduce': []
            }
    
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
   - Nhân vật xuất hiện, cảnh giới và vai trò của họ. Yêu cầu tên nhân vật phong cách tu tiên Hán Việt, ví dụ: "Lăng Hàn", "Giang Phong"...
   - Mâu thuẫn được thiết lập hoặc phát triển
   - Bối cảnh, địa điểm
   - Các tình tiết không được lặp hoặc na ná nhau 
   - Mục đích và động cơ của nhân vật chính
   - Foreshadowing (nếu có) - các chi tiết nhỏ sẽ quan trọng sau này

2. Yêu cầu về cốt truyện:
   - Chương 1: Giới thiệu nhân vật chính, bối cảnh, và sự kiện khởi đầu
   - Chương 2-4: Phát triển xung đột, giới thiệu thêm nhân vật và thế lực
   - Chương 5: Cao trào nhỏ đầu tiên, mở ra hướng phát triển cho batch tiếp theo
   
3. Cài cắm tình tiết (Foreshadowing):
   - QUAN TRỌNG: Foreshadowing chỉ được cài cắm trong phạm vi TỐI ĐA 2 CHAPTERS tiếp theo
   - Ví dụ: Foreshadowing ở chương 1 sẽ xuất hiện/được giải mã ở chương 2 hoặc chương 3 (KHÔNG phải chương 4 hoặc 5)
   - Ví dụ: Foreshadowing ở chương 3 sẽ xuất hiện/được giải mã ở chương 4 hoặc chương 5
   - Mỗi chương nên có ít nhất 1-2 điểm foreshadowing nhỏ cho 1-2 chương sau đó
   - hành động bên trong events các batch sau không lặp với hành động của Foreshadowing
   

4. Định nghĩa các mâu thuẫn theo timeline:
   - Immediate (1 chapter): Cần giải quyết ngay
   - Batch (5 chapters): Giải quyết trong batch này
   - Short-term (10 chapters): Giải quyết trong 10 chương
   - Medium-term (30 chapters): Cốt truyện trung hạn
   - Long-term (100 chapters): Cốt truyện dài hạn
   - Epic (300 chapters): Mâu thuẫn xuyên suốt toàn bộ truyện

**LƯU Ý VỀ FORESHADOWING:**
- Chương 1: reveal_chapter chỉ có thể là 2 hoặc 3
- Chương 2: reveal_chapter chỉ có thể là 3 hoặc 4
- Chương 3: reveal_chapter chỉ có thể là 4 hoặc 5
- Chương 4: reveal_chapter chỉ có thể là 5 hoặc 6
- Chương 5: reveal_chapter chỉ có thể là 6 hoặc 7
***Lưu ý về tên MC/các nhân vật:**
- Không dùng tên các nhân vật lịch sử như: Trần Hưng Đạo, Lý Thường Kiệt, Võ Tánh, Nguyễn Huệ, v.v.
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
        {{
          "detail": "Chi tiết cài cắm (mô tả ngắn gọn)", 
          "reveal_chapter": <số chương sẽ xuất hiện/giải mã (PHẢI trong khoảng +1 đến +2 chương)>,
          "importance": 0.8
        }}
      ]
    }}
  ]
}}
```

Hãy tạo outline theo đúng định dạng JSON trên."""
        
        return prompt
    
    def _create_continuation_outline_prompt(self, batch_num: int, context: Dict[str, Any], 
                                           conflict_plan: Dict[str, Any]) -> str:
        """Create prompt for continuation outline generation."""
        start_chapter = (batch_num - 1) * self.chapters_per_batch + 1
        end_chapter = start_chapter + self.chapters_per_batch - 1
        
        prompt = f"""Hãy tạo outline cho 5 chương tiếp theo (Chương {start_chapter}-{end_chapter}) dựa trên ngữ cảnh sau:

**NGỮ CẢNH HIỆN TẠI:**

**Tóm tắt toàn bộ truyện:**
{context.get('super_summary', 'Chưa có')}

**Tóm tắt chương gần nhất:**
{context.get('recent_summary', 'Chưa có')}

**MÂU THUẪN CẦN XỬ LÝ:**

**Mâu thuẫn cần giải quyết trong batch này:**
{self._format_conflicts_to_resolve(conflict_plan.get('conflicts_to_resolve', []))}

**Mâu thuẫn tiếp tục phát triển:**
{self._format_conflicts_to_develop(conflict_plan.get('conflicts_to_develop', []))}

**Gợi ý mâu thuẫn mới:**
{self._format_conflicts_to_introduce(conflict_plan.get('conflicts_to_introduce', []))}

**Nhân vật liên quan:**
{self._format_characters(context.get('related_characters', []))}

**Entity liên quan:**
{self._format_entities(context.get('related_entities', []))}

**Sự kiện quan trọng:**
{self._format_events(context.get('related_events', []))}

**Gợi ý từ người dùng:**
{context.get('user_suggestions', 'Không có')}

**YÊU CẦU:**

1. Phải xử lý các mâu thuẫn theo kế hoạch đã phân tích ở trên
2. Sử dụng các nhân vật và entity đã có một cách hợp lý
3. Tạo sự liên kết chặt chẽ giữa các chương
4. Cài cắm foreshadowing cho các batch sau
5. Xác định rõ mục đích, động cơ của nhân vật chính trong mỗi chương

**LƯU Ý QUAN TRỌNG:**
- Mỗi chapter outline PHẢI có field "conflict_ids": danh sách ID các mâu thuẫn được đề cập/xử lý trong chương đó
- Mỗi chapter outline PHẢI có field "expected_conflict_updates": dictionary mapping conflict_id -> expected status sau chapter này
- Mỗi chapter outline PHẢI có field "entities": danh sách entities liên quan đến chương này
- Ví dụ: "expected_conflict_updates": {{"lh_01_02": "resolved", "lh_02_01": "developing"}}

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
        {{"event": "Mô tả sự kiện", "importance": 0.9, "related_entities": ["entity1", "entity2"]}}
      ],
      "characters": [
        {{
          "name": "Tên nhân vật",
          "role": "Vai trò trong chương này",
          "motivation": "Mục đích, động cơ"
        }}
      ],
      "entities": [
        {{
          "name": "Tên entity",
          "category": "characters/items/locations/techniques/...",
          "relevance": "Tại sao entity này quan trọng trong chương"
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
      "conflict_ids": ["lh_01_01", "lh_02_03"],
      "expected_conflict_updates": {{
        "lh_01_01": "developing",
        "lh_02_03": "resolved"
      }},
      "settings": ["Địa điểm"],
      "foreshadowing": [
        {{"detail": "Chi tiết cài cắm", "reveal_chapter": null, "importance": 0.8}}
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

        formatted = []
        for e in entities[:20]:
            # Handle description as array or string
            desc = e.get('description', '')
            if isinstance(desc, list):
                desc_text = "; ".join(desc) if desc else ""
            else:
                desc_text = desc

            formatted.append(f"- {e.get('name', 'Unknown')} ({e.get('category', e.get('type', 'unknown'))}): {desc_text[:100]}")

        return "\n".join(formatted)
    
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
        return "\n".join([f"- [{c.get('timeline', 'unknown')}] {c.get('description', '')} (ID: {c.get('id', 'N/A')})" 
                         for c in conflicts])
    
    def _format_conflicts_detailed(self, conflicts: List[Dict]) -> str:
        """Format conflicts with detailed information."""
        if not conflicts:
            return "Chưa có"
        result = []
        for c in conflicts:
            text = f"- ID: {c.get('id', 'N/A')}\n"
            text += f"  Mô tả: {c.get('description', '')}\n"
            text += f"  Timeline: {c.get('timeline', 'unknown')}\n"
            text += f"  Nhân vật: {', '.join(c.get('characters_involved', []))}\n"
            text += f"  Entity: {', '.join(c.get('entities_involved', []))}"
            result.append(text)
        return "\n\n".join(result)
    
    def _format_conflicts_to_resolve(self, conflicts: List[Dict]) -> str:
        """Format conflicts to resolve."""
        if not conflicts:
            return "Không có"
        result = []
        for c in conflicts:
            text = f"- Conflict ID: {c.get('conflict_id')}\n"
            text += f"  Dự kiến giải quyết ở chương: {c.get('expected_resolution_chapter', 'N/A')}\n"
            text += f"  Cách tiếp cận: {c.get('resolution_approach', '')}"
            result.append(text)
        return "\n\n".join(result)
    
    def _format_conflicts_to_develop(self, conflicts: List[Dict]) -> str:
        """Format conflicts to develop."""
        if not conflicts:
            return "Không có"
        result = []
        for c in conflicts:
            text = f"- Conflict ID: {c.get('conflict_id')}\n"
            text += f"  Hướng phát triển: {c.get('development_direction', '')}"
            result.append(text)
        return "\n\n".join(result)
    
    def _format_conflicts_to_introduce(self, conflicts: List[Dict]) -> str:
        """Format new conflicts to introduce."""
        if not conflicts:
            return "Không có"
        result = []
        for c in conflicts:
            text = f"- Mô tả: {c.get('description', '')}\n"
            text += f"  Timeline: {c.get('timeline', 'unknown')}\n"
            text += f"  Lý do: {c.get('reason', '')}"
            result.append(text)
        return "\n\n".join(result)
    
    def _parse_outline_response(self, response: str, batch_num: int) -> List[Dict[str, Any]]:
        """Parse LLM response to extract outline."""
        try:
            outline_data = parse_json_from_response(response)
            # Handle both direct list and object with 'chapters' key
            if isinstance(outline_data, list):
                return outline_data
            return outline_data.get('chapters', [])
        except Exception as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            self.logger.error(f"Response preview: {response[:500]}")
            raise ValueError("Could not parse outline from LLM response")
    
    def _save_outline(self, outlines: List[Dict[str, Any]], batch_num: int):
        """Save outline to file."""
        file_path = os.path.join(self.paths['outlines_dir'], f'batch_{batch_num}_outline.json')
        save_json({'batch': batch_num, 'chapters': outlines}, file_path)
        self.logger.info(f"Saved outline for batch {batch_num} to {file_path}")
    
    def _load_outline(self, batch_num: int) -> List[Dict[str, Any]]:
        """Load outline from file."""
        file_path = os.path.join(self.paths['outlines_dir'], f'batch_{batch_num}_outline.json')
        data = load_json(file_path)
        return data.get('chapters', [])
