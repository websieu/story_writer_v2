"""
Post-chapter processing: Extract events, conflicts, summaries, etc.
"""
import os
from typing import Dict, Any, List, Optional
from src.utils import save_json, load_json, parse_json_from_response


class PostChapterProcessor:
    """Handle all post-chapter processing tasks."""
    
    def __init__(self, llm_client, checkpoint_manager, logger, config, paths):
        self.llm_client = llm_client
        self.checkpoint = checkpoint_manager
        self.logger = logger
        self.config = config
        self.paths = paths
        self.max_chars = config.get('story', {}).get('max_chars_for_llm', 30000)
        self.events_file = os.path.join(paths['events_dir'], 'events.json')
        self.conflicts_file = os.path.join(paths['conflicts_dir'], 'conflicts.json')
        self.summaries_file = os.path.join(paths['summaries_dir'], 'summaries.json')
        
        # Load existing data
        self.events = self._load_events()
        self.conflicts = self._load_conflicts()
        self.summaries = self._load_summaries()
    
    def process_chapter(self, chapter_content: str, chapter_num: int) -> Dict[str, Any]:
        """
        Process a chapter after it's written.
        
        Returns dictionary with extracted data.
        """
        self.logger.info(f"Post-processing chapter {chapter_num}")
        
        # Extract events
        events = self.extract_events(chapter_content, chapter_num)
        
        # Extract conflicts
        conflicts = self.extract_conflicts(chapter_content, chapter_num)
        
        # Generate summary
        summary = self.generate_summary(chapter_content, chapter_num)
        
        # Update super summary
        super_summary = self.update_super_summary(chapter_num)
        
        return {
            'events': events,
            'conflicts': conflicts,
            'summary': summary,
            'super_summary': super_summary
        }
    
    def extract_events(self, chapter_content: str, chapter_num: int) -> List[Dict[str, Any]]:
        """Extract important events from chapter."""
        step_name = f"event_extraction_{chapter_num}"
        
        if self.checkpoint.is_step_completed(step_name, chapter=chapter_num):
            self.logger.info(f"Events for chapter {chapter_num} already extracted")
            return self._get_chapter_events(chapter_num)
        
        self.logger.info(f"Extracting events from chapter {chapter_num}")
        
        # Truncate content if needed
        truncated = chapter_content[:self.max_chars] + "..." if len(chapter_content) > self.max_chars else chapter_content
        
        prompt = f"""Hãy trích xuất các sự kiện QUAN TRỌNG từ chương {chapter_num}. Chỉ trích xuất những sự kiện 
        ảnh hưởng đến mạch truyện, không trích xuất những chi tiết nhỏ không quan trọng.

**NỘI DUNG CHƯƠNG:**
{truncated}

**YÊU CẦU:**
- Chỉ trích xuất sự kiện quan trọng (3-10 sự kiện)
- Mỗi sự kiện cần có mức độ quan trọng từ 0-1
- Sự kiện nào ảnh hưởng lớn đến cốt truyện thì importance cao hơn

**ĐỊNH DẠNG OUTPUT (JSON):**

```json
{{
  "chapter": {chapter_num},
  "events": [
    {{
      "description": "Mô tả sự kiện ngắn gọn",
      "importance": 0.9,
      "characters_involved": ["Tên nhân vật 1", "Tên nhân vật 2"],
      "entities_involved": ["Entity 1", "Entity 2"],
      "location": "Địa điểm xảy ra",
      "consequences": "Hậu quả/ảnh hưởng của sự kiện"
    }}
  ]
}}
```

Hãy trích xuất theo định dạng JSON trên."""
        
        result = self.llm_client.call(
            prompt=prompt,
            task_name="event_extraction",
            system_message="Bạn là chuyên gia phân tích cốt truyện, chỉ trích xuất những sự kiện thực sự quan trọng.",
            chapter_id=chapter_num
        )
        
        # Parse events
        events = self._parse_events_response(result['response'], chapter_num)
        
        # Save events
        self.events.extend(events)
        self._save_events()
        
        # Mark completed
        self.checkpoint.mark_step_completed(step_name, chapter=chapter_num)
        
        return events
    
    def extract_conflicts(self, chapter_content: str, chapter_num: int) -> List[Dict[str, Any]]:
        """Extract new conflicts from chapter."""
        step_name = f"conflict_extraction_{chapter_num}"
        
        if self.checkpoint.is_step_completed(step_name, chapter=chapter_num):
            self.logger.info(f"Conflicts for chapter {chapter_num} already extracted")
            return self._get_chapter_conflicts(chapter_num)
        
        self.logger.info(f"Extracting conflicts from chapter {chapter_num}")
        
        # Truncate content if needed
        truncated = chapter_content[:self.max_chars] + "..." if len(chapter_content) > self.max_chars else chapter_content
        
        # Get existing conflicts for reference
        unresolved = self.get_unresolved_conflicts()
        
        prompt = f"""Hãy trích xuất các mâu thuẫn từ chương {chapter_num}.

**NỘI DUNG CHƯƠNG:**
{truncated}

**MÂU THUẪN ĐÃ CÓ:**
{self._format_conflicts_list(unresolved)}

**YÊU CẦU:**
1. Xác định các mâu thuẫn MỚI phát sinh trong chương này
2. Cập nhật trạng thái các mâu thuẫn cũ (nếu có tiến triển hoặc được giải quyết)
3. Phân loại timeline cho mâu thuẫn:
   - immediate: Cần giải quyết ngay (1 chapter)
   - batch: Trong 5 chapters
   - short_term: 10 chapters
   - medium_term: 30 chapters
   - long_term: 100 chapters
   - epic: 300 chapters

**ĐỊNH DẠNG OUTPUT (JSON):**

```json
{{
  "chapter": {chapter_num},
  "new_conflicts": [
    {{
      "id": "conflict_unique_id",
      "description": "Mô tả mâu thuẫn",
      "type": "internal/external/philosophical",
      "timeline": "batch",
      "characters_involved": ["Nhân vật 1", "Nhân vật 2"],
      "entities_involved": ["Entity 1", "Entity 2"],
      "introduced_chapter": {chapter_num},
      "status": "active"
    }}
  ],
  "updated_conflicts": [
    {{
      "id": "conflict_id_existing",
      "status": "resolved/developing",
      "resolution_chapter": {chapter_num}
    }}
  ]
}}
```

Hãy trích xuất theo định dạng JSON trên."""
        
        result = self.llm_client.call(
            prompt=prompt,
            task_name="conflict_extraction",
            system_message="Bạn là chuyên gia phân tích mâu thuẫn trong văn học.",
            chapter_id=chapter_num
        )
        
        # Parse conflicts
        new_conflicts, updated = self._parse_conflicts_response(result['response'], chapter_num)
        
        # Update conflicts
        self._update_conflicts(new_conflicts, updated, chapter_num)
        
        # Mark completed
        self.checkpoint.mark_step_completed(step_name, chapter=chapter_num)
        
        return new_conflicts
    
    def generate_summary(self, chapter_content: str, chapter_num: int) -> str:
        """Generate concise summary of chapter."""
        step_name = f"summary_generation_{chapter_num}"
        
        if self.checkpoint.is_step_completed(step_name, chapter=chapter_num):
            self.logger.info(f"Summary for chapter {chapter_num} already generated")
            return self._get_chapter_summary(chapter_num)
        
        self.logger.info(f"Generating summary for chapter {chapter_num}")
        
        # Truncate content if needed
        truncated = chapter_content[:self.max_chars] + "..." if len(chapter_content) > self.max_chars else chapter_content
        
        prompt = f"""Hãy tóm tắt ngắn gọn nội dung chương {chapter_num}.

**NỘI DUNG CHƯƠNG:**
{truncated}

**YÊU CẦU:**
- Tóm tắt 400-500 từ
- Bao gồm các sự kiện chính
- Nhấn mạnh điểm quan trọng
- Ghi rõ cảnh giới nhân vật.
- Không bỏ sót thông tin then chốt

Hãy viết tóm tắt."""
        
        result = self.llm_client.call(
            prompt=prompt,
            task_name="summary_generation",
            system_message="Bạn là chuyên gia tóm tắt nội dung.",
            chapter_id=chapter_num
        )
        
        summary = result['response'].strip()
        
        # Save summary
        self.summaries.append({
            'chapter': chapter_num,
            'summary': summary
        })
        self._save_summaries()
        
        # Mark completed
        self.checkpoint.mark_step_completed(step_name, chapter=chapter_num)
        
        return summary
    
    def update_super_summary(self, chapter_num: int) -> str:
        """Update super summary of entire story so far."""
        step_name = f"super_summary_update_{chapter_num}"
        
        if self.checkpoint.is_step_completed(step_name, chapter=chapter_num):
            self.logger.info(f"Super summary already updated for chapter {chapter_num}")
            metadata = self.checkpoint.get_step_metadata(step_name, chapter=chapter_num)
            return metadata.get('super_summary', '') if metadata else ''
        
        self.logger.info(f"Updating super summary up to chapter {chapter_num}")
        
        # Get all summaries up to this chapter
        recent_summaries = [s['summary'] for s in self.summaries if s['chapter'] <= chapter_num]
        
        if not recent_summaries:
            return ""
        
        # Get previous super summary
        prev_super = self.checkpoint.get_metadata('super_summary', '')
        
        prompt = f"""Hãy tạo tóm tắt SIÊU NGẮN GỌN cho toàn bộ truyện từ đầu đến chương {chapter_num}.

**TÓM TẮT CŨ (nếu có):**
{prev_super if prev_super else "Chưa có"}

**TÓM TẮT CÁC CHƯƠNG GẦN ĐÂY:**
{self._format_recent_summaries(recent_summaries[-5:])}

**YÊU CẦU:**
- Tóm tắt CỰC NGẮN: 400-500 từ cho toàn bộ truyện
- Chỉ giữ lại thông tin cốt lõi nhất
- Tập trung vào mạch chính, bỏ chi tiết phụ
- Ghi rõ cảnh giới nhân vật.
- Cập nhật với thông tin mới từ các chương gần đây

Hãy viết tóm tắt siêu ngắn gọn."""
        
        result = self.llm_client.call(
            prompt=prompt,
            task_name="summary_generation",
            system_message="Bạn là chuyên gia tóm tắt, có khả năng nắm bắt cốt lõi.",
            chapter_id=chapter_num
        )
        
        super_summary = result['response'].strip()
        
        # Save to metadata
        self.checkpoint.set_metadata('super_summary', super_summary)
        
        # Mark completed
        self.checkpoint.mark_step_completed(
            step_name, 
            chapter=chapter_num,
            metadata={'super_summary': super_summary}
        )
        
        return super_summary
    
    def get_recent_summaries(self, count: int = 2) -> List[str]:
        """Get N most recent chapter summaries."""
        if not self.summaries:
            return []
        sorted_summaries = sorted(self.summaries, key=lambda x: x['chapter'], reverse=True)
        return [s['summary'] for s in sorted_summaries[:count]]
    
    def get_unresolved_conflicts(self) -> List[Dict[str, Any]]:
        """Get all unresolved conflicts."""
        return [c for c in self.conflicts if c.get('status') == 'active']
    
    def get_conflicts_by_timeline(self, timeline: str) -> List[Dict[str, Any]]:
        """Get unresolved conflicts by timeline."""
        return [c for c in self.conflicts 
                if c.get('status') == 'active' and c.get('timeline') == timeline]
    
    def get_events_by_entities(self, entity_names: List[str], max_events: int = 10) -> List[Dict[str, Any]]:
        """
        Get events related to specific entities.
        
        Args:
            entity_names: List of entity names to search for
            max_events: Maximum number of events to return (most important first)
            
        Returns:
            List of events involving the specified entities
        """
        if not entity_names:
            return []
        
        # Normalize entity names for matching
        entity_names_lower = [name.lower() for name in entity_names]
        
        related_events = []
        for event in self.events:
            # Check if any entity is involved
            involved = False
            
            # Check characters_involved
            chars = event.get('characters_involved', [])
            if any(char.lower() in entity_names_lower for char in chars):
                involved = True
            
            # Check entities_involved
            entities = event.get('entities_involved', [])
            if any(entity.lower() in entity_names_lower for entity in entities):
                involved = True
            
            if involved:
                related_events.append(event)
        
        # Sort by importance (descending) and limit
        related_events.sort(key=lambda x: x.get('importance', 0), reverse=True)
        return related_events[:max_events]
    
    def get_events_by_chapter_range(self, start_chapter: int, end_chapter: int) -> List[Dict[str, Any]]:
        """
        Get all events from a range of chapters.
        
        Args:
            start_chapter: Starting chapter number (inclusive)
            end_chapter: Ending chapter number (inclusive)
            
        Returns:
            List of events from the specified chapter range
        """
        return [e for e in self.events 
                if start_chapter <= e.get('chapter', 0) <= end_chapter]
    
    def _load_events(self) -> List[Dict[str, Any]]:
        """Load events from file."""
        if os.path.exists(self.events_file):
            return load_json(self.events_file)
        return []
    
    def _save_events(self):
        """Save events to file."""
        save_json(self.events, self.events_file)
    
    def _load_conflicts(self) -> List[Dict[str, Any]]:
        """Load conflicts from file."""
        if os.path.exists(self.conflicts_file):
            return load_json(self.conflicts_file)
        return []
    
    def _save_conflicts(self):
        """Save conflicts to file."""
        save_json(self.conflicts, self.conflicts_file)
    
    def _load_summaries(self) -> List[Dict[str, Any]]:
        """Load summaries from file."""
        if os.path.exists(self.summaries_file):
            return load_json(self.summaries_file)
        return []
    
    def _save_summaries(self):
        """Save summaries to file."""
        save_json(self.summaries, self.summaries_file)
    
    def _parse_events_response(self, response: str, chapter_num: int) -> List[Dict[str, Any]]:
        """Parse events from LLM response."""
        try:
            data = parse_json_from_response(response)
            # Handle both direct list and object with 'events' key
            if isinstance(data, list):
                events = data
            else:
                events = data.get('events', [])
            # Add chapter info to each event
            for event in events:
                event['chapter'] = chapter_num
            return events
        except Exception as e:
            self.logger.warning(f"Failed to parse events for chapter {chapter_num}: {str(e)}")
            self.logger.warning(f"Response preview: {response[:500]}")
            return []
    
    def _parse_conflicts_response(self, response: str, chapter_num: int):
        """Parse conflicts from LLM response."""
        try:
            data = parse_json_from_response(response)
            new_conflicts = data.get('new_conflicts', [])
            updated_conflicts = data.get('updated_conflicts', [])
            return new_conflicts, updated_conflicts
        except Exception as e:
            self.logger.warning(f"Failed to parse conflicts for chapter {chapter_num}")
            return [], []
    
    def _update_conflicts(self, new_conflicts: List[Dict], updated: List[Dict], chapter_num: int):
        """Update conflicts list."""
        # Add new conflicts
        for conflict in new_conflicts:
            if 'id' not in conflict:
                conflict['id'] = f"conflict_ch{chapter_num}_{len(self.conflicts)}"
            self.conflicts.append(conflict)
        
        # Update existing conflicts
        for update in updated:
            conflict_id = update.get('id')
            for i, conflict in enumerate(self.conflicts):
                if conflict.get('id') == conflict_id:
                    if 'status' in update:
                        self.conflicts[i]['status'] = update['status']
                    if 'resolution_chapter' in update:
                        self.conflicts[i]['resolution_chapter'] = update['resolution_chapter']
                    break
        
        self._save_conflicts()
    
    def _get_chapter_events(self, chapter_num: int) -> List[Dict[str, Any]]:
        """Get events for a specific chapter."""
        return [e for e in self.events if e.get('chapter') == chapter_num]
    
    def _get_chapter_conflicts(self, chapter_num: int) -> List[Dict[str, Any]]:
        """Get conflicts introduced in a specific chapter."""
        return [c for c in self.conflicts if c.get('introduced_chapter') == chapter_num]
    
    def _get_chapter_summary(self, chapter_num: int) -> str:
        """Get summary for a specific chapter."""
        for s in self.summaries:
            if s['chapter'] == chapter_num:
                return s['summary']
        return ""
    
    def _format_conflicts_list(self, conflicts: List[Dict]) -> str:
        """Format conflicts for prompt."""
        if not conflicts:
            return "Chưa có mâu thuẫn"
        return "\n".join([f"- [{c.get('timeline', 'unknown')}] {c.get('description', '')} (ID: {c.get('id', 'unknown')})" 
                         for c in conflicts])
    
    def _format_recent_summaries(self, summaries: List[str]) -> str:
        """Format recent summaries for prompt."""
        return "\n\n".join([f"Chương {i+1}: {s}" for i, s in enumerate(summaries)])
