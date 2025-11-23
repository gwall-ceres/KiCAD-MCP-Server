# FastMCP Migration Guide: Node.js to Python

This document provides an **authoritative mapping** between the Node.js MCP SDK and Python fastmcp library based on official documentation. Use this as the single source of truth during migration to avoid hallucinations.

## Documentation Sources

- **FastMCP Official Docs**: https://gofastmcp.com/
- **FastMCP GitHub**: https://github.com/jlowin/fastmcp
- **Tools Documentation**: https://gofastmcp.com/servers/tools
- **Resources Documentation**: https://gofastmcp.com/servers/resources
- **Prompts Documentation**: https://gofastmcp.com/servers/prompts
- **PyPI Package**: https://pypi.org/project/fastmcp/

---

## 1. Server Initialization

### Node.js (Current)
```typescript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';

const server = new McpServer({
  name: 'kicad-mcp-server',
  version: '1.0.0',
  description: 'MCP server for KiCAD PCB design operations'
});
```

### Python (FastMCP)
```python
from fastmcp import FastMCP

mcp = FastMCP(
    name="kicad-mcp-server",
    # version is inferred from package metadata
    # description can be added via instructions parameter
)
```

**Key Differences:**
- FastMCP uses a simpler constructor
- No explicit version parameter (uses package metadata)
- Description provided via other means if needed

---

## 2. Tool Registration

### Node.js (Current)
```typescript
import { z } from 'zod';

server.tool(
  "set_board_size",
  {
    width: z.number().describe("Board width"),
    height: z.number().describe("Board height"),
    unit: z.enum(["mm", "inch"]).describe("Unit of measurement")
  },
  async ({ width, height, unit }) => {
    const result = await callKicadScript("set_board_size", {
      width, height, unit
    });

    return {
      content: [{
        type: "text",
        text: JSON.stringify(result)
      }]
    };
  }
);
```

### Python (FastMCP)
```python
from typing import Literal
from fastmcp import FastMCP

mcp = FastMCP("kicad-mcp-server")

@mcp.tool
def set_board_size(
    width: float,
    height: float,
    unit: Literal["mm", "inch"]
) -> dict:
    """Set the size of the PCB board.

    Args:
        width: Board width
        height: Board height
        unit: Unit of measurement (mm or inch)
    """
    # Direct call to Python function - no subprocess needed!
    result = board_commands.set_board_size({
        "width": width,
        "height": height,
        "unit": unit
    })
    return result
```

**Key Differences:**
- Use `@mcp.tool` decorator instead of `server.tool()` method
- Type hints replace Zod schemas (`Literal` for enums)
- Docstrings provide descriptions (parsed automatically)
- Return values are automatically converted to MCP content blocks
- No need for manual content block construction
- **No subprocess call needed** - direct Python function execution

### Tool with Custom Metadata
```python
from typing import Annotated
from pydantic import Field

@mcp.tool(
    name="custom_name",  # Override function name
    description="Custom description",  # Override docstring
    tags={"pcb", "design"},  # Categorization
    enabled=True,  # Can disable dynamically
)
def my_tool(
    query: Annotated[str, Field(description="Search query")],
    limit: Annotated[int, Field(10, ge=1, le=100)] = 10
) -> dict:
    """Tool with advanced parameter metadata"""
    return {"results": []}
```

**Parameter Metadata Options:**
- Simple: `Annotated[str, "Description here"]`
- Advanced: `Annotated[int, Field(default=10, ge=1, le=100, description="...")]`

---

## 3. Resource Registration

### Node.js (Current)
```typescript
server.resource(
  "kicad://project/current/info",
  async () => {
    const result = await callKicadScript("get_project_info", {});
    return {
      contents: [{
        uri: "kicad://project/current/info",
        mimeType: "application/json",
        text: JSON.stringify(result)
      }]
    };
  }
);
```

### Python (FastMCP)
```python
@mcp.resource("kicad://project/current/info")
def get_project_info() -> dict:
    """Provides current project metadata and configuration."""
    return project_commands.get_project_info({})
```

**Key Differences:**
- Use `@mcp.resource(uri)` decorator
- URI is the first argument to the decorator
- Return value automatically serialized as JSON
- MimeType inferred (application/json for dict)
- Much simpler - no manual content block construction

