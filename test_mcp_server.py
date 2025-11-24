#!/usr/bin/env python3
"""
Test the KiCAD MCP Server via stdio to verify schematic DSL tools work through MCP protocol
"""
import subprocess
import json
import sys
import time

PROJECT_PATH = r"C:\Users\geoff\Desktop\projects\kicad-astro-daughterboard2\Astro-DB_rev00005"

def send_request(proc, request):
    """Send JSON-RPC request to server"""
    req_json = json.dumps(request)
    proc.stdin.write(req_json + '\n')
    proc.stdin.flush()

def read_response(proc, timeout=30):
    """Read JSON-RPC response from server"""
    start = time.time()
    while time.time() - start < timeout:
        line = proc.stdout.readline()
        if line:
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    raise TimeoutError(f"No response after {timeout}s")

def test_mcp_tools():
    """Test schematic DSL tools via MCP protocol"""
    print("=" * 80)
    print("TESTING KICAD MCP SERVER - SCHEMATIC DSL TOOLS")
    print("=" * 80)

    # Start the server
    print("\n[1/5] Starting MCP server...")
    server_script = r"C:\Users\geoff\Desktop\projects\KiCAD-MCP-Server\dist\index.js"

    proc = subprocess.Popen(
        ["node", server_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env={
            "PYTHONPATH": "C:\\Program Files\\KiCad\\9.0\\lib\\python3\\dist-packages",
            "LOG_LEVEL": "error"  # Reduce noise
        }
    )

    try:
        time.sleep(2)  # Wait for server to start

        # 1. Initialize
        print("[2/5] Initializing MCP connection...")
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        })

        init_response = read_response(proc, timeout=10)
        if "error" in init_response:
            print(f"[ERROR] Initialize failed: {init_response['error']}")
            return False
        print("[OK] Server initialized")

        # 2. List tools
        print("[3/5] Listing available tools...")
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        })

        tools_response = read_response(proc, timeout=10)
        if "error" in tools_response:
            print(f"[ERROR] tools/list failed: {tools_response['error']}")
            return False

        tools = tools_response.get("result", {}).get("tools", [])
        tool_names = [t["name"] for t in tools]

        # Check if our new tools are present
        dsl_tools = ["get_schematic_index", "get_schematic_page", "get_schematic_context"]
        found_tools = [t for t in dsl_tools if t in tool_names]

        print(f"[OK] Found {len(tools)} total tools")
        print(f"     Schematic DSL tools: {found_tools}")

        if len(found_tools) != 3:
            print(f"[ERROR] Missing DSL tools! Expected 3, found {len(found_tools)}")
            return False

        # 3. Test get_schematic_index
        print("[4/5] Testing get_schematic_index...")
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_schematic_index",
                "arguments": {
                    "project_path": PROJECT_PATH
                }
            }
        })

        index_response = read_response(proc, timeout=60)
        if "error" in index_response:
            print(f"[ERROR] get_schematic_index failed: {index_response['error']}")
            return False

        result = index_response.get("result", {})
        content = result.get("content", [])
        if content and len(content) > 0:
            text = content[0].get("text", "")
            if "Astro_Connectors1" in text and "battery_charger" in text:
                print("[OK] get_schematic_index returned valid data")
                print(f"     Preview: {text[:100]}...")
            else:
                print("[ERROR] Unexpected response format")
                return False
        else:
            print("[ERROR] No content in response")
            return False

        # 4. Test get_schematic_page
        print("[5/5] Testing get_schematic_page...")
        send_request(proc, {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "get_schematic_page",
                "arguments": {
                    "project_path": PROJECT_PATH,
                    "page_name": "battery_charger"
                }
            }
        })

        page_response = read_response(proc, timeout=60)
        if "error" in page_response:
            print(f"[ERROR] get_schematic_page failed: {page_response['error']}")
            return False

        result = page_response.get("result", {})
        content = result.get("content", [])
        if content and len(content) > 0:
            text = content[0].get("text", "")
            if "battery_charger" in text and "COMP" in text:
                print("[OK] get_schematic_page returned valid data")
                print(f"     Preview: {text[:100]}...")
            else:
                print("[ERROR] Unexpected response format")
                return False
        else:
            print("[ERROR] No content in response")
            return False

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED ✓")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        proc.terminate()
        proc.wait(timeout=5)

if __name__ == '__main__':
    success = test_mcp_tools()
    sys.exit(0 if success else 1)
