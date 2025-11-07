"""
Step 5: Chapter content writer
"""
import os
from typing import Dict, Any, List, Optional
from src.utils import save_text, load_text, save_json, load_json


class ChapterWriter:
    """Generate detailed chapter content from outlines."""
    
    def __init__(self, llm_client, checkpoint_manager, logger, config, entity_manager):
        self.llm_client = llm_client
        self.checkpoint = checkpoint_manager
        self.logger = logger
        self.config = config
        self.entity_manager = entity_manager
        self.target_words = config['story']['target_words_per_chapter']
        self.last_chapter_chars = config['story']['last_chapter_context_chars']
    
    def write_chapter(self, chapter_outline: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Write detailed chapter content.
        
        Args:
            chapter_outline: Outline for this chapter
            context: Dictionary containing:
                - motif: Original story motif
                - recent_summaries: List of last 2 chapter summaries
                - super_summary: Brief summary of entire story
                - previous_chapter_end: Last 1000 chars of previous chapter
                - related_characters: Relevant characters
                - related_events: Relevant events
                - related_entities: Relevant entities
                
        Returns:
            Chapter content text
        """
        chapter_num = chapter_outline.get('chapter_number', 0)
        step_name = f"chapter_writing_{chapter_num}"
        
        # Check checkpoint
        if self.checkpoint.is_step_completed(step_name, chapter=chapter_num):
            self.logger.info(f"Chapter {chapter_num} already written, loading from file")
            return self._load_chapter(chapter_num)
        
        self.logger.info(f"Writing chapter {chapter_num}: {chapter_outline.get('title')}")
        
        # Create writing prompt
        prompt = self._create_writing_prompt(chapter_outline, context)
        
        system_message = f"""Bạn là một tác giả truyện tu tiên tài năng, có khả năng viết những đoạn văn sinh động, 
        hấp dẫn với các mô tả chi tiết và đối thoại tự nhiên. Hãy viết chương truyện khoảng {self.target_words} từ."""
        
        # Call LLM
        result = self.llm_client.call(
            prompt=prompt,
            task_name="chapter_writing",
            system_message=system_message,
            max_tokens=8000  # Allow longer output
        )
        
        chapter_content = result['response']
        
        # Save chapter
        self._save_chapter(chapter_content, chapter_num, chapter_outline.get('title', ''))
        
        # Mark as completed
        self.checkpoint.mark_step_completed(
            step_name,
            chapter=chapter_num,
            metadata={
                'title': chapter_outline.get('title'),
                'word_count': len(chapter_content.split())
            }
        )
        
        return chapter_content
    
    def _create_writing_prompt(self, chapter_outline: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create detailed writing prompt."""
        chapter_num = chapter_outline.get('chapter_number', 0)
        
        # Build context sections
        motif_section = self._format_motif(context.get('motif', {}))
        summary_section = self._format_summaries(context.get('recent_summaries', []), context.get('super_summary', ''))
        previous_end_section = self._format_previous_end(context.get('previous_chapter_end', ''))
        characters_section = self._format_characters(context.get('related_characters', []))
        events_section = self._format_events(context.get('related_events', []))
        entities_section = self._format_entities(context.get('related_entities', []))
        
        prompt = f"""Hãy viết nội dung chi tiết cho chương {chapter_num} dựa trên outline và ngữ cảnh sau:

**OUTLINE CHƯƠNG {chapter_num}: {chapter_outline.get('title')}**

Tóm tắt: {chapter_outline.get('summary')}

Sự kiện chính:
{self._format_key_events(chapter_outline.get('key_events', []))}

Nhân vật trong chương:
{self._format_chapter_characters(chapter_outline.get('characters', []))}

Mâu thuẫn:
{self._format_conflicts(chapter_outline.get('conflicts', []))}

Địa điểm: {', '.join(chapter_outline.get('settings', []))}

---

**NGỮ CẢNH:**

{motif_section}

{summary_section}

{previous_end_section}

{characters_section}

{events_section}

{entities_section}

---

**YÊU CẦU VIẾT:**

1. **Độ dài:** Khoảng {self.target_words} từ

2. **Cấu trúc:**
   - Mở đầu: Nối tiếp tự nhiên từ chương trước (nếu có)
   - Phát triển: Triển khai các sự kiện chính theo outline
   - Cao trào: Tạo điểm nhấn, kịch tính
   - Kết thúc: Để lại hồi hộp cho chương sau

3. **Nội dung:**
   - Mô tả chi tiết bối cảnh, hành động, cảm xúc
   - Đối thoại tự nhiên, phù hợp tính cách nhân vật
   - Thể hiện rõ mục đích, động cơ của nhân vật chính
   - Cài cắm các chi tiết foreshadowing theo outline
   - Sử dụng các entity đã cho một cách hợp lý

4. **Phong cách:**
   - Ngôn ngữ phong phú, không lặp từ
   - Nhịp độ phù hợp: chậm khi mô tả, nhanh khi hành động
   - Cân bằng giữa tường thuật, mô tả, và đối thoại

5. **Lưu ý:**
   - Giữ tính nhất quán với các chương trước
   - Phát triển nhân vật một cách tự nhiên
   - Không giải quyết mọi mâu thuẫn trong một chương

Hãy viết nội dung chương truyện hoàn chỉnh."""
        
        return prompt
    
    def _format_motif(self, motif: Dict[str, Any]) -> str:
        """Format motif information."""
        if not motif:
            return ""
        return f"""**Motif gốc:**
Tiêu đề: {motif.get('title', '')}
Mô tả: {motif.get('description', '')}
Chủ đề: {', '.join(motif.get('themes', []))}"""
    
    def _format_summaries(self, recent_summaries: List[str], super_summary: str) -> str:
        """Format summary information."""
        sections = []
        
        if super_summary:
            sections.append(f"**Tóm tắt toàn bộ:** {super_summary}")
        
        if recent_summaries:
            sections.append("**Các chương gần đây:**")
            for i, summary in enumerate(recent_summaries[-2:], 1):
                sections.append(f"{i}. {summary}")
        
        return "\n".join(sections) if sections else ""
    
    def _format_previous_end(self, previous_end: str) -> str:
        """Format previous chapter ending."""
        if not previous_end:
            return ""
        return f"""**Kết chương trước:**
{previous_end}"""
    
    def _format_characters(self, characters: List[Dict[str, Any]]) -> str:
        """Format character information."""
        if not characters:
            return ""
        
        char_list = []
        for char in characters[:10]:
            char_info = f"- **{char.get('name', 'Unknown')}**"
            if char.get('description'):
                char_info += f": {char.get('description', '')[:200]}"
            if char.get('cultivation_level'):
                char_info += f" | Tu vi: {char.get('cultivation_level')}"
            char_list.append(char_info)
        
        return "**Nhân vật liên quan:**\n" + "\n".join(char_list) if char_list else ""
    
    def _format_events(self, events: List[Dict[str, Any]]) -> str:
        """Format event information."""
        if not events:
            return ""
        
        event_list = [f"- {e.get('description', '')} (quan trọng: {e.get('importance', 0):.1f})" 
                     for e in events[:10]]
        
        return "**Sự kiện liên quan:**\n" + "\n".join(event_list) if event_list else ""
    
    def _format_entities(self, entities: List[Dict[str, Any]]) -> str:
        """Format entity information."""
        if not entities:
            return ""
        
        entity_list = []
        for e in entities[:15]:
            entity_info = f"- **{e.get('name', 'Unknown')}** ({e.get('category', e.get('type', 'unknown'))})"
            if e.get('description'):
                entity_info += f": {e.get('description', '')[:150]}"
            entity_list.append(entity_info)
        
        return "**Entity liên quan:**\n" + "\n".join(entity_list) if entity_list else ""
    
    def _format_key_events(self, events: List[Dict[str, Any]]) -> str:
        """Format key events from outline."""
        if not events:
            return "Không có"
        return "\n".join([f"- {e.get('event', '')} (quan trọng: {e.get('importance', 0):.1f})" 
                         for e in events])
    
    def _format_chapter_characters(self, characters: List[Dict[str, Any]]) -> str:
        """Format characters in chapter outline."""
        if not characters:
            return "Không có"
        char_list = []
        for c in characters:
            char_str = f"- {c.get('name', '')}"
            if c.get('role'):
                char_str += f": {c.get('role')}"
            if c.get('motivation'):
                char_str += f" | Động cơ: {c.get('motivation')}"
            char_list.append(char_str)
        return "\n".join(char_list)
    
    def _format_conflicts(self, conflicts: List[Dict[str, Any]]) -> str:
        """Format conflicts from outline."""
        if not conflicts:
            return "Không có"
        return "\n".join([f"- [{c.get('timeline', 'unknown')}] {c.get('description', '')} (trạng thái: {c.get('status', 'unknown')})" 
                         for c in conflicts])
    
    def _save_chapter(self, content: str, chapter_num: int, title: str):
        """Save chapter content to file."""
        output_dir = self.config['paths']['output_dir']
        
        # Save as text file
        text_file = os.path.join(output_dir, 'chapters', f'chapter_{chapter_num:03d}.txt')
        save_text(content, text_file)
        
        # Also save metadata
        metadata = {
            'chapter_number': chapter_num,
            'title': title,
            'word_count': len(content.split()),
            'char_count': len(content)
        }
        meta_file = os.path.join(output_dir, 'chapters', f'chapter_{chapter_num:03d}_meta.json')
        save_json(metadata, meta_file)
        
        self.logger.info(f"Saved chapter {chapter_num} to {text_file}")
    
    def _load_chapter(self, chapter_num: int) -> str:
        """Load chapter content from file."""
        output_dir = self.config['paths']['output_dir']
        text_file = os.path.join(output_dir, 'chapters', f'chapter_{chapter_num:03d}.txt')
        return load_text(text_file)
    
    def get_chapter_end(self, chapter_num: int, chars: int = None) -> str:
        """Get the last N characters of a chapter."""
        if chars is None:
            chars = self.last_chapter_chars
        
        try:
            content = self._load_chapter(chapter_num)
            return content[-chars:] if len(content) > chars else content
        except:
            return ""
