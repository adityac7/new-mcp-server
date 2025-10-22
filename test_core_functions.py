"""
Test core functions directly (bypassing MCP protocol)
This verifies the underlying logic works correctly
"""
import asyncio
import sys
from datetime import datetime

sys.path.insert(0, '/home/ubuntu/new-mcp-server')

from app.database import get_db
from app.models import Dataset
from app.encryption import get_encryption_manager
import psycopg2

def test_database_connection():
    """Test that we can connect to the metadata database"""
    print("\n" + "=" * 80)
    print("TEST 1: Database Connection")
    print("=" * 80)
    try:
        db = next(get_db())
        datasets = db.query(Dataset).all()
        print(f"✓ SUCCESS: Connected to database")
        print(f"  Found {len(datasets)} datasets")
        for ds in datasets:
            print(f"  - ID {ds.id}: {ds.name} (active: {ds.is_active})")
        db.close()
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_dataset_connection():
    """Test that we can connect to a dataset"""
    print("\n" + "=" * 80)
    print("TEST 2: Dataset Connection")
    print("=" * 80)
    try:
        db = next(get_db())
        dataset = db.query(Dataset).filter(Dataset.id == 1).first()
        
        if not dataset:
            print("✗ FAILED: Dataset ID 1 not found")
            db.close()
            return False
        
        encryption_manager = get_encryption_manager()
        connection_string = encryption_manager.decrypt(dataset.connection_string_encrypted)
        
        if connection_string.startswith('postgres://'):
            connection_string = connection_string.replace('postgres://', 'postgresql://', 1)
        
        # Test connection
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()
        
        # Test query
        cur.execute("SELECT COUNT(*) FROM digital_insights")
        count = cur.fetchone()[0]
        
        print(f"✓ SUCCESS: Connected to dataset '{dataset.name}'")
        print(f"  Total respondents: {count:,}")
        
        cur.close()
        conn.close()
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_schema_query():
    """Test that we can query the schema"""
    print("\n" + "=" * 80)
    print("TEST 3: Schema Query")
    print("=" * 80)
    try:
        db = next(get_db())
        dataset = db.query(Dataset).filter(Dataset.id == 1).first()
        
        encryption_manager = get_encryption_manager()
        connection_string = encryption_manager.decrypt(dataset.connection_string_encrypted)
        
        if connection_string.startswith('postgres://'):
            connection_string = connection_string.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()
        
        # Get tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]
        
        print(f"✓ SUCCESS: Found {len(tables)} tables")
        for table in tables:
            print(f"  - {table}")
        
        cur.close()
        conn.close()
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_weighted_query():
    """Test a weighted query"""
    print("\n" + "=" * 80)
    print("TEST 4: Weighted Query")
    print("=" * 80)
    try:
        db = next(get_db())
        dataset = db.query(Dataset).filter(Dataset.id == 1).first()
        
        encryption_manager = get_encryption_manager()
        connection_string = encryption_manager.decrypt(dataset.connection_string_encrypted)
        
        if connection_string.startswith('postgres://'):
            connection_string = connection_string.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()
        
        # Test weighted query
        cur.execute("""
            SELECT gender, COUNT(*) as count, SUM(weights) as weighted_count
            FROM digital_insights
            GROUP BY gender
            LIMIT 5
        """)
        
        results = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        
        print(f"✓ SUCCESS: Executed weighted query")
        print(f"  Columns: {columns}")
        print(f"  Results:")
        for row in results:
            print(f"    {row}")
        
        cur.close()
        conn.close()
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_metadata_table():
    """Test that metadata table exists and has the metadata_text column"""
    print("\n" + "=" * 80)
    print("TEST 5: Metadata Table Schema")
    print("=" * 80)
    try:
        db = next(get_db())
        
        from sqlalchemy import inspect
        inspector = inspect(db.bind)
        columns = inspector.get_columns('metadata')
        
        print(f"✓ SUCCESS: Metadata table exists")
        print(f"  Columns:")
        for col in columns:
            print(f"    - {col['name']}: {col['type']}")
        
        # Check for metadata_text column
        has_metadata_text = any(col['name'] == 'metadata_text' for col in columns)
        if has_metadata_text:
            print(f"  ✓ metadata_text column exists")
        else:
            print(f"  ✗ metadata_text column MISSING")
            return False
        
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def main():
    print("=" * 80)
    print("MCP ANALYTICS SERVER - CORE FUNCTION TEST")
    print("=" * 80)
    print(f"Test started at: {datetime.now()}")
    print()
    
    results = []
    
    results.append(("Database Connection", test_database_connection()))
    results.append(("Dataset Connection", test_dataset_connection()))
    results.append(("Schema Query", test_schema_query()))
    results.append(("Weighted Query", test_weighted_query()))
    results.append(("Metadata Table", test_metadata_table()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed
    
    print(f"Total tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()
    
    for name, result in results:
        status_icon = "✓" if result else "✗"
        status_text = "PASS" if result else "FAIL"
        print(f"{status_icon} {name}: {status_text}")
    
    print("\n" + "=" * 80)
    print(f"Test completed at: {datetime.now()}")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

