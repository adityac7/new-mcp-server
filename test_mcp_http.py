"""
Test MCP tools via HTTP/SSE endpoint
This simulates how ChatGPT would call the MCP server
"""
import requests
import json
from datetime import datetime

# MCP endpoint
MCP_URL = "http://localhost:8000/mcp"

def call_mcp_tool(tool_name: str, arguments: dict = None):
    """Call an MCP tool via HTTP POST"""
    if arguments is None:
        arguments = {}
    
    # MCP protocol request format
    request_data = {
        "jsonrpc": "2.0",
        "id": f"test-{tool_name}",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    try:
        response = requests.post(
            MCP_URL,
            json=request_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    print("=" * 80)
    print("MCP ANALYTICS SERVER - HTTP ENDPOINT TEST")
    print("=" * 80)
    print(f"Test started at: {datetime.now()}")
    print(f"Endpoint: {MCP_URL}")
    print()
    
    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }
    
    # Test 1: list_available_datasets
    print("\n" + "=" * 80)
    print("TEST 1: list_available_datasets()")
    print("=" * 80)
    result = call_mcp_tool("list_available_datasets")
    if result["success"]:
        print("✓ SUCCESS")
        print(f"Response: {json.dumps(result['data'], indent=2)[:500]}...")
        results["passed"] += 1
        results["tests"].append({"name": "list_available_datasets", "status": "PASS"})
    else:
        print(f"✗ FAILED: {result['error']}")
        results["failed"] += 1
        results["tests"].append({"name": "list_available_datasets", "status": "FAIL", "error": result['error']})
    
    # Test 2: get_dataset_schema
    print("\n" + "=" * 80)
    print("TEST 2: get_dataset_schema(dataset_id=1)")
    print("=" * 80)
    result = call_mcp_tool("get_dataset_schema", {"dataset_id": 1})
    if result["success"]:
        print("✓ SUCCESS")
        print(f"Response: {json.dumps(result['data'], indent=2)[:500]}...")
        results["passed"] += 1
        results["tests"].append({"name": "get_dataset_schema", "status": "PASS"})
    else:
        print(f"✗ FAILED: {result['error']}")
        results["failed"] += 1
        results["tests"].append({"name": "get_dataset_schema", "status": "FAIL", "error": result['error']})
    
    # Test 3: get_context (level 0)
    print("\n" + "=" * 80)
    print("TEST 3: get_context(level=0)")
    print("=" * 80)
    result = call_mcp_tool("get_context", {"level": 0})
    if result["success"]:
        print("✓ SUCCESS")
        print(f"Response: {json.dumps(result['data'], indent=2)[:500]}...")
        results["passed"] += 1
        results["tests"].append({"name": "get_context_level_0", "status": "PASS"})
    else:
        print(f"✗ FAILED: {result['error']}")
        results["failed"] += 1
        results["tests"].append({"name": "get_context_level_0", "status": "FAIL", "error": result['error']})
    
    # Test 4: get_dataset_sample
    print("\n" + "=" * 80)
    print("TEST 4: get_dataset_sample(dataset_id=1, table_name='respondents', limit=5)")
    print("=" * 80)
    result = call_mcp_tool("get_dataset_sample", {
        "dataset_id": 1,
        "table_name": "respondents",
        "limit": 5
    })
    if result["success"]:
        print("✓ SUCCESS")
        print(f"Response: {json.dumps(result['data'], indent=2)[:500]}...")
        results["passed"] += 1
        results["tests"].append({"name": "get_dataset_sample", "status": "PASS"})
    else:
        print(f"✗ FAILED: {result['error']}")
        results["failed"] += 1
        results["tests"].append({"name": "get_dataset_sample", "status": "FAIL", "error": result['error']})
    
    # Test 5: query_dataset (simple count)
    print("\n" + "=" * 80)
    print("TEST 5: query_dataset(dataset_id=1, query='SELECT COUNT(*) as total FROM respondents')")
    print("=" * 80)
    result = call_mcp_tool("query_dataset", {
        "dataset_id": 1,
        "query": "SELECT COUNT(*) as total FROM respondents",
        "apply_weights": False
    })
    if result["success"]:
        print("✓ SUCCESS")
        print(f"Response: {json.dumps(result['data'], indent=2)[:500]}...")
        results["passed"] += 1
        results["tests"].append({"name": "query_dataset_count", "status": "PASS"})
    else:
        print(f"✗ FAILED: {result['error']}")
        results["failed"] += 1
        results["tests"].append({"name": "query_dataset_count", "status": "FAIL", "error": result['error']})
    
    # Test 6: execute_multi_query
    print("\n" + "=" * 80)
    print("TEST 6: execute_multi_query with 2 queries")
    print("=" * 80)
    result = call_mcp_tool("execute_multi_query", {
        "queries": [
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
        ],
        "apply_weights": False
    })
    if result["success"]:
        print("✓ SUCCESS")
        print(f"Response: {json.dumps(result['data'], indent=2)[:500]}...")
        results["passed"] += 1
        results["tests"].append({"name": "execute_multi_query", "status": "PASS"})
    else:
        print(f"✗ FAILED: {result['error']}")
        results["failed"] += 1
        results["tests"].append({"name": "execute_multi_query", "status": "FAIL", "error": result['error']})
    
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
    results = main()
    exit(0 if results["failed"] == 0 else 1)

