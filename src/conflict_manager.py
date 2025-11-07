"""
Conflict management utilities for long-form stories.
Includes automatic pruning and priority scoring.
"""
from typing import Dict, Any, List, Tuple


class ConflictManager:
    """Manage conflicts for long-form story generation."""
    
    def __init__(self, config: Dict[str, Any], logger):
        """
        Initialize conflict manager.
        
        Args:
            config: Configuration dictionary
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        
        # Pruning thresholds by timeline (chapters of inactivity)
        self.pruning_thresholds = {
            'immediate': 10,
            'batch': 10,
            'short_term': 30,
            'medium_term': 100,
            'long_term': None,  # Never auto-prune
            'epic': None  # Never auto-prune
        }
    
    def prune_stale_conflicts(self, conflicts: List[Dict[str, Any]], 
                             current_chapter: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Automatically prune conflicts that have been inactive for too long.
        
        Rules:
        - immediate/batch: prune if inactive > 10 chapters
        - short_term: prune if inactive > 30 chapters
        - medium_term: prune if inactive > 100 chapters
        - long_term/epic: never auto-prune
        
        Args:
            conflicts: List of all conflicts
            current_chapter: Current chapter number
            
        Returns:
            Tuple of (active_conflicts, pruned_conflicts)
        """
        active_conflicts = []
        pruned_conflicts = []
        
        for conflict in conflicts:
            # Skip already resolved conflicts
            if conflict.get('status') != 'active':
                continue
            
            timeline = conflict.get('timeline', 'medium_term')
            threshold = self.pruning_thresholds.get(timeline)
            
            # Don't prune if no threshold (long_term/epic)
            if threshold is None:
                active_conflicts.append(conflict)
                continue
            
            # Calculate staleness
            introduced_chapter = conflict.get('introduced_chapter', 1)
            last_mentioned = conflict.get('last_mentioned_chapter', introduced_chapter)
            stale_duration = current_chapter - last_mentioned
            
            # Prune if too stale
            if stale_duration > threshold:
                conflict['status'] = 'abandoned'
                conflict['resolution_chapter'] = current_chapter
                conflict['resolution_note'] = (
                    f'Auto-pruned: {stale_duration} chapters of inactivity '
                    f'(threshold: {threshold})'
                )
                pruned_conflicts.append(conflict)
                
                self.logger.info(
                    f"Pruned stale conflict: {conflict.get('id')} "
                    f"(timeline: {timeline}, inactive: {stale_duration} chapters)"
                )
            else:
                active_conflicts.append(conflict)
        
        if pruned_conflicts:
            self.logger.info(
                f"Pruned {len(pruned_conflicts)} stale conflicts at chapter {current_chapter}"
            )
        
        return active_conflicts, pruned_conflicts
    
    def select_conflicts_for_batch(self, all_conflicts: List[Dict[str, Any]],
                                  current_batch: int,
                                  current_chapter: int,
                                  relevance_scorer) -> List[Dict[str, Any]]:
        """
        Select conflicts for the next batch with priority scoring.
        
        Args:
            all_conflicts: All available conflicts
            current_batch: Current batch number
            current_chapter: Current chapter number
            relevance_scorer: RelevanceScorer instance for priority calculation
            
        Returns:
            List of selected conflicts sorted by priority
        """
        # First, prune stale conflicts
        active_conflicts, pruned = self.prune_stale_conflicts(all_conflicts, current_chapter)
        
        # Score remaining conflicts
        scored_conflicts = []
        for conflict in active_conflicts:
            priority = relevance_scorer.calculate_conflict_priority(conflict, current_chapter)
            scored_conflicts.append({
                'conflict': conflict,
                'priority': priority
            })
        
        # Sort by priority
        scored_conflicts.sort(key=lambda x: x['priority'], reverse=True)
        
        # Determine limit based on batch number (adaptive)
        if current_batch <= 5:
            limit = 5  # Early story: fewer conflicts
        elif current_batch <= 20:
            limit = 8
        elif current_batch <= 40:
            limit = 12
        else:
            limit = 15  # Late story: more conflicts
        
        # Select top N
        selected = [item['conflict'] for item in scored_conflicts[:limit]]
        
        self.logger.info(
            f"Selected {len(selected)} conflicts for batch {current_batch} "
            f"from {len(active_conflicts)} active conflicts"
        )
        
        return selected
    
    def update_conflict_mentions(self, conflicts: List[Dict[str, Any]],
                                chapter_num: int,
                                chapter_outline: Dict[str, Any]) -> List[str]:
        """
        Update last_mentioned_chapter for conflicts mentioned in outline.
        
        Args:
            conflicts: List of all conflicts
            chapter_num: Current chapter number
            chapter_outline: Chapter outline data
            
        Returns:
            List of conflict IDs that were mentioned
        """
        mentioned_ids = []
        
        # Get conflict IDs mentioned in outline
        outline_conflict_ids = set(chapter_outline.get('conflict_ids', []))
        
        # Update last_mentioned_chapter
        for conflict in conflicts:
            conflict_id = conflict.get('id', '')
            if conflict_id in outline_conflict_ids:
                conflict['last_mentioned_chapter'] = chapter_num
                mentioned_ids.append(conflict_id)
        
        if mentioned_ids:
            self.logger.info(
                f"Updated mention tracking for {len(mentioned_ids)} conflicts "
                f"in chapter {chapter_num}"
            )
        
        return mentioned_ids
    
    def get_conflicts_by_timeline(self, conflicts: List[Dict[str, Any]],
                                 timeline: str) -> List[Dict[str, Any]]:
        """
        Get active conflicts filtered by timeline.
        
        Args:
            conflicts: List of all conflicts
            timeline: Timeline to filter by
            
        Returns:
            Filtered list of conflicts
        """
        return [
            c for c in conflicts
            if c.get('status') == 'active' and c.get('timeline') == timeline
        ]
    
    def get_conflicts_needing_resolution(self, conflicts: List[Dict[str, Any]],
                                       current_chapter: int) -> List[Dict[str, Any]]:
        """
        Get conflicts that need resolution based on timeline and progress.
        
        Args:
            conflicts: List of all conflicts
            current_chapter: Current chapter number
            
        Returns:
            List of conflicts that should be resolved soon
        """
        urgent_conflicts = []
        
        timeline_durations = {
            'immediate': 1,
            'batch': 5,
            'short_term': 10,
            'medium_term': 30,
            'long_term': 100,
            'epic': 300
        }
        
        for conflict in conflicts:
            if conflict.get('status') != 'active':
                continue
            
            timeline = conflict.get('timeline', 'medium_term')
            expected_duration = timeline_durations.get(timeline, 30)
            
            introduced = conflict.get('introduced_chapter', 1)
            elapsed = current_chapter - introduced
            
            # Flag if > 80% of expected duration has elapsed
            if elapsed >= expected_duration * 0.8:
                urgent_conflicts.append(conflict)
        
        return urgent_conflicts
    
    def suggest_new_conflicts(self, current_chapter: int,
                            active_count: int,
                            story_phase: str) -> Dict[str, Any]:
        """
        Suggest if new conflicts should be introduced.
        
        Args:
            current_chapter: Current chapter number
            active_count: Number of active conflicts
            story_phase: Current story phase (introduction/development/climax/resolution)
            
        Returns:
            Suggestion dictionary with recommended action
        """
        phase_optimal_conflicts = {
            'introduction': 3,
            'rising_action': 6,
            'development': 10,
            'climax': 8,  # Focus on resolving
            'resolution': 4   # Mostly resolving
        }
        
        optimal = phase_optimal_conflicts.get(story_phase, 8)
        
        if active_count < optimal * 0.7:
            return {
                'action': 'introduce',
                'reason': f'Too few conflicts ({active_count}) for {story_phase} phase',
                'suggested_count': optimal - active_count,
                'suggested_timelines': self._suggest_timelines_for_phase(story_phase)
            }
        elif active_count > optimal * 1.5:
            return {
                'action': 'reduce',
                'reason': f'Too many conflicts ({active_count}) for {story_phase} phase',
                'suggested_resolution_count': active_count - optimal
            }
        else:
            return {
                'action': 'maintain',
                'reason': f'Conflict count ({active_count}) appropriate for {story_phase}'
            }
    
    def _suggest_timelines_for_phase(self, phase: str) -> List[str]:
        """Suggest appropriate conflict timelines for story phase."""
        if phase == 'introduction':
            return ['immediate', 'batch', 'short_term']
        elif phase == 'rising_action':
            return ['batch', 'short_term', 'medium_term']
        elif phase == 'development':
            return ['short_term', 'medium_term', 'long_term']
        elif phase == 'climax':
            return ['immediate', 'batch']  # Focus on urgent conflicts
        else:  # resolution
            return ['immediate']  # Wrap up quickly