### Resource Templates (Dynamic URIs)
```python
@mcp.resource("kicad://component/{reference}/properties")
def get_component_properties(reference: str) -> dict:
    """Get properties for a specific component by reference.

    Args:
        reference: Component reference designator (e.g., 'R1', 'U3')
    """
    return component_commands.get_component_properties({
        "reference": reference
    })
```

**Template Syntax:**
- Use `{parameter_name}` in URI string
- Function parameter names must match template variables
- FastMCP automatically extracts and validates parameters

### Resource with Custom Options
```python
@mcp.resource(
    uri="kicad://board/preview",
    name="BoardPreview",
    description="PNG preview of the current PCB board",
    mime_type="image/png",
    tags={"visualization", "preview"}
)
def get_board_preview() -> bytes:
    """Returns PNG image data of the board"""
    return board_commands.get_board_2d_view({"format": "png"})
```

---

## 4. Prompt Registration

### Node.js (Current)
```typescript
server.prompt(
  "design-review",
  async (args) => {
    return {
      messages: [{
        role: "user",
        content: {
          type: "text",
          text: "Review the PCB design for common issues..."
        }
      }]
    };
  }
);
```

### Python (FastMCP)
```python
from fastmcp import FastMCP
from fastmcp.prompts import PromptMessage

@mcp.prompt
def design_review() -> list[PromptMessage]:
    """Comprehensive PCB design review checklist."""
    return [
        PromptMessage(
            role="user",
            content="Review the PCB design for common issues including:\n"
                   "- Clearance violations\n"
                   "- Unconnected nets\n"
                   "- Manufacturing constraints\n"
        )
    ]
```

**Key Differences:**
- Use `@mcp.prompt` decorator
- Return list of `PromptMessage` objects
- Can include dynamic content based on parameters

### Prompt with Arguments
```python
@mcp.prompt
def component_placement_guide(component_type: str) -> list[PromptMessage]:
    """Guide for placing specific component types.

    Args:
        component_type: Type of component (e.g., 'resistor', 'capacitor', 'IC')
    """
    return [
        PromptMessage(
            role="user",
            content=f"Provide best practices for placing {component_type} components..."
        )
    ]
```

---

## 5. Server Execution

### Node.js (Current)
```typescript
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

async function start() {
  const transport = new StdioServerTransport();
  await server.connect(transport);

  // Setup signal handlers
  process.on('SIGINT', async () => {
    await server.close();
    process.exit(0);
  });
}

start().catch(console.error);
```

### Python (FastMCP)
```python
if __name__ == "__main__":
    # STDIO is the default transport
    mcp.run()

    # Or explicitly specify:
    # mcp.run(transport="stdio")
```

**Key Differences:**
- Single line to run server: `mcp.run()`
- STDIO transport is default (no import needed)
- Signal handling built-in
- Automatic lifecycle management

**Alternative: FastMCP CLI**
```bash
# No need for __main__ block at all
fastmcp run path/to/server.py
```

---

## 6. Async Support

### Node.js (Current)
```typescript
// Always async
server.tool("fetch_data", schema, async (params) => {
  const data = await someAsyncOperation();
  return { content: [{ type: "text", text: JSON.stringify(data) }] };
});
```

### Python (FastMCP)
```python
# Sync functions work fine
@mcp.tool
def calculate(a: int, b: int) -> int:
    """Synchronous calculation"""
    return a + b

# Async functions also supported
@mcp.tool
async def fetch_data(url: str) -> dict:
    """Async I/O operation"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

**Key Differences:**
- Both `def` and `async def` work
- Use async for I/O-bound operations
- Use sync for CPU-bound operations (FastMCP handles threading)

---

## 7. Error Handling

### Node.js (Current)
```typescript
try {
  const result = await callKicadScript("command", params);
  return { content: [{ type: "text", text: JSON.stringify(result) }] };
} catch (error) {
  return {
    content: [{ type: "text", text: `Error: ${error.message}` }],
    isError: true
  };
}
```

### Python (FastMCP)
```python
from fastmcp.exceptions import ToolError

@mcp.tool
def divide(a: float, b: float) -> float:
    """Divide two numbers"""
    if b == 0:
        raise ToolError("Division by zero not allowed")
    return a / b
```

**Error Types:**
- `ToolError`: User-facing error message (always shown)
- `ValueError`, `TypeError`: Standard Python exceptions
- `Exception`: Generic errors

**Masking Errors (Security):**
```python
# Only show ToolError messages, hide implementation details
mcp = FastMCP("secure-server", mask_error_details=True)
```

---

## 8. Context Access (Advanced)

### Node.js (Current)
```typescript
// Limited context access
server.tool("process", schema, async (params, context) => {
  // Context not commonly used
});
```

### Python (FastMCP)
```python
from fastmcp import FastMCP, Context

