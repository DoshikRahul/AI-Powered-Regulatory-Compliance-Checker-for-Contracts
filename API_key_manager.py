import os
from dotenv import load_dotenv
from functools import wraps
import time
from typing import Optional, Dict, List, Callable, Any
import logging
from groq import Groq, RateLimitError
import notifications

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

class APIKeyManager:
    def __init__(self):
        # Load API keys from environment
        self.api_keys: List[str] = [
            os.getenv("GROQ_API_KEY_1"),
            os.getenv("GROQ_API_KEY_2")
        ]
        self.current_key_index: int = 0
        self.rate_limit_cooldown: Dict[int, float] = {0: 0, 1: 0}  # Track when each key can be used again
        self.request_count: Dict[int, int] = {0: 0, 1: 0}  # Track request count per key
        self.last_reset: float = time.time()
        
        # Validate API keys
        if not any(self.api_keys):
            raise ValueError("No API keys found in .env file. Please add GROQ_API_KEY_1 and GROQ_API_KEY_2 to your .env file")
        
        self.validate_api_keys()
        logger.info(f"✓ API Key Manager initialized with {len(self.api_keys)} key(s)")
    
    def validate_api_keys(self) -> None:
        """Validate all API keys and remove invalid ones."""
        valid_keys = []
        valid_indices = []
        
        for i, key in enumerate(self.api_keys):
            if key and len(key) > 0:
                valid_keys.append(key)
                valid_indices.append(i)
                logger.info(f"✓ API Key {i + 1} loaded successfully")
            else:
                logger.warning(f"✗ API Key {i + 1} is missing or invalid")
        
        self.api_keys = valid_keys
        
        # Update tracking dicts to only include valid keys
        self.rate_limit_cooldown = {i: 0 for i in range(len(valid_keys))}
        self.request_count = {i: 0 for i in range(len(valid_keys))}
        
        if not self.api_keys:
            raise ValueError("No valid API keys available. Please check your .env file")
    
    def get_current_key(self) -> str:
        """Get the current API key, switching if necessary."""
        # Check if current key is in cooldown
        if time.time() < self.rate_limit_cooldown[self.current_key_index]:
            logger.info(f"Key {self.current_key_index + 1} is in cooldown, switching...")
            next_key = self.switch_key()
            if not next_key:
                # Calculate wait time
                wait_times = [max(0, self.rate_limit_cooldown[i] - time.time()) for i in range(len(self.api_keys))]
                min_wait = min(wait_times)
                logger.warning(f"All keys are in cooldown. Minimum wait time: {min_wait:.1f} seconds")
                if min_wait > 0:
                    logger.info(f"Waiting {min_wait:.1f} seconds for next available key...")
                    time.sleep(min_wait + 1)
                    # Reset to first available key
                    self.current_key_index = wait_times.index(min_wait)
        
        key = self.api_keys[self.current_key_index]
        self.request_count[self.current_key_index] += 1
        return key
    
    def switch_key(self) -> Optional[str]:
        """Switch to the next available API key."""
        if len(self.api_keys) == 1:
            logger.warning("Only one API key available, cannot switch")
            return None
        
        original_index = self.current_key_index
        attempts = 0
        
        while attempts < len(self.api_keys):
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            attempts += 1
            
            # Check if this key is available (not in cooldown)
            if time.time() >= self.rate_limit_cooldown[self.current_key_index]:
                logger.info(f"🔄 Switched to API Key {self.current_key_index + 1}")
                return self.api_keys[self.current_key_index]
            
            if self.current_key_index == original_index:
                break
        
        return None
    
    def mark_rate_limited(self, cooldown_seconds: int = 60) -> Optional[str]:
        """Mark current key as rate limited and switch to another."""
        current_time = time.time()
        self.rate_limit_cooldown[self.current_key_index] = current_time + cooldown_seconds
        
        logger.warning(f"⚠️  Key {self.current_key_index + 1} hit rate limit. Cooldown: {cooldown_seconds}s")
        logger.info(f"📊 Key {self.current_key_index + 1} stats: {self.request_count[self.current_key_index]} requests made")
        
        # Try to switch to another key
        next_key = self.switch_key()
        
        if next_key:
            logger.info(f"✓ Switched to Key {self.current_key_index + 1}")
            return next_key
        else:
            logger.error("❌ All API keys are rate limited")
            return None
    
    def reset_counters(self):
        """Reset all counters (useful for testing or manual resets)."""
        self.request_count = {i: 0 for i in range(len(self.api_keys))}
        self.rate_limit_cooldown = {i: 0 for i in range(len(self.api_keys))}
        self.last_reset = time.time()
        self.current_key_index = 0
        logger.info("🔄 All counters reset")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about API key usage."""
        stats = {
            'current_key': self.current_key_index + 1,
            'total_keys': len(self.api_keys),
            'requests_per_key': self.request_count,
            'cooldown_status': {}
        }
        
        for i in range(len(self.api_keys)):
            remaining = self.rate_limit_cooldown[i] - time.time()
            stats['cooldown_status'][i + 1] = 'Available' if remaining <= 0 else f'Cooldown: {remaining:.1f}s'
        
        return stats

# Global API key manager instance
api_manager = APIKeyManager()

def make_api_call_with_retry(api_call_func: Callable, max_retries: int = 3, initial_delay: int = 2) -> Any:
    """
    Execute an API call with automatic retry and key rotation on rate limits.
    
    Args:
        api_call_func: Function that makes the API call (should accept client parameter)
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds between retries
    
    Returns:
        Result from the API call
    """
    delay = initial_delay
    
    for attempt in range(max_retries):
        try:
            # Get current API key and create client
            api_key = api_manager.get_current_key()
            client = Groq(api_key=api_key)
            
            # Make the API call
            logger.info(f"🔹 Attempt {attempt + 1}/{max_retries} with Key {api_manager.current_key_index + 1}")
            result = api_call_func(client)
            
            logger.info(f"✓ API call successful with Key {api_manager.current_key_index + 1}")
            return result
            
        except RateLimitError as e:
            logger.error(f"⚠️  Rate limit error: {str(e)}")
            
            # Mark key as rate limited and try to switch
            next_key = api_manager.mark_rate_limited(cooldown_seconds=60)
            
            if next_key is None and attempt < max_retries - 1:
                # All keys are rate limited, wait before retry
                logger.info(f"⏳ Waiting {delay} seconds before retry...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            elif next_key is None:
                raise Exception("❌ All API keys have reached their rate limits. Please wait before trying again.")
            
            if attempt == max_retries - 1:
                # Send alert when max retries reached
                try:
                    keys_status = api_manager.get_stats()['cooldown_status']
                    wait_times = [max(0, api_manager.rate_limit_cooldown[i] - time.time()) for i in range(len(api_manager.api_keys))]
                    min_wait = min(wait_times) if wait_times else 0
                    notifications.send_rate_limit_alert(keys_status, max_retries, min_wait)
                except Exception as email_err:
                    logger.error(f"Failed to send rate limit notification: {email_err}")
                raise Exception(f"❌ Max retries ({max_retries}) reached. All API keys are rate limited.")
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if it's a rate limit error by message content
            if "rate" in error_msg and "limit" in error_msg or "429" in error_msg:
                logger.error(f"⚠️  Rate limit detected in error message: {str(e)}")
                next_key = api_manager.mark_rate_limited(cooldown_seconds=60)
                
                if next_key is None and attempt < max_retries - 1:
                    logger.info(f"⏳ Waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    delay *= 2
                elif next_key is None:
                    raise Exception("❌ All API keys have reached their rate limits.")
                    
                if attempt == max_retries - 1:
                    # Send alert when max retries reached
                    try:
                        keys_status = api_manager.get_stats()['cooldown_status']
                        wait_times = [max(0, api_manager.rate_limit_cooldown[i] - time.time()) for i in range(len(api_manager.api_keys))]
                        min_wait = min(wait_times) if wait_times else 0
                        notifications.send_rate_limit_alert(keys_status, max_retries, min_wait)
                    except Exception as email_err:
                        logger.error(f"Failed to send rate limit notification: {email_err}")
                    raise Exception(f"❌ Max retries ({max_retries}) reached.")
            else:
                # Not a rate limit error, re-raise immediately
                logger.error(f"❌ API call failed: {str(e)}")
                raise
    
    raise Exception(f"❌ Failed after {max_retries} attempts")

# Legacy decorator for backward compatibility
def with_api_key_rotation(max_retries: int = 3):
    """Decorator to handle API key rotation and rate limits."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            def api_call(client):
                return func(*args, **kwargs, client=client)
            return make_api_call_with_retry(api_call, max_retries=max_retries)
        return wrapper
    return decorator