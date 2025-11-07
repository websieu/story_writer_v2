"""
Core utilities for the story generation system.
"""
import os
import json
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import time


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_json(file_path: str) -> Any:
    """Load JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Any, file_path: str, indent: int = 2) -> None:
    """Save data to JSON file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def load_text(file_path: str) -> str:
    """Load text file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def save_text(text: str, file_path: str) -> None:
    """Save text to file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)


def ensure_directories():
    """Ensure all required directories exist."""
    directories = [
        "data",
        "output",
        "output/chapters",
        "output/outlines",
        "output/entities",
        "output/events",
        "output/conflicts",
        "output/summaries",
        "checkpoints",
        "logs"
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


class Logger:
    """Custom logger for the story generation system."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.config = config
        self.log_config = config.get('logging', {})
        
        # Set up logging
        log_level = getattr(logging, self.log_config.get('level', 'INFO'))
        
        # Create logs directory
        os.makedirs(config['paths']['logs_dir'], exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        
        # File handler
        log_file = os.path.join(
            config['paths']['logs_dir'],
            f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def debug(self, message: str):
        self.logger.debug(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def log_llm_call(self, step: str, prompt: str, response: str, 
                     tokens: Dict[str, int], cost: float, duration: float):
        """Log LLM API call details."""
        if self.log_config.get('log_prompts', True):
            self.info(f"[{step}] Prompt:\n{prompt[:500]}..." if len(prompt) > 500 else f"[{step}] Prompt:\n{prompt}")
        
        if self.log_config.get('log_responses', True):
            self.info(f"[{step}] Response:\n{response[:500]}..." if len(response) > 500 else f"[{step}] Response:\n{response}")
        
        if self.log_config.get('log_tokens', True):
            self.info(f"[{step}] Tokens - Input: {tokens.get('input', 0)}, Output: {tokens.get('output', 0)}, Total: {tokens.get('total', 0)}")
        
        if self.log_config.get('log_cost', True):
            self.info(f"[{step}] Cost: ${cost:.4f}, Duration: {duration:.2f}s")


class CostTracker:
    """Track API costs and token usage."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pricing = config.get('cost_tracking', {}).get('pricing', {})
        self.enabled = config.get('cost_tracking', {}).get('enabled', True)
        self.total_cost = 0.0
        self.total_tokens = {'input': 0, 'output': 0, 'total': 0}
        self.calls = []
    
    def add_call(self, model: str, input_tokens: int, output_tokens: int, 
                 step: str = "", duration: float = 0.0):
        """Add an API call to the tracker."""
        if not self.enabled:
            return 0.0
        
        model_pricing = self.pricing.get(model, {'input': 0.0, 'output': 0.0})
        input_cost = (input_tokens / 1000) * model_pricing.get('input', 0.0)
        output_cost = (output_tokens / 1000) * model_pricing.get('output', 0.0)
        total_cost = input_cost + output_cost
        
        self.total_cost += total_cost
        self.total_tokens['input'] += input_tokens
        self.total_tokens['output'] += output_tokens
        self.total_tokens['total'] += (input_tokens + output_tokens)
        
        self.calls.append({
            'timestamp': datetime.now().isoformat(),
            'step': step,
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cost': total_cost,
            'duration': duration
        })
        
        return total_cost
    
    def get_summary(self) -> Dict[str, Any]:
        """Get cost and usage summary."""
        return {
            'total_cost': self.total_cost,
            'total_tokens': self.total_tokens,
            'total_calls': len(self.calls),
            'calls': self.calls
        }
    
    def save_summary(self, file_path: str):
        """Save cost summary to file."""
        save_json(self.get_summary(), file_path)
