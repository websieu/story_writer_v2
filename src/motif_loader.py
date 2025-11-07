"""
Step 1: Motif loader - Load and select story motifs
"""
import random
from typing import Dict, Any, List, Optional
from src.utils import load_json, save_json


class MotifLoader:
    """Load and manage story motifs."""
    
    def __init__(self, motif_file: str, logger):
        self.motif_file = motif_file
        self.logger = logger
        self.motifs = []
        self._load_motifs()
    
    def _load_motifs(self):
        """Load motifs from JSON file."""
        try:
            data = load_json(self.motif_file)
            self.motifs = data.get('motifs', [])
            self.logger.info(f"Loaded {len(self.motifs)} motifs from {self.motif_file}")
        except Exception as e:
            self.logger.error(f"Failed to load motifs: {str(e)}")
            raise
    
    def get_motif_by_id(self, motif_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific motif by ID."""
        for motif in self.motifs:
            if motif.get('id') == motif_id:
                return motif
        return None
    
    def get_random_motif(self, genre: Optional[str] = None) -> Dict[str, Any]:
        """Get a random motif, optionally filtered by genre."""
        filtered_motifs = self.motifs
        
        if genre:
            filtered_motifs = [m for m in self.motifs if m.get('genre') == genre]
            if not filtered_motifs:
                self.logger.warning(f"No motifs found for genre: {genre}, using all motifs")
                filtered_motifs = self.motifs
        
        if not filtered_motifs:
            raise ValueError("No motifs available")
        
        selected = random.choice(filtered_motifs)
        self.logger.info(f"Selected motif: {selected.get('id')} - {selected.get('title')}")
        return selected
    
    def get_motifs_by_theme(self, theme: str) -> List[Dict[str, Any]]:
        """Get motifs by theme."""
        return [m for m in self.motifs if theme in m.get('themes', [])]
