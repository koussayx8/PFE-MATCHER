import json
import sqlite3
from pathlib import Path
from datetime import datetime
from config.settings import CACHE_DIR, DATABASE_PATH

def migrate_cache():
    print(f"Starting migration from {CACHE_DIR} to {DATABASE_PATH}...")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Ensure table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            project_title TEXT,
            company TEXT,
            score INTEGER,
            recommendation TEXT,
            matching_points TEXT, -- JSON
            gaps TEXT, -- JSON
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    count = 0
    errors = 0
    
    for file_path in CACHE_DIR.glob("match_*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                match = json.load(f)
                
            # Check if already exists (simple check by project_id)
            cursor.execute("SELECT id FROM matches WHERE project_id = ?", (match.get("project_id"),))
            if cursor.fetchone():
                continue
                
            timestamp = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            cursor.execute("""
                INSERT INTO matches (
                    project_id, project_title, company, score, 
                    recommendation, matching_points, gaps, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match.get("project_id"),
                match.get("project_title"),
                match.get("company"),
                match.get("overall_score", 0),
                match.get("recommendation"),
                json.dumps(match.get("matching_points", [])),
                json.dumps(match.get("gaps", [])),
                timestamp
            ))
            count += 1
            
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")
            errors += 1
            
    conn.commit()
    conn.close()
    
    print(f"Migration complete! Imported {count} matches. Errors: {errors}")

if __name__ == "__main__":
    migrate_cache()
