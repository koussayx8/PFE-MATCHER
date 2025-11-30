import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from config.settings import DATABASE_PATH

logger = logging.getLogger(__name__)

def get_connection():
    return sqlite3.connect(DATABASE_PATH)

def init_database():
    """Initialize the SQLite database with required tables."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Applications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT,
                project_title TEXT,
                company TEXT,
                match_score INTEGER,
                status TEXT DEFAULT 'pending', -- pending, queued, sent, responded, rejected
                sent_at TIMESTAMP,
                response_at TIMESTAMP,
                notes TEXT,
                email_subject TEXT,
                email_body TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

def log_application(project: Dict[str, Any], match_data: Dict[str, Any], email_data: Dict[str, Any], status: str = "pending"):
    """Log a new application or update existing."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO applications (
                project_id, project_title, company, match_score, status, 
                sent_at, email_subject, email_body
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project.get("id"),
            project.get("title"),
            project.get("company"),
            match_data.get("overall_score", 0),
            status,
            datetime.now() if status == "sent" else None,
            email_data.get("subject"),
            email_data.get("body")
        ))
        
        conn.commit()
        conn.close()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Failed to log application: {e}")
        return None

def update_application_status(app_id: int, status: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        updates = ["status = ?"]
        params = [status]
        
        if status == "sent":
            updates.append("sent_at = ?")
            params.append(datetime.now())
        elif status == "responded":
            updates.append("response_at = ?")
            params.append(datetime.now())
            
        params.append(app_id)
        
        cursor.execute(f"UPDATE applications SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to update application {app_id}: {e}")

def get_application_history(limit: int = 100) -> List[Dict[str, Any]]:
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM applications ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        return []

def get_statistics() -> Dict[str, Any]:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        cursor.execute("SELECT COUNT(*) FROM applications")
        stats["total_applications"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM applications WHERE status = 'sent'")
        stats["sent_emails"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM applications WHERE status = 'responded'")
        stats["responses"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(match_score) FROM applications")
        avg = cursor.fetchone()[0]
        stats["avg_match_score"] = round(avg, 1) if avg else 0
        
        conn.close()
        return stats
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {}
