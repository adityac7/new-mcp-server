"""
Migration: Add date_range and date_column to datasets table
"""
from app.database import get_db
from sqlalchemy import text

def migrate():
    """Add date_range and date_column columns to datasets table"""
    db = next(get_db())
    
    try:
        # Check if columns already exist
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'datasets' 
            AND column_name IN ('date_range', 'date_column')
        """))
        
        existing_columns = [row[0] for row in result.fetchall()]
        
        # Add date_range column if it doesn't exist
        if 'date_range' not in existing_columns:
            print("Adding date_range column...")
            db.execute(text("""
                ALTER TABLE datasets 
                ADD COLUMN date_range VARCHAR(100)
            """))
            print("✅ Added date_range column")
        else:
            print("✓ date_range column already exists")
        
        # Add date_column column if it doesn't exist
        if 'date_column' not in existing_columns:
            print("Adding date_column column...")
            db.execute(text("""
                ALTER TABLE datasets 
                ADD COLUMN date_column VARCHAR(100)
            """))
            print("✅ Added date_column column")
        else:
            print("✓ date_column column already exists")
        
        # Update digital_insights dataset with date information
        print("\nUpdating digital_insights dataset...")
        db.execute(text("""
            UPDATE datasets 
            SET date_range = 'Jan 2018 - Dec 2025',
                date_column = 'date'
            WHERE id = 1
        """))
        print("✅ Updated digital_insights with date range")
        
        db.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

