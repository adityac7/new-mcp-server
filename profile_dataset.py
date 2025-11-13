#!/usr/bin/env python3
"""
Synchronous Dataset Profiling
Profiles a dataset schema without requiring Celery/Redis
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from app.database import get_db
from app.models import Dataset, DatasetSchema
from app.encryption import get_encryption_manager
import psycopg2


def profile_dataset_sync(dataset_id: int) -> dict:
    """
    Profile a dataset's schema synchronously

    Returns:
        dict with success status and stats
    """
    db = next(get_db())

    try:
        # Get dataset
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            return {"success": False, "error": "Dataset not found"}

        print(f"📊 Profiling dataset: {dataset.name}")

        # Decrypt connection string
        encryption_manager = get_encryption_manager()
        connection_string = encryption_manager.decrypt(dataset.connection_string_encrypted)

        # Fix postgres:// to postgresql://
        if connection_string.startswith('postgres://'):
            connection_string = connection_string.replace('postgres://', 'postgresql://', 1)

        # Connect to dataset database
        try:
            conn = psycopg2.connect(connection_string)
            cur = conn.cursor()
        except Exception as e:
            return {"success": False, "error": f"Connection failed: {str(e)}"}

        # Get all tables in public schema
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]

        if not tables:
            return {"success": False, "error": "No tables found in database"}

        print(f"   Found {len(tables)} tables")

        # Delete existing schema entries for this dataset
        db.query(DatasetSchema).filter(DatasetSchema.dataset_id == dataset_id).delete()
        db.commit()

        total_columns = 0

        # Profile each table
        for table_name in tables:
            # Get columns for this table
            cur.execute("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))

            columns = cur.fetchall()

            # Save schema entries
            for col_name, data_type, is_nullable in columns:
                schema_entry = DatasetSchema(
                    dataset_id=dataset_id,
                    table_name=table_name,
                    column_name=col_name,
                    data_type=data_type,
                    is_nullable=(is_nullable == 'YES')
                )
                db.add(schema_entry)
                total_columns += 1

            print(f"   ✓ {table_name}: {len(columns)} columns")

        # Commit all schema entries
        db.commit()

        # Close connection
        cur.close()
        conn.close()

        print(f"✅ Profiling complete: {len(tables)} tables, {total_columns} columns")

        return {
            "success": True,
            "tables": len(tables),
            "columns": total_columns,
            "table_names": tables
        }

    except Exception as e:
        print(f"❌ Profiling failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python profile_dataset.py <dataset_id>")
        print()
        print("Example: python profile_dataset.py 1")
        sys.exit(1)

    dataset_id = int(sys.argv[1])

    print(f"Starting dataset profiling for ID: {dataset_id}")
    print("=" * 60)

    result = profile_dataset_sync(dataset_id)

    print("=" * 60)

    if result["success"]:
        print(f"✅ SUCCESS")
        print(f"   Tables: {result['tables']}")
        print(f"   Columns: {result['columns']}")
    else:
        print(f"❌ FAILED")
        print(f"   Error: {result['error']}")
        sys.exit(1)
