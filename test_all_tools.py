"""
Comprehensive test script for all 6 MCP tools
Tests the local server with public URL
"""
import asyncio
import asyncpg
import json
from datetime import datetime

# Database connection
DATABASE_URL = "postgresql://analytics_db_clug_user:sa1jEkjEmuIKRxQu3x6Oa83Ep4AWGSAM@dpg-d3pmmtali9vc73bn81i0-a.singapore-postgres.render.com/analytics_db_clug"

async def test_all_tools():
    """Test all 6 MCP tools by calling them directly"""
    
    print("=" * 80)
    print("MCP ANALYTICS SERVER - COMPREHENSIVE TOOL TEST")
    print("=" * 80)
    print(f"Test started at: {datetime.now()}")
    print()
    
    # Import the tools from server.py
    import sys
    sys.path.insert(0, '/home/ubuntu/new-mcp-server')
    
    # We'll test the tools by importing and calling them directly
    from server import (
        list_available_datasets,
        get_dataset_schema,
        query_dataset,
        get_dataset_sample,
        get_context,
        execute_multi_query
    )
    
    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }
    
    # Test 1: list_available_datasets
    print("\n" + "=" * 80)
    print("TEST 1: list_available_datasets()")
    print("=" * 80)
    try:
        result = await list_available_datasets()
        print("✓ SUCCESS")
        print(f"Result preview: {str(result)[:500]}...")
        results["passed"] += 1
        results["tests"].append({"name": "list_available_datasets", "status": "PASS"})
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "list_available_datasets", "status": "FAIL", "error": str(e)})
    
    # Test 2: get_dataset_schema
    print("\n" + "=" * 80)
    print("TEST 2: get_dataset_schema(dataset_id=1)")
    print("=" * 80)
    try:
        result = await get_dataset_schema(dataset_id=1)
        print("✓ SUCCESS")
        print(f"Result preview: {str(result)[:500]}...")
        results["passed"] += 1
        results["tests"].append({"name": "get_dataset_schema", "status": "PASS"})
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "get_dataset_schema", "status": "FAIL", "error": str(e)})
    
    # Test 3: get_context (level 0)
    print("\n" + "=" * 80)
    print("TEST 3: get_context(level=0)")
    print("=" * 80)
    try:
        result = await get_context(level=0)
        print("✓ SUCCESS")
        print(f"Result preview: {str(result)[:500]}...")
        results["passed"] += 1
        results["tests"].append({"name": "get_context_level_0", "status": "PASS"})
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "get_context_level_0", "status": "FAIL", "error": str(e)})
    
    # Test 4: get_context (level 2 with dataset_id)
    print("\n" + "=" * 80)
    print("TEST 4: get_context(level=2, dataset_id=1)")
    print("=" * 80)
    try:
        result = await get_context(level=2, dataset_id=1)
        print("✓ SUCCESS")
        print(f"Result preview: {str(result)[:500]}...")
        results["passed"] += 1
        results["tests"].append({"name": "get_context_level_2", "status": "PASS"})
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "get_context_level_2", "status": "FAIL", "error": str(e)})
    
    # Test 5: get_dataset_sample
    print("\n" + "=" * 80)
    print("TEST 5: get_dataset_sample(dataset_id=1, table_name='respondents', limit=5)")
    print("=" * 80)
    try:
        result = await get_dataset_sample(dataset_id=1, table_name="respondents", limit=5)
        print("✓ SUCCESS")
        print(f"Result preview: {str(result)[:500]}...")
        results["passed"] += 1
        results["tests"].append({"name": "get_dataset_sample", "status": "PASS"})
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "get_dataset_sample", "status": "FAIL", "error": str(e)})
    
    # Test 6: query_dataset (simple count)
    print("\n" + "=" * 80)
    print("TEST 6: query_dataset(dataset_id=1, query='SELECT COUNT(*) as total FROM respondents')")
    print("=" * 80)
    try:
        result = await query_dataset(
            dataset_id=1,
            query="SELECT COUNT(*) as total FROM respondents",
            apply_weights=False
        )
        print("✓ SUCCESS")
        print(f"Result preview: {str(result)[:500]}...")
        results["passed"] += 1
        results["tests"].append({"name": "query_dataset_count", "status": "PASS"})
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "query_dataset_count", "status": "FAIL", "error": str(e)})
    
    # Test 7: query_dataset with weighting
    print("\n" + "=" * 80)
    print("TEST 7: query_dataset with apply_weights=True")
    print("=" * 80)
    try:
        result = await query_dataset(
            dataset_id=1,
            query="SELECT gender, COUNT(*) as count FROM respondents GROUP BY gender LIMIT 5",
            apply_weights=True
        )
        print("✓ SUCCESS")
        print(f"Result preview: {str(result)[:500]}...")
        results["passed"] += 1
        results["tests"].append({"name": "query_dataset_weighted", "status": "PASS"})
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "query_dataset_weighted", "status": "FAIL", "error": str(e)})
    
    # Test 8: execute_multi_query
    print("\n" + "=" * 80)
    print("TEST 8: execute_multi_query with 2 queries")
    print("=" * 80)
    try:
        queries = [
            {
                "dataset_id": 1,
                "query": "SELECT COUNT(*) as total_respondents FROM respondents",
                "label": "Total Respondents"
            },
            {
                "dataset_id": 1,
                "query": "SELECT gender, COUNT(*) as count FROM respondents GROUP BY gender LIMIT 3",
                "label": "Gender Distribution"
            }
        ]
        result = await execute_multi_query(queries=queries, apply_weights=False)
        print("✓ SUCCESS")
        print(f"Result preview: {str(result)[:500]}...")
        results["passed"] += 1
        results["tests"].append({"name": "execute_multi_query", "status": "PASS"})
    except Exception as e:
        print(f"✗ FAILED: {e}")
        results["failed"] += 1
        results["tests"].append({"name": "execute_multi_query", "status": "FAIL", "error": str(e)})
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {results['passed'] + results['failed']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print()
    
    for test in results["tests"]:
        status_icon = "✓" if test["status"] == "PASS" else "✗"
        print(f"{status_icon} {test['name']}: {test['status']}")
        if "error" in test:
            print(f"  Error: {test['error']}")
    
    print("\n" + "=" * 80)
    print(f"Test completed at: {datetime.now()}")
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_all_tools())
    exit(0 if results["failed"] == 0 else 1)

