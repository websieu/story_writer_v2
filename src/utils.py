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


def get_project_paths(project_id: str, config: Dict[str, Any]) -> Dict[str, str]:
    """
    Get all paths for a specific project.
    All data stored in projects/{project_id}/
    """
    base_dir = config['paths']['projects_base_dir']
    project_root = os.path.join(base_dir, project_id)
    subdirs = config['paths']['project_subdirs']
    
    paths = {
        'project_root': project_root,
        'logs_dir': os.path.join(project_root, subdirs['logs']),
        'checkpoints_dir': os.path.join(project_root, subdirs['checkpoints']),
        'outputs_dir': os.path.join(project_root, subdirs['outputs']),
        'chapters_dir': os.path.join(project_root, subdirs['chapters']),
        'outlines_dir': os.path.join(project_root, subdirs['outlines']),
        'entities_dir': os.path.join(project_root, subdirs['entities']),
        'events_dir': os.path.join(project_root, subdirs['events']),
        'conflicts_dir': os.path.join(project_root, subdirs['conflicts']),
        'summaries_dir': os.path.join(project_root, subdirs['summaries']),
        'llm_logs_dir': os.path.join(project_root, subdirs['llm_logs']),
    }
    
    return paths


def ensure_project_directories(project_id: str, config: Dict[str, Any]):
    """Ensure all required directories exist for a project."""
    paths = get_project_paths(project_id, config)
    
    for path in paths.values():
        os.makedirs(path, exist_ok=True)


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


class Logger:
    """
    Custom logger for the story generation system.
    Logs each LLM request to separate files organized by task/batch/chapter.
    """
    
    def __init__(self, name: str, project_id: str, config: Dict[str, Any]):
        self.config = config
        self.project_id = project_id
        self.log_config = config.get('logging', {})
        self.paths = get_project_paths(project_id, config)
        
        # Set up logging
        log_level = getattr(logging, self.log_config.get('level', 'INFO'))
        
        # Create logs directory
        os.makedirs(self.paths['logs_dir'], exist_ok=True)
        os.makedirs(self.paths['llm_logs_dir'], exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        
        # File handler - main log
        log_file = os.path.join(
            self.paths['logs_dir'],
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
        """Log LLM API call details to main log."""
        if self.log_config.get('log_prompts', True):
            self.info(f"[{step}] Prompt:\n{prompt[:500]}..." if len(prompt) > 500 else f"[{step}] Prompt:\n{prompt}")
        
        if self.log_config.get('log_responses', True):
            self.info(f"[{step}] Response:\n{response[:500]}..." if len(response) > 500 else f"[{step}] Response:\n{response}")
        
        if self.log_config.get('log_tokens', True):
            self.info(f"[{step}] Tokens - Input: {tokens.get('input', 0)}, Output: {tokens.get('output', 0)}, Total: {tokens.get('total', 0)}")
        
        if self.log_config.get('log_cost', True):
            self.info(f"[{step}] Cost: ${cost:.4f}, Duration: {duration:.2f}s")
    
    def log_llm_request(self, task_name: str, system_prompt: str, user_prompt: str,
                       response: Optional[str] = None, error: Optional[str] = None,
                       batch_id: Optional[int] = None, chapter_id: Optional[int] = None,
                       tokens: Optional[Dict[str, int]] = None, cost: Optional[float] = None,
                       duration: Optional[float] = None, model: Optional[str] = None):
        """
        Log individual LLM request to separate file.
        File naming: {task_name}_batch{batch_id}_chapter{chapter_id}_{timestamp}.txt
        
        Args:
            task_name: Name of the task (outline_generation, chapter_writing, etc.)
            system_prompt: System prompt sent to LLM
            user_prompt: User prompt sent to LLM
            response: LLM response (if successful)
            error: Error message (if failed)
            batch_id: Batch number (optional)
            chapter_id: Chapter number (optional)
            tokens: Token usage dict
            cost: API call cost
            duration: Call duration in seconds
            model: Model name used
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        
        # Build filename
        filename_parts = [task_name]
        if batch_id is not None:
            filename_parts.append(f"batch{batch_id:03d}")
        if chapter_id is not None:
            filename_parts.append(f"chapter{chapter_id:03d}")
        filename_parts.append(timestamp)
        
        filename = "_".join(filename_parts) + ".txt"
        filepath = os.path.join(self.paths['llm_logs_dir'], filename)
        
        # Prepare log content
        log_lines = []
        log_lines.append("=" * 80)
        log_lines.append(f"LLM REQUEST LOG")
        log_lines.append("=" * 80)
        log_lines.append(f"Timestamp: {datetime.now().isoformat()}")
        log_lines.append(f"Project ID: {self.project_id}")
        log_lines.append(f"Task: {task_name}")
        if batch_id is not None:
            log_lines.append(f"Batch: {batch_id}")
        if chapter_id is not None:
            log_lines.append(f"Chapter: {chapter_id}")
        if model:
            log_lines.append(f"Model: {model}")
        
        log_lines.append("\n" + "-" * 80)
        log_lines.append("SYSTEM PROMPT:")
        log_lines.append("-" * 80)
        log_lines.append(system_prompt)
        
        log_lines.append("\n" + "-" * 80)
        log_lines.append("USER PROMPT:")
        log_lines.append("-" * 80)
        log_lines.append(user_prompt)
        
        if response:
            log_lines.append("\n" + "-" * 80)
            log_lines.append("RESPONSE:")
            log_lines.append("-" * 80)
            log_lines.append(response)
        
        if error:
            log_lines.append("\n" + "-" * 80)
            log_lines.append("ERROR:")
            log_lines.append("-" * 80)
            log_lines.append(error)
        
        log_lines.append("\n" + "-" * 80)
        log_lines.append("METRICS:")
        log_lines.append("-" * 80)
        if tokens:
            log_lines.append(f"Input Tokens: {tokens.get('input', 0)}")
            log_lines.append(f"Output Tokens: {tokens.get('output', 0)}")
            log_lines.append(f"Total Tokens: {tokens.get('total', 0)}")
        if cost is not None:
            log_lines.append(f"Cost: ${cost:.4f}")
        if duration is not None:
            log_lines.append(f"Duration: {duration:.2f}s")
        
        log_lines.append("=" * 80)
        
        # Save to file
        try:
            save_text("\n".join(log_lines), filepath)
            self.debug(f"Saved LLM request log to: {filepath}")
        except Exception as e:
            self.error(f"Failed to save LLM request log: {e}")
    def log_llm_error(self, task_name: str, system_prompt: str, user_prompt: str,
                     error: str, batch_id: Optional[int] = None, 
                     chapter_id: Optional[int] = None, model: Optional[str] = None):
        """
        Log LLM request that resulted in error.
        Saves both prompts and error message for debugging.
        """
        self.log_llm_request(
            task_name=task_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=None,
            error=error,
            batch_id=batch_id,
            chapter_id=chapter_id,
            model=model
        )
        self.error(f"LLM Error in {task_name}: {error}")



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
