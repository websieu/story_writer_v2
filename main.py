"""
Main orchestrator for story generation system
"""
import os
import sys
from typing import Dict, Any, List, Optional

from src.utils import (load_config, get_project_paths, ensure_project_directories, 
                       Logger, CostTracker)
from src.checkpoint import CheckpointManager
from src.llm_client import LLMClient
from src.motif_loader import MotifLoader
from src.outline_generator import OutlineGenerator
from src.entity_manager import EntityManager
from src.chapter_writer import ChapterWriter
from src.post_processor import PostChapterProcessor


class StoryGenerator:
    """Main orchestrator for the story generation system."""
    
    def __init__(self, config_path: str = "config/config.yaml", project_id: str = "story_001"):
        """
        Initialize the story generator.
        
        Args:
            config_path: Path to configuration file
            project_id: Unique project identifier (all data stored in projects/{project_id}/)
        """
        # Load configuration
        self.config = load_config(config_path)
        self.project_id = project_id
        
        # Ensure project directories exist
        ensure_project_directories(project_id, self.config)
        
        # Get project-specific paths
        self.paths = get_project_paths(project_id, self.config)
        
        # Initialize core components
        self.logger = Logger("StoryGenerator", project_id, self.config)
        self.cost_tracker = CostTracker(self.config)
        self.checkpoint = CheckpointManager(
            self.paths['checkpoints_dir'],
            project_id
        )
        
        # Initialize LLM client
        self.llm_client = LLMClient(self.config, self.logger, self.cost_tracker)
        
        # Initialize modules
        self.motif_loader = MotifLoader(
            self.config['paths']['motif_file'],
            self.logger
        )
        self.outline_generator = OutlineGenerator(
            self.llm_client,
            self.checkpoint,
            self.logger,
            self.config,
            self.paths
        )
        self.entity_manager = EntityManager(
            self.llm_client,
            self.checkpoint,
            self.logger,
            self.config,
            self.paths
        )
        self.post_processor = PostChapterProcessor(
            self.llm_client,
            self.checkpoint,
            self.logger,
            self.config,
            self.paths
        )
        self.chapter_writer = ChapterWriter(
            self.llm_client,
            self.checkpoint,
            self.logger,
            self.config,
            self.entity_manager,
            self.paths,
            self.post_processor
        )
        
        # Inject dependencies into outline_generator
        self.outline_generator.entity_manager = self.entity_manager
        self.outline_generator.post_processor = self.post_processor
        
        self.logger.info(f"StoryGenerator initialized for project: {project_id}")
        self.logger.info(f"Project root: {self.paths['project_root']}")
    
    def generate_story(self, num_batches: int = 1, motif_id: Optional[str] = None,
                       genre: Optional[str] = None):
        """
        Generate a complete story.
        
        Args:
            num_batches: Number of 5-chapter batches to generate
            motif_id: Specific motif ID to use (optional)
            genre: Genre filter for random motif selection (optional)
        """
        self.logger.info(f"Starting story generation: {num_batches} batches")
        
        # Step 1: Load motif
        if motif_id:
            motif = self.motif_loader.get_motif_by_id(motif_id)
        else:
            motif = self.motif_loader.get_random_motif(genre)
        
        if not motif:
            raise ValueError("No motif found")
        
        self.checkpoint.set_metadata('motif', motif)
        self.logger.info(f"Using motif: {motif.get('title')}")
        
        # Generate batches
        for batch_num in range(1, num_batches + 1):
            self.generate_batch(batch_num, motif)
        
        # Save final cost summary
        self._save_final_summary()
        
        self.logger.info("Story generation completed!")
    
    def generate_batch(self, batch_num: int, motif: Dict[str, Any], 
                       user_suggestions: Optional[str] = None):
        """
        Generate one batch of 5 chapters.
        
        Args:
            batch_num: Batch number (1-indexed)
            motif: Story motif
            user_suggestions: Optional user input for this batch
        """
        self.logger.info(f"=== Generating Batch {batch_num} ===")
        
        # Step 2: Generate outline
        if batch_num == 1:
            outlines = self.outline_generator.generate_initial_outline(motif, batch_num)
        else:
            context = self._prepare_batch_context(batch_num, user_suggestions)
            outlines = self.outline_generator.generate_continuation_outline(batch_num, context)
        
        # Step 3-4: Extract entities from outlines
        self.entity_manager.extract_entities_from_outlines(outlines, batch_num)
        
        # Step 5: Write each chapter
        for i, chapter_outline in enumerate(outlines):
            chapter_num = chapter_outline.get('chapter_number')
            # Get next chapter outline if exists
            next_chapter_outline = outlines[i + 1] if i + 1 < len(outlines) else None
            self._generate_chapter(chapter_num, chapter_outline, motif, next_chapter_outline)
        
        self.logger.info(f"=== Batch {batch_num} completed ===")
    
    def _generate_chapter(self, chapter_num: int, chapter_outline: Dict[str, Any],
                         motif: Dict[str, Any], next_chapter_outline: Optional[Dict[str, Any]] = None):
        """Generate a single chapter with all processing."""
        self.logger.info(f"--- Generating Chapter {chapter_num}: {chapter_outline.get('title')} ---")
        
        # Prepare context for chapter writing
        context = self._prepare_chapter_context(chapter_num, chapter_outline, motif, next_chapter_outline)
        
        # Write chapter
        chapter_content = self.chapter_writer.write_chapter(chapter_outline, context)
        
        # Post-processing
        self.logger.info(f"Post-processing chapter {chapter_num}")
        
        # Extract new entities from chapter
        self.entity_manager.extract_entities_from_chapter(chapter_content, chapter_num)
        
        # Extract events, conflicts, summaries
        post_data = self.post_processor.process_chapter(chapter_content, chapter_num)
        
        # Update checkpoint progress
        self.checkpoint.update_progress(
            batch=(chapter_num - 1) // 5 + 1,
            chapter=chapter_num
        )
        
        self.logger.info(f"--- Chapter {chapter_num} completed ---")
    
    def _prepare_chapter_context(self, chapter_num: int, chapter_outline: Dict[str, Any],
                                 motif: Dict[str, Any], next_chapter_outline: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Prepare context for chapter writing."""
        # Get relevant entities
        related_entities = self.entity_manager.get_relevant_entities(chapter_outline)
        
        # Get related characters
        character_names = [c.get('name') for c in chapter_outline.get('characters', [])]
        related_characters = [
            e for e in self.entity_manager.entities.get('characters', [])
            if e.get('name') in character_names
        ]
        
        # Get related events
        related_events = self._get_relevant_events(chapter_outline)
        
        # Get recent summaries
        recent_summaries = self.post_processor.get_recent_summaries(count=2)
        
        # Get super summary
        super_summary = self.checkpoint.get_metadata('super_summary', '')
        
        # Get previous chapter ending
        previous_chapter_end = ""
        if chapter_num > 1:
            previous_chapter_end = self.chapter_writer.get_chapter_end(chapter_num - 1)
        
        return {
            'motif': motif,
            'related_entities': related_entities,
            'related_characters': related_characters,
            'related_events': related_events,
            'recent_summaries': recent_summaries,
            'super_summary': super_summary,
            'previous_chapter_end': previous_chapter_end,
            'next_chapter_outline': next_chapter_outline  # Add next chapter outline for context
        }
    
    def _prepare_batch_context(self, batch_num: int, user_suggestions: Optional[str] = None) -> Dict[str, Any]:
        """Prepare context for generating continuation outline."""
        # Get super summary
        super_summary = self.checkpoint.get_metadata('super_summary', '')
        
        # Get most recent chapter summary
        recent_summary = self.post_processor.get_recent_summaries(count=1)
        recent_summary = recent_summary[0] if recent_summary else ''
        
        # Get active conflicts from previous batch
        active_conflicts = self.post_processor.get_unresolved_conflicts()
        
        # From active conflicts, find related characters and entities
        related_characters = self._get_characters_from_conflicts(active_conflicts)
        related_entities = self._get_entities_from_conflicts(active_conflicts)
        
        # From related characters/entities, find related events
        related_events = self._get_events_from_characters_entities(related_characters, related_entities)
        
        return {
            'super_summary': super_summary,
            'recent_summary': recent_summary,
            'active_conflicts': active_conflicts,
            'related_characters': related_characters,
            'related_entities': related_entities,
            'related_events': related_events,
            'user_suggestions': user_suggestions or ''
        }
    
    def _get_relevant_events(self, chapter_outline: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get events relevant to chapter."""
        # Get all events, sorted by importance
        all_events = sorted(
            self.post_processor.events,
            key=lambda x: x.get('importance', 0),
            reverse=True
        )

        # Filter by characters involved
        character_names = [c.get('name') for c in chapter_outline.get('characters', [])]
        # BUG FIX: Use case-insensitive matching
        character_names_lower = [name.lower() for name in character_names if name]
        relevant = []

        for event in all_events:
            characters_involved = event.get('characters_involved', [])
            characters_involved_lower = [char.lower() for char in characters_involved if char]

            # BUG FIX: Case-insensitive matching
            if any(char_lower in characters_involved_lower for char_lower in character_names_lower):
                relevant.append(event)

        return relevant[:10]  # Top 10 relevant events
    
    def _get_top_characters(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Get top characters by importance/frequency."""
        # For simplicity, return all main characters
        # Could be enhanced with frequency tracking
        return self.entity_manager.entities.get('characters', [])[:limit]
    
    def _get_top_entities(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top entities across all categories."""
        all_entities = []
        for category, entities in self.entity_manager.entities.items():
            for entity in entities:
                all_entities.append({**entity, 'category': category})
        
        # Could be enhanced with usage tracking
        return all_entities[:limit]
    
    def _get_top_events(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Get top events by importance."""
        sorted_events = sorted(
            self.post_processor.events,
            key=lambda x: x.get('importance', 0),
            reverse=True
        )
        return sorted_events[:limit]
    
    def _select_conflicts_for_batch(self, batch_num: int, 
                                    all_conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Select conflicts that should be addressed in this batch.
        
        Prioritize based on timeline and when they were introduced.
        """
        selected = []
        
        # Always include immediate conflicts
        immediate = [c for c in all_conflicts if c.get('timeline') == 'immediate']
        selected.extend(immediate)
        
        # Include batch-level conflicts
        batch_conflicts = [c for c in all_conflicts if c.get('timeline') == 'batch']
        selected.extend(batch_conflicts)
        
        # Include some short-term conflicts
        short_term = [c for c in all_conflicts if c.get('timeline') == 'short_term']
        selected.extend(short_term[:2])
        
        # Include awareness of medium/long-term conflicts
        medium_term = [c for c in all_conflicts if c.get('timeline') in ['medium_term', 'long_term']]
        selected.extend(medium_term[:2])
        
        return selected
    
    def _get_characters_from_conflicts(self, conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get characters related to conflicts."""
        character_names = set()
        for conflict in conflicts:
            chars = conflict.get('characters_involved', [])
            character_names.update(chars)
        
        # Get full character details
        characters = []
        for char_name in character_names:
            char = self.entity_manager.get_entity_by_name(char_name)
            if char:
                characters.append(char)
        
        return characters
    
    def _get_entities_from_conflicts(self, conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get entities related to conflicts."""
        entity_names = set()
        for conflict in conflicts:
            entities = conflict.get('entities_involved', [])
            entity_names.update(entities)
        
        # Get full entity details
        entities = []
        for entity_name in entity_names:
            entity = self.entity_manager.get_entity_by_name(entity_name)
            if entity:
                entities.append(entity)
        
        return entities
    
    def _get_events_from_characters_entities(self, characters: List[Dict[str, Any]], 
                                            entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get events related to characters and entities."""
        character_names = {c.get('name') for c in characters}
        entity_names = {e.get('name') for e in entities}
        
        related_events = []
        for event in self.post_processor.events:
            # Check if event involves any of the characters
            event_chars = set(event.get('characters_involved', []))
            # Check if event involves any of the entities
            event_entities = set(event.get('entities_involved', []))
            
            if event_chars.intersection(character_names) or event_entities.intersection(entity_names):
                related_events.append(event)
        
        # Sort by importance and return top events
        related_events.sort(key=lambda x: x.get('importance', 0), reverse=True)
        return related_events[:20]
    
    def _save_final_summary(self):
        """Save final cost and progress summary."""
        # Save cost summary
        cost_file = os.path.join(self.paths['outputs_dir'], 'cost_summary.json')
        self.cost_tracker.save_summary(cost_file)
        
        # Log final stats
        summary = self.cost_tracker.get_summary()
        self.logger.info(f"Total cost: ${summary['total_cost']:.2f}")
        self.logger.info(f"Total tokens: {summary['total_tokens']['total']:,}")
        self.logger.info(f"Total API calls: {summary['total_calls']}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate a story using AI")
    parser.add_argument('--project-id', '--story-id', dest='project_id', 
                       default='story_001', help='Project identifier (all data stored in projects/{project_id}/)')
    parser.add_argument('--batches', type=int, default=1, help='Number of batches to generate')
    parser.add_argument('--motif-id', help='Specific motif ID to use')
    parser.add_argument('--genre', help='Genre filter for motif selection')
    parser.add_argument('--config', default='config/config.yaml', help='Config file path')
    
    args = parser.parse_args()
    
    try:
        generator = StoryGenerator(
            config_path=args.config,
            project_id=args.project_id
        )
        
        generator.generate_story(
            num_batches=args.batches,
            motif_id=args.motif_id,
            genre=args.genre
        )
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
