"""
Step 5: Chapter content writer
"""
import os
from typing import Dict, Any, List, Optional
from src.prompts.generate_prompt import WRITING_SYSTEM_PROMPT
from src.utils import save_text, load_text, save_json, load_json


class ChapterWriter:
    """Generate detailed chapter content from outlines."""
    
    def __init__(self, llm_client, checkpoint_manager, logger, config, entity_manager, paths):
        self.llm_client = llm_client
        self.checkpoint = checkpoint_manager
        self.logger = logger
        self.config = config
        self.paths = paths
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
        
        system_message = WRITING_SYSTEM_PROMPT
        # Call LLM with chapter_id
        result = self.llm_client.call(
            prompt=prompt,
            task_name="chapter_writing",
            system_message=system_message,
            max_tokens=8000,  # Allow longer output
            chapter_id=chapter_num
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
        
        # Prefer entities from outline, fallback to context
        outline_entities = chapter_outline.get('entities', [])
        if outline_entities:
            # Get full entity details filtered by current chapter number
            related_entities = self._get_entities_from_outline(outline_entities, chapter_num)
        else:
            # Filter context entities by chapter number if available
            related_entities = self._filter_entities_by_chapter(
                context.get('related_entities', []), 
                chapter_num
            )
        
        characters_section = self._format_characters(context.get('related_characters', []))
        events_section = self._format_events(context.get('related_events', []))
        entities_section = self._format_entities(related_entities)
        
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

"""
        
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
    
    def _get_entities_from_outline(self, outline_entities: List[Dict[str, Any]], chapter_num: int) -> List[Dict[str, Any]]:
        """
        Get full entity details from entity names in outline, filtered by chapter number.

        Args:
            outline_entities: List of entity references from the outline
            chapter_num: Current chapter number to filter entities

        Returns:
            List of entities that appear in this specific chapter
        """
        full_entities = []
        for outline_entity in outline_entities:
            entity_name = outline_entity.get('name', '')
            if entity_name:
                # Try to find full entity details from entity manager
                entity = self.entity_manager.get_entity_by_name(entity_name)
                if entity:
                    # Only include if entity appears in this chapter
                    if chapter_num in entity.get('appear_in_chapters', []):
                        full_entities.append(entity)
                else:
                    # If not found in entity manager, use the outline entity info as fallback
                    # Also check appear_in_chapters for outline entity
                    if chapter_num in outline_entity.get('appear_in_chapters', []):
                        full_entities.append(outline_entity)
        return full_entities
    
    def _filter_entities_by_chapter(self, entities: List[Dict[str, Any]], chapter_num: int) -> List[Dict[str, Any]]:
        """
        Filter entities to only include those that appear in the specified chapter.
        
        Args:
            entities: List of entities to filter
            chapter_num: Chapter number to filter by
            
        Returns:
            Filtered list of entities
        """
        filtered = []
        for entity in entities:
            appear_in = entity.get('appear_in_chapters', [])
            # If entity has no chapter info, include it (backward compatibility)
            # Otherwise, only include if it appears in this chapter
            if not appear_in or chapter_num in appear_in:
                filtered.append(entity)
        return filtered
    
    def _save_chapter(self, content: str, chapter_num: int, title: str):
        """Save chapter content to file."""
        # Save as text file
        text_file = os.path.join(self.paths['chapters_dir'], f'chapter_{chapter_num:03d}.txt')
        save_text(content, text_file)
        
        # Also save metadata
        metadata = {
            'chapter_number': chapter_num,
            'title': title,
            'word_count': len(content.split()),
            'char_count': len(content)
        }
        meta_file = os.path.join(self.paths['chapters_dir'], f'chapter_{chapter_num:03d}_meta.json')
        save_json(metadata, meta_file)
        
        self.logger.info(f"Saved chapter {chapter_num} to {text_file}")
    
    def _load_chapter(self, chapter_num: int) -> str:
        """Load chapter content from file."""
        text_file = os.path.join(self.paths['chapters_dir'], f'chapter_{chapter_num:03d}.txt')
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
