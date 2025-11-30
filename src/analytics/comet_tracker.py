import logging
import os
from typing import Dict, Any, List
from config.settings import COMET_API_KEY, COMET_PROJECT_NAME, COMET_WORKSPACE

logger = logging.getLogger(__name__)

class CometTracker:
    def __init__(self):
        self.experiment = None
        self.disabled = False
        
        if not COMET_API_KEY:
            logger.info("Comet API key not found. Analytics disabled.")
            self.disabled = True
            return

        if not COMET_WORKSPACE:
            logger.warning("Comet Workspace not configured. Analytics disabled.")
            self.disabled = True
            return
            
        try:
            from comet_ml import Experiment
            self.experiment = Experiment(
                api_key=COMET_API_KEY,
                project_name=COMET_PROJECT_NAME,
                workspace=COMET_WORKSPACE,
                auto_output_logging="simple"
            )
            logger.info("Comet ML initialized successfully.")
        except ImportError:
            logger.warning("comet_ml not installed. Analytics disabled.")
            self.disabled = True
        except Exception as e:
            logger.error(f"Failed to initialize Comet: {e}")
            self.disabled = True

    def log_match(self, project: Dict[str, Any], match_data: Dict[str, Any]):
        if self.disabled or not self.experiment:
            return
            
        try:
            self.experiment.log_metric("match_score", match_data.get("overall_score", 0))
            self.experiment.log_parameter("company", project.get("company"))
            self.experiment.log_text(match_data.get("recommendation", ""))
        except Exception:
            pass

    def log_cv_analysis(self, cv_data: Dict[str, Any]):
        if self.disabled or not self.experiment:
            return
        
        try:
            skills = cv_data.get("skills", {})
            self.experiment.log_parameter("skill_count", len(skills.get("technical", [])))
            self.experiment.log_text(str(cv_data.get("domains_of_interest", [])))
        except Exception:
            pass

    def log_email_sent(self, project: Dict[str, Any], success: bool):
        if self.disabled or not self.experiment:
            return
            
        try:
            self.experiment.log_metric("email_sent_success", 1 if success else 0)
        except Exception:
            pass

    def log_response_received(self, project: Dict[str, Any], days: int):
        if self.disabled or not self.experiment:
            return
            
        try:
            self.experiment.log_metric("response_received", 1)
            self.experiment.log_metric("days_to_response", days)
        except Exception:
            pass

    def log_batch_metrics(self, matches: List[Dict[str, Any]]):
        if self.disabled or not self.experiment:
            return
            
        try:
            scores = [m.get("overall_score", 0) for m in matches]
            if scores:
                avg_score = sum(scores) / len(scores)
                self.experiment.log_metric("batch_avg_score", avg_score)
                self.experiment.log_metric("batch_max_score", max(scores))
        except Exception:
            pass