@mcp.tool
async def process_data(data_uri: str, ctx: Context) -> dict:
    """Process data with logging and progress tracking"""

    # Logging
    await ctx.info(f"Processing {data_uri}")
    await ctx.debug("Debug information")
    await ctx.warning("Warning message")

    # Progress reporting
    await ctx.report_progress(progress=50, total=100)

    # Access other resources
    resource = await ctx.read_resource(data_uri)

    # Sample from LLM
    response = await ctx.sample_llm(
        messages=[{"role": "user", "content": "Analyze this..."}]
    )

    return {"status": "complete"}
```

**Context Features:**
- Logging: `info()`, `debug()`, `warning()`, `error()`
- Progress: `report_progress(progress, total)`
- Resources: `read_resource(uri)`
- LLM Sampling: `sample_llm(messages, params)`

---

## 9. Return Types & Content Blocks

### Node.js (Current)
```typescript
// Manual content block construction
return {
  content: [
    { type: "text", text: "Hello" },
    { type: "image", data: base64ImageData, mimeType: "image/png" }
  ]
};
```

### Python (FastMCP)
```python
from fastmcp.utilities.types import Image, Audio, File

# Automatic conversion based on type
@mcp.tool
def get_text() -> str:
    return "Hello"  # Automatically becomes TextContent

@mcp.tool
def get_data() -> dict:
    return {"key": "value"}  # Automatically structured + text

@mcp.tool
def get_image() -> Image:
    return Image(path="chart.png")  # Automatically image content

@mcp.tool
def get_multiple() -> list:
    return [
        "Text content",
        Image(path="image.png"),
        {"data": "structured"}
    ]  # Multiple content blocks
```

**Automatic Conversions:**
- `str` → TextContent
- `dict`/Pydantic model → StructuredContent + TextContent (if return type annotated)
- `bytes` → Base64-encoded BlobResourceContents
- `Image`/`Audio`/`File` → Appropriate media content
- `list` → Multiple content blocks
- `None` → Empty response

**Explicit Control:**
```python
from fastmcp.tools.tool import ToolResult

@mcp.tool
def advanced() -> ToolResult:
    return ToolResult(
        content="Summary text",
        structured_content={"data": "value", "count": 42},
        meta={"execution_time_ms": 145}
    )
```

---

## 10. Configuration & Settings

### Node.js (Current)
```typescript
const server = new McpServer({
  name: 'server',
  version: '1.0.0'
});

// Configuration scattered across files
```

### Python (FastMCP)
```python
mcp = FastMCP(
    name="kicad-mcp-server",

    # Validation
    strict_input_validation=False,  # Default: flexible validation

    # Error handling
    mask_error_details=False,  # Default: show all errors

    # Duplicate handling
    on_duplicate_tools="warn",     # Options: warn, error, replace, ignore
    on_duplicate_prompts="warn",
    on_duplicate_resources="warn",

    # Instructions (shown to LLM)
    instructions="AI-assisted PCB design with KiCAD..."
)
```

---

## 11. Complete Migration Example

### Before (Node.js + Python subprocess)

**src/server.ts (TypeScript)**
```typescript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { spawn } from 'child_process';
import { z } from 'zod';

const server = new McpServer({ name: 'kicad' });
const pythonProcess = spawn('python', ['kicad_interface.py']);

server.tool(
  "place_component",
  {
    componentId: z.string(),
    position: z.object({ x: z.number(), y: z.number() })
  },
  async ({ componentId, position }) => {
    // Send JSON to Python subprocess via stdin
    const request = JSON.stringify({
      command: "place_component",
      params: { componentId, position }
    });
    pythonProcess.stdin.write(request + '\n');

    // Wait for response from stdout
    const result = await readFromPythonProcess();

    return {
      content: [{ type: "text", text: JSON.stringify(result) }]
    };
  }
);
```

**python/kicad_interface.py (Python)**
```python
# Reads from stdin, processes, writes to stdout
for line in sys.stdin:
    command_data = json.loads(line)
    command = command_data["command"]
    params = command_data["params"]

    result = interface.handle_command(command, params)
    print(json.dumps(result))
    sys.stdout.flush()
