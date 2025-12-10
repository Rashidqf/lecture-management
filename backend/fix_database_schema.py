"""
Database Schema Fix Script
This script fixes the course_id NOT NULL constraint issue in the broadcasts table.
Run this once to fix your database schema.
"""
import sqlite3
import os
import shutil
from datetime import datetime

def fix_broadcasts_table_schema(db_path):
    """Fix the broadcasts table to allow NULL course_id"""
    
    # Backup database first
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        # Step 1: Create new table with correct schema
        cursor.execute("""
            CREATE TABLE broadcasts_new (
                id INTEGER PRIMARY KEY,
                teacher_id INTEGER NOT NULL,
                course_id INTEGER,
                lecture_topic VARCHAR(200) NOT NULL,
                course_title VARCHAR(200) NOT NULL,
                broadcast_url VARCHAR(500) UNIQUE,
                status VARCHAR(20) DEFAULT 'active',
                started_at DATETIME,
                ended_at DATETIME,
                audio_file_path VARCHAR(500),
                FOREIGN KEY(teacher_id) REFERENCES users(id),
                FOREIGN KEY(course_id) REFERENCES courses(id)
            )
        """)
        
        # Step 2: Copy data from old table (handle NULL course_id)
        cursor.execute("""
            INSERT INTO broadcasts_new 
            (id, teacher_id, course_id, lecture_topic, course_title, broadcast_url, 
             status, started_at, ended_at, audio_file_path)
            SELECT 
                id, teacher_id, 
                CASE WHEN course_id = 0 THEN NULL ELSE course_id END as course_id,
                lecture_topic, course_title, broadcast_url, 
                status, started_at, ended_at, audio_file_path
            FROM broadcasts
        """)
        
        # Step 3: Drop old table
        cursor.execute("DROP TABLE broadcasts")
        
        # Step 4: Rename new table
        cursor.execute("ALTER TABLE broadcasts_new RENAME TO broadcasts")
        
        conn.commit()
        print("✓ Database schema fixed successfully!")
        print("  course_id column now allows NULL values")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error fixing schema: {e}")
        print(f"  Restore from backup: {backup_path}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    # Find the database file
    db_paths = [
        "instance/VirtualClassroom.sqlite3",
        "../instance/VirtualClassroom.sqlite3",
        "VirtualClassroom.sqlite3"
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("✗ Database file not found. Please specify the path.")
        print("  Expected locations:")
        for path in db_paths:
            print(f"    - {path}")
    else:
        print(f"Found database: {db_path}")
        response = input("This will modify your database. Continue? (yes/no): ")
        if response.lower() == 'yes':
            fix_broadcasts_table_schema(db_path)
        else:
            print("Cancelled.")

