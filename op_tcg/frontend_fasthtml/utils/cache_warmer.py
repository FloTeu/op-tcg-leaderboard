import logging
import os
from typing import List, Callable, Any
from concurrent.futures import ThreadPoolExecutor
import threading
import time

from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend_fasthtml.utils.extract import (
    get_all_tournament_decklist_data, get_leader_data, get_leader_extended, get_card_popularity_data,
    get_all_tournament_extened_data, get_card_data, get_card_types, get_leader_win_rate
)

logger = logging.getLogger(__name__)

class CacheWarmer:
    """Background cache warmer that pre-loads frequently accessed data"""
    
    def __init__(self, warm_interval_hours: float | None = None):
        # Get interval from environment variable or use default
        if warm_interval_hours is None:
            warm_interval_hours = float(os.environ.get("CACHE_WARM_INTERVAL_HOURS", "3.0"))
        
        self.warm_interval_hours = warm_interval_hours
        self.warm_interval_seconds = warm_interval_hours * 3600
        self.is_running = False
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cache_warmer")
        self._stop_event = threading.Event()
        
        logger.info(f"Cache warmer initialized with {self.warm_interval_hours}h interval")
        
    def get_cache_warming_tasks(self) -> List[Callable[[], Any]]:
        """Define all the cache warming tasks to run"""
        return [
            # Static data - warm every cycle
            lambda: get_leader_data(),
            lambda: get_card_data(), 
            lambda: get_card_popularity_data(),
            lambda: get_card_types(),
            lambda: get_all_tournament_decklist_data(),
            
            # Meta-specific data
            lambda: get_leader_extended(),
            lambda: get_all_tournament_extened_data(),
            
            # Per meta format data
            *[lambda mf=meta_format: get_leader_win_rate([mf]) 
              for meta_format in MetaFormat.to_list()],
        ]
    
    def warm_cache_sync(self) -> None:
        """Synchronously warm the cache with all defined tasks"""
        tasks = self.get_cache_warming_tasks()
        start_time = time.time()
        
        logger.info(f"Starting cache warming cycle - {len(tasks)} tasks")
        
        successful_tasks = 0
        failed_tasks = 0
        
        for i, task in enumerate(tasks):
            if self._stop_event.is_set():
                logger.info("Cache warming stopped early")
                break
                
            try:
                task_start = time.time()
                result = task()
                task_duration = time.time() - task_start
                
                # Log task completion (with result size if it's a list)
                result_info = f"{len(result)} items" if isinstance(result, list) else "completed"
                logger.debug(f"Task {i+1}/{len(tasks)} completed in {task_duration:.2f}s: {result_info}")
                successful_tasks += 1
                
            except Exception as e:
                logger.error(f"Cache warming task {i+1}/{len(tasks)} failed: {e}")
                failed_tasks += 1
        
        total_duration = time.time() - start_time
        logger.info(f"Cache warming cycle completed in {total_duration:.2f}s - Success: {successful_tasks}, Failed: {failed_tasks}")
    
    def start_background_warming(self) -> None:
        """Start the background cache warming process"""
        if self.is_running:
            logger.warning("Cache warmer is already running")
            return
        
        self.is_running = True
        self._stop_event.clear()
        
        def background_loop():
            logger.info(f"Cache warmer started - warming every {self.warm_interval_hours} hours")
            
            # Initial warm-up on startup
            try:
                self.warm_cache_sync()
            except Exception as e:
                logger.error(f"Initial cache warming failed: {e}")
            
            # Continuous warming loop
            while not self._stop_event.is_set():
                try:
                    # Wait for the specified interval or until stop is requested
                    if self._stop_event.wait(timeout=self.warm_interval_seconds):
                        break  # Stop event was set
                    
                    self.warm_cache_sync()
                    
                except Exception as e:
                    logger.error(f"Background cache warming failed: {e}")
                    # Continue the loop even if warming fails
        
        # Start the background thread
        self.executor.submit(background_loop)
        logger.info("Background cache warming thread started")
    
    def stop_background_warming(self) -> None:
        """Stop the background cache warming process"""
        if not self.is_running:
            return
        
        logger.info("Stopping cache warmer...")
        self._stop_event.set()
        self.is_running = False
        
        # Shutdown executor with a timeout
        self.executor.shutdown(wait=True, timeout=30)
        logger.info("Cache warmer stopped")
    
    def warm_cache_now(self) -> None:
        """Immediately warm the cache (can be called manually)"""
        if self.is_running:
            # Run warming in the background executor
            future = self.executor.submit(self.warm_cache_sync)
            logger.info("Manual cache warming initiated")
            return future
        else:
            # Run synchronously if background warmer isn't running
            self.warm_cache_sync()

# Global cache warmer instance
_cache_warmer: CacheWarmer | None = None

def get_cache_warmer() -> CacheWarmer:
    """Get the global cache warmer instance"""
    global _cache_warmer
    if _cache_warmer is None:
        _cache_warmer = CacheWarmer()
    return _cache_warmer

def start_cache_warming() -> None:
    """Start background cache warming"""
    warmer = get_cache_warmer()
    warmer.start_background_warming()

def stop_cache_warming() -> None:
    """Stop background cache warming"""
    warmer = get_cache_warmer()
    warmer.stop_background_warming()

def warm_cache_now() -> None:
    """Manually trigger cache warming"""
    warmer = get_cache_warmer()
    warmer.warm_cache_now() 