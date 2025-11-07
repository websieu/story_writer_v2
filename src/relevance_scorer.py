"""
Relevance scoring system for entities, events, and conflicts.
Enables intelligent selection for long-form stories (300+ chapters).
"""
from typing import Dict, Any, List, Set


class RelevanceScorer:
    """Calculate relevance scores for entities, events, and conflicts."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize scorer with configuration.
        
        Args:
            config: Configuration dictionary with scoring parameters
        """
        self.config = config
        
        # Get window configuration
        windows = config.get('story', {}).get('context_windows', {})
        self.window_immediate = windows.get('immediate', 5)
        self.window_recent = windows.get('recent', 20)
        self.window_medium = windows.get('medium', 50)
        self.window_historical = windows.get('historical', 100)
        
    def calculate_entity_relevance(self, entity: Dict[str, Any], current_chapter: int,
                                   chapter_outline: Dict[str, Any]) -> float:
        """
        Calculate relevance score (0-1) for an entity.
        
        Factors:
        - Recency (40%): How recently did the entity appear?
        - Frequency (20%): How often does it appear?
        - Outline match (30%): Is it mentioned in the chapter outline?
        - Importance (10%): Base importance score
        
        Args:
            entity: Entity dictionary
            current_chapter: Current chapter number
            chapter_outline: Outline for current chapter
            
        Returns:
            Relevance score between 0 and 1
        """
        score = 0.0
        
        # Factor 1: Recency (40%)
        appear_chapters = entity.get('appear_in_chapters', [])
        if appear_chapters:
            last_appearance = max(appear_chapters)
            chapter_distance = current_chapter - last_appearance
            
            # Decay function based on windows
            if chapter_distance == 0:
                recency_score = 1.0
            elif chapter_distance <= self.window_immediate:
                recency_score = 0.9
            elif chapter_distance <= self.window_recent:
                recency_score = 0.7
            elif chapter_distance <= self.window_medium:
                recency_score = 0.4
            elif chapter_distance <= self.window_historical:
                recency_score = 0.2
            else:
                recency_score = 0.05
            
            score += recency_score * 0.4
        
        # Factor 2: Frequency (20%)
        frequency = len(appear_chapters)
        max_frequency = min(current_chapter, 50)  # Cap at 50 for normalization
        if max_frequency > 0:
            frequency_score = min(frequency / max_frequency, 1.0)
            score += frequency_score * 0.2
        
        # Factor 3: Outline match (30%)
        entity_name = entity.get('name', '').lower()
        
        # Check entities in outline
        outline_entities = chapter_outline.get('entities', [])
        outline_entity_names = {e.get('name', '').lower() for e in outline_entities}
        
        # Check characters in outline
        outline_characters = chapter_outline.get('characters', [])
        outline_character_names = {c.get('name', '').lower() for c in outline_characters}
        
        # Check settings (for locations)
        outline_settings = chapter_outline.get('settings', [])
        outline_setting_names = {s.lower() for s in outline_settings}
        
        if (entity_name in outline_entity_names or 
            entity_name in outline_character_names or
            entity_name in outline_setting_names):
            score += 1.0 * 0.3
        
        # Factor 4: Importance (10%)
        importance = entity.get('importance', 0.5)
        score += importance * 0.1
        
        return min(score, 1.0)
    
    def calculate_event_relevance(self, event: Dict[str, Any], current_chapter: int,
                                  chapter_outline: Dict[str, Any]) -> float:
        """
        Calculate relevance score (0-1) for an event.
        
        Factors:
        - Recency (40%): How recent is the event?
        - Importance (30%): Event importance score
        - Character overlap (20%): Overlap with outline characters
        - Entity overlap (10%): Overlap with outline entities
        
        Args:
            event: Event dictionary
            current_chapter: Current chapter number
            chapter_outline: Outline for current chapter
            
        Returns:
            Relevance score between 0 and 1
        """
        score = 0.0
        
        # Factor 1: Recency (40%)
        event_chapter = event.get('chapter', 1)
        chapter_distance = current_chapter - event_chapter
        
        if chapter_distance <= self.window_immediate:
            recency_score = 1.0
        elif chapter_distance <= self.window_recent:
            recency_score = 0.8
        elif chapter_distance <= self.window_medium:
            recency_score = 0.5
        elif chapter_distance <= self.window_historical:
            recency_score = 0.2
        else:
            recency_score = 0.05
        
        score += recency_score * 0.4
        
        # Factor 2: Importance (30%)
        importance = event.get('importance', 0.5)
        score += importance * 0.3
        
        # Factor 3: Character overlap (20%)
        event_characters = set(event.get('characters_involved', []))
        outline_characters = set(c.get('name', '') for c in chapter_outline.get('characters', []))
        
        if event_characters and outline_characters:
            overlap_ratio = len(event_characters & outline_characters) / len(event_characters)
            score += overlap_ratio * 0.2
        
        # Factor 4: Entity overlap (10%)
        event_entities = set(event.get('entities_involved', []))
        outline_entities = set(e.get('name', '') for e in chapter_outline.get('entities', []))
        
        if event_entities and outline_entities:
            overlap_ratio = len(event_entities & outline_entities) / len(event_entities)
            score += overlap_ratio * 0.1
        
        return min(score, 1.0)
    
    def calculate_conflict_priority(self, conflict: Dict[str, Any], current_chapter: int) -> float:
        """
        Calculate priority score (0-1) for a conflict.
        
        Factors:
        - Timeline urgency (40%): How urgent based on timeline?
        - Staleness penalty (30%): How long since last mentioned?
        - Character involvement (30%): Are involved characters important?
        
        Args:
            conflict: Conflict dictionary
            current_chapter: Current chapter number
            
        Returns:
            Priority score between 0 and 1
        """
        score = 0.0
        
        # Factor 1: Timeline urgency (40%)
        timeline = conflict.get('timeline', 'medium_term')
        introduced_chapter = conflict.get('introduced_chapter', 1)
        chapters_elapsed = current_chapter - introduced_chapter
        
        # Timeline configurations: (base_score, expected_duration)
        timeline_configs = {
            'immediate': (1.0, 1),
            'batch': (0.9, 5),
            'short_term': (0.7, 10),
            'medium_term': (0.5, 30),
            'long_term': (0.3, 100),
            'epic': (0.2, 300)
        }
        
        base_score, expected_duration = timeline_configs.get(timeline, (0.5, 30))
        
        # Increase urgency if approaching expected resolution time
        if expected_duration > 0:
            progress = chapters_elapsed / expected_duration
            if progress >= 0.8:
                urgency_multiplier = 1.5  # Very urgent
            elif progress >= 0.5:
                urgency_multiplier = 1.2  # Moderately urgent
            else:
                urgency_multiplier = 1.0  # Normal
            
            urgency_score = min(base_score * urgency_multiplier, 1.0)
        else:
            urgency_score = base_score
        
        score += urgency_score * 0.4
        
        # Factor 2: Staleness penalty (30%)
        last_mentioned_chapter = conflict.get('last_mentioned_chapter', introduced_chapter)
        stale_duration = current_chapter - last_mentioned_chapter
        
        if stale_duration <= self.window_immediate:
            freshness = 1.0
        elif stale_duration <= self.window_recent:
            freshness = 0.8
        elif stale_duration <= self.window_medium:
            freshness = 0.5
        elif stale_duration <= self.window_historical:
            freshness = 0.2
        else:
            freshness = 0.05  # Very stale
        
        score += freshness * 0.3
        
        # Factor 3: Character involvement (30%)
        # Use average importance of involved characters (simplified to 0.5 for now)
        # In a full implementation, would look up actual character importance
        characters_involved = conflict.get('characters_involved', [])
        if characters_involved:
            # Assume average character importance of 0.6
            char_importance = 0.6
        else:
            char_importance = 0.3
        
        score += char_importance * 0.3
        
        return min(score, 1.0)
    
    def get_entities_with_sliding_window(self, all_entities: List[Dict[str, Any]],
                                        current_chapter: int,
                                        chapter_outline: Dict[str, Any],
                                        max_entities: int = 30) -> List[Dict[str, Any]]:
        """
        Get entities using sliding window approach with relevance scoring.
        
        Categorizes entities by recency:
        - Immediate window (last 5 chapters): Take all relevant
        - Recent window (last 20 chapters): Take 80%
        - Medium window (last 50 chapters): Take 50%
        - Historical window (last 100 chapters): Take 20%
        - Old (>100 chapters): Only if very important
        
        Args:
            all_entities: All available entities
            current_chapter: Current chapter number
            chapter_outline: Outline for current chapter
            max_entities: Maximum entities to return
            
        Returns:
            Filtered and scored list of entities
        """
        # Categorize by window
        categorized = {
            'immediate': [],
            'recent': [],
            'medium': [],
            'historical': [],
            'old': []
        }
        
        for entity in all_entities:
            # Calculate relevance score
            relevance = self.calculate_entity_relevance(entity, current_chapter, chapter_outline)
            
            # Skip if relevance too low
            if relevance < 0.05:
                continue
            
            # Get recency info
            appear_chapters = entity.get('appear_in_chapters', [])
            if not appear_chapters:
                continue
            
            last_appearance = max(appear_chapters)
            distance = current_chapter - last_appearance
            
            # Categorize by window
            scored_entity = {
                'entity': entity,
                'relevance': relevance
            }
            
            if distance <= self.window_immediate:
                categorized['immediate'].append(scored_entity)
            elif distance <= self.window_recent:
                categorized['recent'].append(scored_entity)
            elif distance <= self.window_medium:
                categorized['medium'].append(scored_entity)
            elif distance <= self.window_historical:
                categorized['historical'].append(scored_entity)
            else:
                categorized['old'].append(scored_entity)
        
        # Sort each category by relevance
        for category in categorized:
            categorized[category].sort(key=lambda x: x['relevance'], reverse=True)
        
        # Sample from each category with priority
        selected = []
        
        # Immediate: take all (highest priority)
        selected.extend([item['entity'] for item in categorized['immediate']])
        
        # Recent: take top 80%
        recent_count = len(categorized['recent'])
        recent_limit = int(recent_count * 0.8)
        selected.extend([item['entity'] for item in categorized['recent'][:recent_limit]])
        
        # Medium: take top 50%
        medium_count = len(categorized['medium'])
        medium_limit = int(medium_count * 0.5)
        selected.extend([item['entity'] for item in categorized['medium'][:medium_limit]])
        
        # Historical: take top 20%
        historical_count = len(categorized['historical'])
        historical_limit = int(historical_count * 0.2)
        selected.extend([item['entity'] for item in categorized['historical'][:historical_limit]])
        
        # Old: only if very important (relevance > 0.8)
        very_important_old = [item['entity'] for item in categorized['old'] 
                             if item['relevance'] > 0.8]
        selected.extend(very_important_old[:5])
        
        # Apply max limit
        if len(selected) > max_entities:
            # Re-score all selected entities and take top N
            scored_selected = []
            for entity in selected:
                relevance = self.calculate_entity_relevance(entity, current_chapter, chapter_outline)
                scored_selected.append({
                    'entity': entity,
                    'relevance': relevance
                })
            
            scored_selected.sort(key=lambda x: x['relevance'], reverse=True)
            selected = [item['entity'] for item in scored_selected[:max_entities]]
        
        return selected
    
    def get_events_with_sliding_window(self, all_events: List[Dict[str, Any]],
                                      current_chapter: int,
                                      chapter_outline: Dict[str, Any],
                                      max_events: int = 20) -> List[Dict[str, Any]]:
        """
        Get events using sliding window approach with relevance scoring.
        
        Args:
            all_events: All available events
            current_chapter: Current chapter number
            chapter_outline: Outline for current chapter
            max_events: Maximum events to return
            
        Returns:
            Filtered and scored list of events
        """
        scored_events = []
        
        for event in all_events:
            relevance = self.calculate_event_relevance(event, current_chapter, chapter_outline)
            
            # Skip events with very low relevance
            if relevance < 0.05:
                continue
            
            scored_events.append({
                'event': event,
                'relevance': relevance
            })
        
        # Sort by relevance
        scored_events.sort(key=lambda x: x['relevance'], reverse=True)
        
        # Return top N
        return [item['event'] for item in scored_events[:max_events]]
    
    def get_adaptive_limits(self, current_chapter: int, 
                          total_planned_chapters: int = 300) -> Dict[str, int]:
        """
        Get adaptive limits based on story progress.
        
        Story phases:
        - Introduction (0-10%): Fewer entities/events
        - Rising Action (10-30%): Building up
        - Development (30-70%): Peak complexity
        - Climax (70-90%): High but focused
        - Resolution (90-100%): Focus on main threads
        
        Args:
            current_chapter: Current chapter number
            total_planned_chapters: Total planned chapters
            
        Returns:
            Dictionary with limits for entities, events, conflicts
        """
        progress = current_chapter / total_planned_chapters
        
        if progress <= 0.1:
            # Introduction phase
            return {
                'entities': 15,
                'events': 8,
                'conflicts': 5
            }
        elif progress <= 0.3:
            # Rising action
            return {
                'entities': 25,
                'events': 15,
                'conflicts': 8
            }
        elif progress <= 0.7:
            # Development (peak complexity)
            return {
                'entities': 35,
                'events': 20,
                'conflicts': 12
            }
        elif progress <= 0.9:
            # Climax
            return {
                'entities': 30,
                'events': 25,
                'conflicts': 15
            }
        else:
            # Resolution
            return {
                'entities': 20,
                'events': 15,
                'conflicts': 8
            }
