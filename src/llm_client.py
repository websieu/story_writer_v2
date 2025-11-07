"""
LLM client wrapper for story generation system.
Sử dụng Gemini API thông qua gemini_client_pool.
"""
import os
import time
from typing import Dict, Any, Optional
from src.gemini_client_pool import gemini_call_text_free, gemini_call_json_free


class LLMClient:
    """Wrapper for LLM API calls with token counting and cost tracking."""
    
    def __init__(self, config: Dict[str, Any], logger, cost_tracker):
        self.config = config
        self.logger = logger
        self.cost_tracker = cost_tracker
        self.default_config = config.get('default_llm', {})
        self.task_configs = config.get('task_configs', {})
        
        # Không cần load keys ở đây nữa, mỗi lần call API sẽ tự động load keys ngẫu nhiên
        self.logger.info("LLMClient initialized. Keys will be loaded dynamically on each API call.")
    
    def call(self, prompt: str, task_name: str = "default", 
             system_message: Optional[str] = None, 
             return_json: bool = False, 
             batch_id: Optional[int] = None,
             chapter_id: Optional[int] = None,
             **kwargs) -> Dict[str, Any]:
        """
        Call LLM API with automatic logging.
        
        Args:
            prompt: User prompt
            task_name: Task name to get specific configuration
            system_message: Optional system message
            return_json: If True, parse response as JSON
            batch_id: Current batch number (for logging)
            chapter_id: Current chapter number (for logging)
            **kwargs: Additional parameters to override config
            
        Returns:
            Dictionary containing response, tokens, cost, and duration
        """
        # Get task-specific configuration
        task_config = self.task_configs.get(task_name, {})
        
        # Merge configurations (kwargs > task_config > default_config)
        llm_config = {**self.default_config, **task_config, **kwargs}
        
        model = llm_config.get('model', 'gemini-2.5-flash')
        temperature = llm_config.get('temperature', 0.7)
        
        # System message
        sys_msg = system_message or ""
        
        # Call API with exception handling
        start_time = time.time()
        response_text = None
        error = None
        
        try:
            self.logger.info(f"Calling Gemini API: model={model}, task={task_name}, batch={batch_id}, chapter={chapter_id}")
            
            if return_json:
                # Không cần truyền keys, sẽ tự động load từ config
                response_data = gemini_call_json_free(
                    system_prompt=sys_msg,
                    user_prompt=prompt,
                    model=model,
                    temperature=temperature,
                    per_job_sleep=0.1  # Giảm sleep time
                )
                # Convert to string for consistent handling
                import json
                response_text = json.dumps(response_data, ensure_ascii=False)
            else:
                # Không cần truyền keys, sẽ tự động load từ config
                response_text = gemini_call_text_free(
                    system_prompt=sys_msg,
                    user_prompt=prompt,
                    model=model,
                    temperature=temperature,
                    per_job_sleep=0.1
                )
            
            duration = time.time() - start_time
            
            # Estimate tokens (rough estimate for Gemini)
            input_tokens = self._estimate_tokens(sys_msg + prompt)
            output_tokens = self._estimate_tokens(response_text)
            total_tokens = input_tokens + output_tokens
            
            # Calculate cost (Gemini pricing)
            cost = self._calculate_gemini_cost(model, input_tokens, output_tokens)
            
            # Track cost
            self.cost_tracker.add_call(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                step=task_name,
                duration=duration
            )
            
            # Log to main log
            self.logger.log_llm_call(
                step=task_name,
                prompt=prompt,
                response=response_text,
                tokens={
                    'input': input_tokens,
                    'output': output_tokens,
                    'total': total_tokens
                },
                cost=cost,
                duration=duration
            )
            
            # Log detailed request to separate file
            self.logger.log_llm_request(
                task_name=task_name,
                system_prompt=sys_msg,
                user_prompt=prompt,
                response=response_text,
                error=None,
                batch_id=batch_id,
                chapter_id=chapter_id,
                tokens={
                    'input': input_tokens,
                    'output': output_tokens,
                    'total': total_tokens
                },
                cost=cost,
                duration=duration,
                model=model
            )
            
            return {
                'response': response_text,
                'tokens': {
                    'input': input_tokens,
                    'output': output_tokens,
                    'total': total_tokens
                },
                'cost': cost,
                'duration': duration,
                'model': model
            }
            
        except Exception as e:
            duration = time.time() - start_time
            error = str(e)
            
            # Log error to main log
            self.logger.error(f"LLM API call failed: {error}")
            
            # Log error to separate file with prompts
            self.logger.log_llm_error(
                task_name=task_name,
                system_prompt=sys_msg,
                user_prompt=prompt,
                error=error,
                batch_id=batch_id,
                chapter_id=chapter_id,
                model=model
            )
            
            raise
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate tokens for Gemini (rough approximation)."""
        # Gemini uses similar tokenization to GPT
        # Rough estimate: ~4 chars per token for English, ~2-3 for Vietnamese
        if not text:
            return 0
        # Use 2.5 chars per token as average for Vietnamese
        return int(len(text) / 2.5)
    
    def _calculate_gemini_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for Gemini API calls."""
        # Gemini 2.5 Flash pricing (as of 2025)
        # Free tier: very generous limits
        # Paid: $0.075 per 1M input tokens, $0.30 per 1M output tokens for Flash
        # Pro: $1.25 per 1M input tokens, $5.00 per 1M output tokens
        
        if 'pro' in model.lower():
            input_cost_per_1m = 1.25
            output_cost_per_1m = 5.00
        else:  # flash or other
            input_cost_per_1m = 0.075
            output_cost_per_1m = 0.30
        
        input_cost = (input_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * output_cost_per_1m
        
        return input_cost + output_cost
