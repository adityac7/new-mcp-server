"""
Migration script to add metadata_text column to metadata table
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

engine = create_engine(DATABASE_URL)

def migrate():
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'metadata' AND column_name = 'metadata_text'
        """))
        
        if result.fetchone():
            print("✓ metadata_text column already exists")
            return
        
        # Add the column
        print("Adding metadata_text column...")
        conn.execute(text("""
            ALTER TABLE metadata 
            ADD COLUMN metadata_text TEXT
        """))
        conn.commit()
        print("✓ Successfully added metadata_text column")

if __name__ == '__main__':
    migrate()
