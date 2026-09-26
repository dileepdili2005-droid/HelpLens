import sqlite3
import json
import logging
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

def get_db_connection():
    """Establish connection to SQLite database with row dict factory."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite database tables if they do not exist."""
    if not Config.USE_DATABASE:
        return
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Table for storing user queries and generated AI solutions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assistance_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                problem_text TEXT NOT NULL,
                category TEXT DEFAULT 'General',
                urgency TEXT DEFAULT 'Standard',
                image_filename TEXT,
                ocr_text TEXT,
                ai_response_json TEXT NOT NULL,
                bookmarked INTEGER DEFAULT 0,
                feedback_rating INTEGER DEFAULT 0, -- 1 for thumbs up, -1 for thumbs down
                feedback_note TEXT DEFAULT ''
            )
        """)
        
        # Create helpful indexes for fast lookup and search
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_created_at ON assistance_history(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_category ON assistance_history(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_bookmarked ON assistance_history(bookmarked)")
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully at %s", Config.DATABASE_PATH)
    except Exception as e:
        logger.error("Error initializing database: %s", str(e))

def save_query(problem_text, category, urgency, image_filename, ocr_text, ai_response_dict):
    """Save a user query and resulting AI guidance to the database."""
    if not Config.USE_DATABASE:
        return None
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO assistance_history (
                problem_text, category, urgency, image_filename, ocr_text, ai_response_json
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            problem_text,
            category,
            urgency,
            image_filename,
            ocr_text or "",
            json.dumps(ai_response_dict)
        ))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return record_id
    except Exception as e:
        logger.error("Error saving query to database: %s", str(e))
        return None

def get_history(limit=20, offset=0, category=None, bookmarked_only=False, search_term=None):
    """Retrieve history records with optional filters, pagination, and text search."""
    if not Config.USE_DATABASE:
        return []
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM assistance_history WHERE 1=1"
        params = []
        
        if bookmarked_only:
            query += " AND bookmarked = 1"
            
        if category and category != "All":
            query += " AND category = ?"
            params.append(category)
            
        if search_term:
            query += " AND (problem_text LIKE ? OR ocr_text LIKE ? OR ai_response_json LIKE ?)"
            like_term = f"%{search_term}%"
            params.extend([like_term, like_term, like_term])
            
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            row_dict = dict(row)
            try:
                row_dict["ai_response"] = json.loads(row_dict["ai_response_json"])
            except Exception:
                row_dict["ai_response"] = {}
            results.append(row_dict)
            
        conn.close()
        return results
    except Exception as e:
        logger.error("Error fetching history: %s", str(e))
        return []

def get_query_by_id(record_id):
    """Retrieve a single history entry by its ID."""
    if not Config.USE_DATABASE:
        return None
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assistance_history WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            res = dict(row)
            try:
                res["ai_response"] = json.loads(res["ai_response_json"])
            except Exception:
                res["ai_response"] = {}
            return res
        return None
    except Exception as e:
        logger.error("Error getting query %s: %s", record_id, str(e))
        return None

def toggle_bookmark(record_id):
    """Toggle bookmark state (0 <-> 1) for a query record."""
    if not Config.USE_DATABASE:
        return False
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT bookmarked FROM assistance_history WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
            
        new_val = 0 if row["bookmarked"] == 1 else 1
        cursor.execute("UPDATE assistance_history SET bookmarked = ? WHERE id = ?", (new_val, record_id))
        conn.commit()
        conn.close()
        return bool(new_val)
    except Exception as e:
        logger.error("Error toggling bookmark: %s", str(e))
        return False

def submit_feedback(record_id, rating, note=""):
    """Submit user feedback (+1 or -1) and optional note for a solution."""
    if not Config.USE_DATABASE:
        return False
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE assistance_history 
            SET feedback_rating = ?, feedback_note = ? 
            WHERE id = ?
        """, (rating, note, record_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error("Error saving feedback: %s", str(e))
        return False

def delete_query(record_id):
    """Delete a specific history record."""
    if not Config.USE_DATABASE:
        return False
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM assistance_history WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error("Error deleting record %s: %s", record_id, str(e))
        return False

def clear_all_history():
    """Clear all history records from the database."""
    if not Config.USE_DATABASE:
        return False
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM assistance_history")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error("Error clearing history: %s", str(e))
        return False