```

### After (Pure Python with FastMCP)

**mcp_server.py (Single file)**
```python
from fastmcp import FastMCP
from typing import Annotated
from pydantic import Field

# Import existing command handlers
from commands.component import ComponentCommands

mcp = FastMCP("kicad-mcp-server")

# Initialize command handlers (already exists!)
component_commands = ComponentCommands(board=None, library=None)

@mcp.tool
def place_component(
    componentId: Annotated[str, "Component ID/footprint to place"],
    position: Annotated[dict, Field(description="Position with x and y coordinates")]
) -> dict:
    """Place a component on the PCB board.

    Args:
        componentId: Component identifier or footprint name
        position: Dictionary with 'x' and 'y' coordinates in mm
    """
    # Direct function call - no subprocess!
    return component_commands.place_component({
        "componentId": componentId,
        "position": position
    })

if __name__ == "__main__":
    mcp.run()  # That's it!
```

**Key Simplifications:**
- ❌ No subprocess management
- ❌ No stdin/stdout communication
- ❌ No JSON serialization between processes
- ❌ No request queue
- ❌ No TypeScript compilation
- ✅ Direct Python function calls
- ✅ Single language codebase
- ✅ Simpler error handling
- ✅ Better performance

---

## 12. Testing

### Node.js (Current)
```typescript
// Requires running subprocess and mocking IPC
```

### Python (FastMCP)
```python
# Direct function testing
def test_place_component():
    result = place_component(
        componentId="R_0805",
        position={"x": 10.0, "y": 20.0}
    )
    assert result["success"] == True

# Or test with FastMCP client
from fastmcp import FastMCP

async def test_with_client():
    async with mcp.client() as client:
        result = await client.call_tool("place_component", {
            "componentId": "R_0805",
            "position": {"x": 10.0, "y": 20.0}
        })
        assert result["success"] == True
```

---

## 13. Deployment Configuration

### Claude Desktop Config (Node.js)
```json
{
  "mcpServers": {
    "kicad": {
      "command": "node",
      "args": ["/path/to/KiCAD-MCP-Server/dist/index.js"],
      "env": {
        "PYTHONPATH": "C:\\Program Files\\KiCad\\9.0\\lib\\python3\\dist-packages"
      }
    }
  }
}
```

### Claude Desktop Config (FastMCP)
```json
{
  "mcpServers": {
    "kicad": {
      "command": "python",
      "args": ["-m", "fastmcp", "run", "/path/to/KiCAD-MCP-Server/mcp_server.py"],
      "env": {
        "PYTHONPATH": "C:\\Program Files\\KiCad\\9.0\\lib\\python3\\dist-packages"
      }
    }
  }
}
```

**Or with virtual environment:**
```json
{
  "mcpServers": {
    "kicad": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "fastmcp", "run", "/path/to/mcp_server.py"]
    }
  }
}
```

---

## 14. Migration Checklist

- [ ] Install fastmcp: `pip install fastmcp`
- [ ] Create new `mcp_server.py` entry point
- [ ] Initialize FastMCP server
- [ ] Convert tool registrations (use @mcp.tool decorator)
- [ ] Convert resource registrations (use @mcp.resource decorator)
- [ ] Convert prompt registrations (use @mcp.prompt decorator)
- [ ] Update return types (leverage automatic conversion)
- [ ] Test all tools individually
- [ ] Update Claude Desktop configuration
- [ ] Update README.md
- [ ] Remove Node.js files (package.json, tsconfig.json, src/, dist/)
- [ ] Remove node_modules/
- [ ] Test end-to-end with Claude Desktop

---

## Summary of Benefits

| Aspect | Node.js SDK | FastMCP |
|--------|-------------|---------|
| **Languages** | TypeScript + Python | Python only |
| **Communication** | IPC via stdin/stdout | Direct function calls |
| **Setup Complexity** | High (2 processes) | Low (1 process) |
| **Type Validation** | Zod schemas | Python type hints |
| **Error Handling** | Manual content blocks | Automatic + ToolError |
| **Return Types** | Manual serialization | Automatic conversion |
| **Async Support** | Required | Optional (sync or async) |
| **Testing** | Complex (subprocess) | Simple (direct calls) |
| **Dependencies** | npm + pip | pip only |
| **Build Step** | Required (tsc) | None |
| **Performance** | IPC overhead | Direct calls |

---

**This document is based on official FastMCP documentation (v2.x) as of 2025.**

For latest updates, see https://gofastmcp.com/
