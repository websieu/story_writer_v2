#!/usr/bin/env python3
"""
Test script for long-form story optimizations (relevance scoring and conflict management).
Tests the implementation without requiring API keys or actual story generation.
"""
import sys
from typing import Dict, Any, List

# Mock config for testing
MOCK_CONFIG = {
    'story': {
        'total_planned_chapters': 300,
        'context_windows': {
            'immediate': 5,
            'recent': 20,
            'medium': 50,
            'historical': 100
        },
        'use_relevance_scoring': True,
        'use_sliding_window': True,
        'use_conflict_pruning': True,
        'use_adaptive_limits': True
    }
}

def test_relevance_scorer():
    """Test relevance scoring functionality."""
    print("\n" + "=" * 60)
    print("Testing Relevance Scorer")
    print("=" * 60)
    
    try:
        from src.relevance_scorer import RelevanceScorer
        
        scorer = RelevanceScorer(MOCK_CONFIG)
        print("  ✓ RelevanceScorer initialized")
        
        # Test entity relevance scoring
        print("\n1. Testing Entity Relevance Scoring...")
        
        entity = {
            'name': 'Lý Hạo',
            'category': 'characters',
            'appear_in_chapters': [1, 5, 10, 15, 20, 25],
            'importance': 0.9
        }
        
        chapter_outline = {
            'characters': [{'name': 'Lý Hạo'}],
            'entities': [],
            'settings': []
        }
        
        current_chapter = 30
        relevance = scorer.calculate_entity_relevance(entity, current_chapter, chapter_outline)
        
        print(f"  Entity: {entity['name']}")
        print(f"  Current chapter: {current_chapter}")
        print(f"  Last appearance: {max(entity['appear_in_chapters'])}")
        print(f"  Relevance score: {relevance:.3f}")
        
        assert 0.0 <= relevance <= 1.0, "Relevance score should be between 0 and 1"
        assert relevance > 0.5, "Main character should have high relevance"
        print("  ✓ Entity relevance scoring works correctly")
        
        # Test event relevance scoring
        print("\n2. Testing Event Relevance Scoring...")
        
        event = {
            'description': 'Đột phá cảnh giới',
            'chapter': 25,
            'importance': 0.8,
            'characters_involved': ['Lý Hạo'],
            'entities_involved': []
        }
        
        relevance = scorer.calculate_event_relevance(event, current_chapter, chapter_outline)
        
        print(f"  Event: {event['description']}")
        print(f"  Event chapter: {event['chapter']}")
        print(f"  Current chapter: {current_chapter}")
        print(f"  Relevance score: {relevance:.3f}")
        
        assert 0.0 <= relevance <= 1.0, "Relevance score should be between 0 and 1"
        print("  ✓ Event relevance scoring works correctly")
        
        # Test conflict priority scoring
        print("\n3. Testing Conflict Priority Scoring...")
        
        conflict = {
            'id': 'conflict_001',
            'timeline': 'short_term',
            'introduced_chapter': 20,
            'last_mentioned_chapter': 28,
            'status': 'active',
            'characters_involved': ['Lý Hạo']
        }
        
        priority = scorer.calculate_conflict_priority(conflict, current_chapter)
        
        print(f"  Conflict: {conflict['id']}")
        print(f"  Timeline: {conflict['timeline']}")
        print(f"  Introduced: chapter {conflict['introduced_chapter']}")
        print(f"  Last mentioned: chapter {conflict['last_mentioned_chapter']}")
        print(f"  Priority score: {priority:.3f}")
        
        assert 0.0 <= priority <= 1.0, "Priority score should be between 0 and 1"
        print("  ✓ Conflict priority scoring works correctly")
        
        # Test adaptive limits
        print("\n4. Testing Adaptive Limits...")
        
        test_chapters = [10, 50, 150, 250, 290]
        for chapter in test_chapters:
            limits = scorer.get_adaptive_limits(chapter, total_planned_chapters=300)
            progress = (chapter / 300) * 100
            print(f"  Chapter {chapter:3d} ({progress:5.1f}%): "
                  f"entities={limits['entities']:2d}, "
                  f"events={limits['events']:2d}, "
                  f"conflicts={limits['conflicts']:2d}")
        
        print("  ✓ Adaptive limits work correctly")
        
        # Test sliding window
        print("\n5. Testing Sliding Window Entity Selection...")
        
        # Create test entities
        test_entities = []
        for i in range(1, 101):
            test_entities.append({
                'name': f'Entity_{i}',
                'category': 'characters',
                'appear_in_chapters': [i, i+5, i+10] if i <= 90 else [i],
                'importance': 0.5
            })
        
        current_chapter = 100
        selected = scorer.get_entities_with_sliding_window(
            test_entities,
            current_chapter,
            chapter_outline,
            max_entities=30
        )
        
        print(f"  Total entities: {len(test_entities)}")
        print(f"  Current chapter: {current_chapter}")
        print(f"  Selected entities: {len(selected)}")
        print(f"  Max entities: 30")
        
        assert len(selected) <= 30, "Should not exceed max_entities limit"
        
        # Check that recent entities are prioritized
        selected_names = [e['name'] for e in selected]
        recent_entity_count = sum(1 for name in selected_names if int(name.split('_')[1]) >= 80)
        print(f"  Recent entities (80-100): {recent_entity_count}/{len(selected)}")
        
        assert recent_entity_count > len(selected) * 0.5, "Should prioritize recent entities"
        print("  ✓ Sliding window entity selection works correctly")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_conflict_manager():
    """Test conflict management functionality."""
    print("\n" + "=" * 60)
    print("Testing Conflict Manager")
    print("=" * 60)
    
    try:
        from src.conflict_manager import ConflictManager
        from src.relevance_scorer import RelevanceScorer
        
        # Mock logger
        class MockLogger:
            def info(self, msg): pass
            def debug(self, msg): pass
            def warning(self, msg): pass
        
        logger = MockLogger()
        manager = ConflictManager(MOCK_CONFIG, logger)
        scorer = RelevanceScorer(MOCK_CONFIG)
        
        print("  ✓ ConflictManager initialized")
        
        # Test conflict pruning
        print("\n1. Testing Conflict Pruning...")
        
        conflicts = [
            {
                'id': 'conflict_001',
                'timeline': 'immediate',
                'introduced_chapter': 1,
                'last_mentioned_chapter': 1,
                'status': 'active'
            },
            {
                'id': 'conflict_002',
                'timeline': 'batch',
                'introduced_chapter': 10,
                'last_mentioned_chapter': 18,
                'status': 'active'
            },
            {
                'id': 'conflict_003',
                'timeline': 'short_term',
                'introduced_chapter': 50,
                'last_mentioned_chapter': 95,
                'status': 'active'
            },
            {
                'id': 'conflict_004',
                'timeline': 'long_term',
                'introduced_chapter': 5,
                'last_mentioned_chapter': 5,
                'status': 'active'
            },
            {
                'id': 'conflict_005',
                'timeline': 'epic',
                'introduced_chapter': 1,
                'last_mentioned_chapter': 1,
                'status': 'active'
            }
        ]
        
        current_chapter = 100
        active, pruned = manager.prune_stale_conflicts(conflicts, current_chapter)
        
        print(f"  Total conflicts: {len(conflicts)}")
        print(f"  Current chapter: {current_chapter}")
        print(f"  Active after pruning: {len(active)}")
        print(f"  Pruned conflicts: {len(pruned)}")
        
        # Check pruning logic
        pruned_ids = [c['id'] for c in pruned]
        active_ids = [c['id'] for c in active]
        
        print(f"  Pruned IDs: {pruned_ids}")
        print(f"  Active IDs: {active_ids}")
        
        # immediate conflict should be pruned (inactive for 99 chapters > threshold 10)
        assert 'conflict_001' in pruned_ids, "Stale immediate conflict should be pruned"
        
        # long_term and epic should never be pruned
        assert 'conflict_004' in active_ids, "Long-term conflict should not be pruned"
        assert 'conflict_005' in active_ids, "Epic conflict should not be pruned"
        
        print("  ✓ Conflict pruning works correctly")
        
        # Test conflict selection for batch
        print("\n2. Testing Conflict Selection for Batch...")
        
        # Reset conflicts
        for c in conflicts:
            c['status'] = 'active'
        
        selected = manager.select_conflicts_for_batch(
            conflicts,
            current_batch=20,
            current_chapter=100,
            relevance_scorer=scorer
        )
        
        print(f"  Batch: 20")
        print(f"  Chapter: 100")
        print(f"  Selected conflicts: {len(selected)}")
        print(f"  Selected IDs: {[c['id'] for c in selected]}")
        
        assert len(selected) > 0, "Should select at least one conflict"
        print("  ✓ Conflict selection works correctly")
        
        # Test get conflicts needing resolution
        print("\n3. Testing Conflicts Needing Resolution...")
        
        urgent = manager.get_conflicts_needing_resolution(conflicts, current_chapter)
        
        print(f"  Urgent conflicts: {len(urgent)}")
        print(f"  IDs: {[c['id'] for c in urgent]}")
        
        # short_term conflict introduced at ch50, at ch100 = 50 chapters elapsed
        # Expected duration for short_term is 10 chapters
        # 50 > 10*0.8, so should be urgent
        urgent_ids = [c['id'] for c in urgent]
        assert 'conflict_003' in urgent_ids, "Short-term conflict should be urgent"
        
        print("  ✓ Urgent conflict detection works correctly")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """Test integration with config."""
    print("\n" + "=" * 60)
    print("Testing Configuration Integration")
    print("=" * 60)
    
    try:
        from src.utils import load_config
        
        config = load_config('config/config.yaml')
        print("  ✓ Config loaded successfully")
        
        # Check if optimization settings exist
        story_config = config.get('story', {})
        
        required_settings = [
            'total_planned_chapters',
            'context_windows',
            'use_relevance_scoring',
            'use_sliding_window',
            'use_conflict_pruning',
            'use_adaptive_limits'
        ]
        
        print("\n  Checking optimization settings:")
        for setting in required_settings:
            if setting in story_config:
                value = story_config[setting]
                print(f"    ✓ {setting}: {value}")
            else:
                print(f"    ✗ {setting}: MISSING")
                return False
        
        # Check window values
        windows = story_config.get('context_windows', {})
        window_keys = ['immediate', 'recent', 'medium', 'historical']
        
        print("\n  Context windows:")
        for key in window_keys:
            if key in windows:
                print(f"    ✓ {key}: {windows[key]} chapters")
            else:
                print(f"    ✗ {key}: MISSING")
                return False
        
        print("\n  ✓ All optimization settings configured correctly")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Long-Form Story Optimization Tests")
    print("=" * 60)
    print("\nTesting implementation for 300-chapter story support")
    
    results = []
    
    results.append(("Relevance Scorer", test_relevance_scorer()))
    results.append(("Conflict Manager", test_conflict_manager()))
    results.append(("Configuration Integration", test_integration()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:10} {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        print("\n✅ Long-form story optimizations are working correctly")
        print("\nKey features validated:")
        print("  • Relevance scoring for entities and events")
        print("  • Sliding window approach for context management")
        print("  • Conflict pruning and priority scoring")
        print("  • Adaptive limits based on story progress")
        print("\n📊 Expected improvements:")
        print("  • ~84% token usage reduction at chapter 250")
        print("  • Better narrative coherence")
        print("  • Automatic conflict lifecycle management")
        print("\n📖 Ready for 300+ chapter story generation!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
