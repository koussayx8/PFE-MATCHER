import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Callable
from pathlib import Path

from config.settings import MAX_EMAILS_PER_DAY, RATE_LIMIT_REQUESTS_PER_MINUTE, DATA_DIR
from src.email_automation.gmail_sender import send_email

logger = logging.getLogger(__name__)

class EmailQueue:
    def __init__(self):
        self.queue: List[Dict[str, Any]] = []
        self.stats_file = DATA_DIR / "email_stats.json"
        self._load_stats()

    def _load_stats(self):
        self.stats = {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0}
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    if data.get("date") == self.stats["date"]:
                        self.stats = data
            except Exception:
                pass

    def _save_stats(self):
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f)
        except Exception as e:
            logger.error(f"Failed to save email stats: {e}")

    def add_to_queue(self, email_data: Dict[str, Any]):
        """
        Add an email to the queue.
        email_data must contain: to_email, subject, body, project_id
        """
        self.queue.append(email_data)
        logger.info(f"Added email to queue. Queue size: {len(self.queue)}")

    def remove_from_queue(self, index: int):
        if 0 <= index < len(self.queue):
            self.queue.pop(index)

    def process_queue(self, service, progress_callback: Callable[[int, int], None] = None) -> List[Dict[str, Any]]:
        """
        Process the email queue with rate limiting.
        
        Args:
            service: Gmail service.
            progress_callback: Function(current, total) to update UI.
            
        Returns:
            List[Dict]: Results of sending.
        """
        results = []
        total = len(self.queue)
        sent_count = 0
        
        # Calculate delay based on rate limit (e.g. 60/min -> 1 sec delay)
        # Add a buffer, say 2 seconds
        delay = 60 / RATE_LIMIT_REQUESTS_PER_MINUTE + 1
        
        logger.info(f"Processing queue of {total} emails...")
        
        # Create a copy to iterate so we can modify queue if needed (or just clear it at end)
        # We'll consume the queue
        while self.queue:
            if self.stats["count"] >= MAX_EMAILS_PER_DAY:
                logger.warning("Daily email limit reached!")
                break
                
            email_data = self.queue.pop(0)
            sent_count += 1
            
            result = send_email(
                service, 
                email_data["to_email"], 
                email_data["subject"], 
                email_data["body"]
            )
            
            # Add context
            result["project_id"] = email_data.get("project_id")
            result["to_email"] = email_data["to_email"]
            results.append(result)
            
            if result["success"]:
                self.stats["count"] += 1
                self._save_stats()
            
            if progress_callback:
                progress_callback(sent_count, total)
                
            # Rate limiting delay
            if self.queue: # Only sleep if there are more emails
                time.sleep(delay)
                
        return results

    def get_queue_status(self) -> Dict[str, Any]:
        return {
            "queue_size": len(self.queue),
            "sent_today": self.stats["count"],
            "remaining_today": MAX_EMAILS_PER_DAY - self.stats["count"]
        }
