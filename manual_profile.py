"""
Manual Schema Profiling Script
Run this to profile a dataset without Celery/Redis
"""

import sys
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Dataset, DatasetSchema
from app.encryption import get_encryption_manager
from app.database import get_db
import os
from dotenv import load_dotenv

load_dotenv()

def profile_dataset(dataset_id: int):
    """Profile a dataset's schema manually"""

    # Get database session
    db = next(get_db())

    # Get dataset
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        print(f"❌ Dataset {dataset_id} not found")
        return

    print(f"📊 Profiling dataset: {dataset.name} (ID: {dataset_id})")

    # Decrypt connection string
    encryption_manager = get_encryption_manager()
    connection_string = encryption_manager.decrypt(dataset.connection_string_encrypted)

    print(f"🔗 Connecting to database...")

    try:
        # Connect to user database
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """)
        tables = cursor.fetchall()

        print(f"✅ Found {len(tables)} tables")

        total_columns = 0

        for (table_name,) in tables:
            print(f"  📋 Profiling table: {table_name}")

            # Get columns for this table
            cursor.execute("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))

            columns = cursor.fetchall()

            for column_name, data_type, is_nullable in columns:
                # Check if already exists
                existing = db.query(DatasetSchema).filter(
                    DatasetSchema.dataset_id == dataset_id,
                    DatasetSchema.table_name == table_name,
                    DatasetSchema.column_name == column_name
                ).first()

                if not existing:
                    schema = DatasetSchema(
                        dataset_id=dataset_id,
                        table_name=table_name,
                        column_name=column_name,
                        data_type=data_type,
                        is_nullable=(is_nullable == 'YES')
                    )
                    db.add(schema)
                    total_columns += 1

        db.commit()

        cursor.close()
        conn.close()

        print(f"✅ Profiled {total_columns} columns successfully!")
        print(f"🎉 Dataset '{dataset.name}' is now ready!")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 manual_profile.py <dataset_id>")
        print("\nAvailable datasets:")
        db = next(get_db())
        datasets = db.query(Dataset).all()
        for d in datasets:
            print(f"  ID {d.id}: {d.name}")
        sys.exit(1)

    dataset_id = int(sys.argv[1])
    profile_dataset(dataset_id)
