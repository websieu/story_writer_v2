"""
Checkpoint manager for resumable story generation.
"""
import os
import json
from typing import Any, Dict, Optional
from datetime import datetime
from src.utils import save_json, load_json


class CheckpointManager:
    """Manage checkpoints for resumable execution."""
    
    def __init__(self, checkpoint_dir: str, story_id: str):
        self.checkpoint_dir = checkpoint_dir
        self.story_id = story_id
        self.checkpoint_file = os.path.join(
            checkpoint_dir, 
            f"{story_id}_checkpoint.json"
        )
        os.makedirs(checkpoint_dir, exist_ok=True)
        self.state = self._load_checkpoint()
    
    def _load_checkpoint(self) -> Dict[str, Any]:
        """Load checkpoint from file."""
        if os.path.exists(self.checkpoint_file):
            return load_json(self.checkpoint_file)
        return {
            'story_id': self.story_id,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'current_batch': 1,
            'current_chapter': 0,
            'completed_steps': {},
            'metadata': {}
        }
    
    def save_checkpoint(self):
        """Save current state to checkpoint file."""
        self.state['last_updated'] = datetime.now().isoformat()
        save_json(self.state, self.checkpoint_file)
    
    def is_step_completed(self, step_name: str, batch: Optional[int] = None, 
                          chapter: Optional[int] = None) -> bool:
        """Check if a step has been completed."""
        key = self._make_key(step_name, batch, chapter)
        return key in self.state['completed_steps']
    
    def mark_step_completed(self, step_name: str, batch: Optional[int] = None, 
                           chapter: Optional[int] = None, metadata: Optional[Dict] = None):
        """Mark a step as completed."""
        key = self._make_key(step_name, batch, chapter)
        self.state['completed_steps'][key] = {
            'completed_at': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        self.save_checkpoint()
    
    def get_step_metadata(self, step_name: str, batch: Optional[int] = None, 
                         chapter: Optional[int] = None) -> Optional[Dict]:
        """Get metadata for a completed step."""
        key = self._make_key(step_name, batch, chapter)
        step_data = self.state['completed_steps'].get(key)
        return step_data.get('metadata') if step_data else None
    
    def _make_key(self, step_name: str, batch: Optional[int] = None, 
                  chapter: Optional[int] = None) -> str:
        """Create a unique key for a step."""
        if batch is not None and chapter is not None:
            return f"{step_name}_batch{batch}_ch{chapter}"
        elif batch is not None:
            return f"{step_name}_batch{batch}"
        else:
            return step_name
    
    def update_progress(self, batch: int, chapter: int):
        """Update current progress."""
        self.state['current_batch'] = batch
        self.state['current_chapter'] = chapter
        self.save_checkpoint()
    
    def set_metadata(self, key: str, value: Any):
        """Set metadata value."""
        self.state['metadata'][key] = value
        self.save_checkpoint()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.state['metadata'].get(key, default)
    
    def reset(self):
        """Reset checkpoint to initial state."""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
        self.state = self._load_checkpoint()
