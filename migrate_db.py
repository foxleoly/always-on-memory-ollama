#!/usr/bin/env python3
"""
Database Migration Script for Always-On Memory Agent

Adds user isolation and authentication tables to the database.
"""

import sqlite3
import uuid
from datetime import datetime

DB_PATH = "memory.db"

def migrate_database():
    """Perform database migration to add user isolation and authentication."""
    print("🔍 Starting database migration...")
    
    db = sqlite3.connect(DB_PATH)
    cursor = db.cursor()
    
    # Check if user_id column exists in memories table
    cursor.execute("PRAGMA table_info(memories)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'user_id' not in columns:
        print(".AddColumn: Adding user_id to memories table")
        cursor.execute("ALTER TABLE memories ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default'")
    else:
        print("✓ Column user_id already exists in memories table")
    
    if 'is_shared' not in columns:
        print(".AddColumn: Adding is_shared to memories table")
        cursor.execute("ALTER TABLE memories ADD COLUMN is_shared INTEGER NOT NULL DEFAULT 0")
    else:
        print("✓ Column is_shared already exists in memories table")
    
    # Create users table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    print("✓ Users table created/verified")
    
    # Commit changes
    db.commit()
    db.close()
    
    print("✅ Database migration completed successfully!")

if __name__ == "__main__":
    migrate_database()