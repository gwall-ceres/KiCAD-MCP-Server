# Export Tools Conversion Summary

## Overview
Converted 8 export tools from TypeScript (Node.js MCP SDK) to Python (FastMCP).

**Source File**: `src/tools/export.ts`
**Target File**: `export_tools_fastmcp.py`
**Backend**: `python/commands/export.py`

---

## Conversion Status

### ✅ Fully Converted (5/8 tools)
These tools have complete Python backend implementations:

1. **export_gerber** - Export Gerber manufacturing files
   - Backend: `ExportCommands.export_gerber()`
   - Status: ✅ Fully implemented
   - Parameters: outputDir, layers[], useProtelExtensions, generateDrillFiles, generateMapFile, useAuxOrigin

2. **export_pdf** - Export PCB to PDF document
   - Backend: `ExportCommands.export_pdf()`
   - Status: ✅ Fully implemented
   - Parameters: outputPath, layers[], blackAndWhite, frameReference, pageSize enum

3. **export_svg** - Export PCB to SVG graphics
   - Backend: `ExportCommands.export_svg()`
   - Status: ✅ Fully implemented
   - Parameters: outputPath, layers[], blackAndWhite, includeComponents

4. **export_3d** - Export 3D models (STEP/STL/VRML/OBJ)
   - Backend: `ExportCommands.export_3d()`
   - Status: ✅ Fully implemented (STEP and VRML only)
   - Parameters: outputPath, format enum, includeComponents, includeCopper, includeSolderMask, includeSilkscreen
   - Note: Only STEP and VRML formats are implemented in backend

5. **export_bom** - Export Bill of Materials
   - Backend: `ExportCommands.export_bom()`
   - Status: ✅ Fully implemented
   - Parameters: outputPath, format enum (CSV/XML/HTML/JSON), groupByValue, includeAttributes[]

### ⚠️ Converted but Missing Backend (3/8 tools)
These tools are converted to FastMCP but need Python backend implementation:

6. **export_netlist** - Export electrical netlist
   - Backend: ❌ NOT IMPLEMENTED
   - Parameters: outputPath, format enum (KiCad/Spice/Cadstar/OrcadPCB2)
   - Action Required: Add `export_netlist()` method to `python/commands/export.py`

7. **export_position_file** - Export component position file for assembly
   - Backend: ❌ NOT IMPLEMENTED
   - Parameters: outputPath, format enum (CSV/ASCII), units enum (mm/inch), side enum (top/bottom/both)
   - Action Required: Add `export_position_file()` method to `python/commands/export.py`

8. **export_vrml** - Export VRML 3D model
   - Backend: ✅ Uses `export_3d()` with format="VRML"
   - Parameters: outputPath, includeComponents, useRelativePaths
   - Status: ✅ Works via export_3d wrapper

---

## Type Conversions

### Zod to Python Type Hints

| TypeScript (Zod) | Python (FastMCP) | Example |
|-----------------|------------------|---------|
| `z.string()` | `str` | `outputPath: str` |
| `z.array(z.string()).optional()` | `List[str] \| None` | `layers: List[str] \| None = None` |
| `z.boolean().optional()` | `bool \| None` | `blackAndWhite: bool \| None = None` |
| `z.enum(["A4", "A3", ...])` | `Literal["A4", "A3", ...]` | `pageSize: Literal["A4", "A3", "A2", ...]` |

### Enum Types Used

```python
# Page sizes for PDF export
Literal["A4", "A3", "A2", "A1", "A0", "Letter", "Legal", "Tabloid"]

# 3D model formats
Literal["STEP", "STL", "VRML", "OBJ"]

# BOM formats
Literal["CSV", "XML", "HTML", "JSON"]

# Netlist formats
Literal["KiCad", "Spice", "Cadstar", "OrcadPCB2"]

# Position file formats
Literal["CSV", "ASCII"]

# Units
Literal["mm", "inch"]

# Board sides
Literal["top", "bottom", "both"]
```

---

## Key Conversion Patterns

### 1. Function Registration
**Before (TypeScript)**:
```typescript
server.tool(
  "export_gerber",
  {
    outputDir: z.string().describe("Directory to save Gerber files"),
    layers: z.array(z.string()).optional()
  },
  async ({ outputDir, layers }) => {
    const result = await callKicadScript("export_gerber", {
      outputDir, layers
    });
    return {
      content: [{ type: "text", text: JSON.stringify(result) }]
    };
  }
);
```

**After (Python FastMCP)**:
```python
@mcp.tool
def export_gerber(
    outputDir: Annotated[str, Field(description="Directory to save Gerber files")],
    layers: Annotated[List[str] | None, Field(description="...")] = None
) -> Dict[str, Any]:
    """Export Gerber files for PCB manufacturing."""
    params = {"outputDir": outputDir}
    if layers is not None:
        params["layers"] = layers

    result = export_commands.export_gerber(params)

    if not result.get("success"):
        raise ToolError(result.get("message", "Export failed"))

    return result
```

### 2. Error Handling
**Before**: Manual content blocks with isError flag
```typescript
try {
  const result = await callKicadScript(...);
  return { content: [{ type: "text", text: JSON.stringify(result) }] };
} catch (error) {
  return {
    content: [{ type: "text", text: `Error: ${error.message}` }],
    isError: true
  };
}
```

**After**: ToolError exceptions
```python
try:
    result = export_commands.export_gerber(params)
    if not result.get("success"):
        raise ToolError(result.get("message", "Export failed"))
    return result
except ToolError:
    raise
except Exception as e:
    raise ToolError(f"Failed to export: {str(e)}")
```

### 3. Optional Parameters
**Before**: Zod `.optional()`
```typescript
layers: z.array(z.string()).optional()
```

**After**: Union with None and default value
```python
layers: Annotated[List[str] | None, Field(...)] = None
```

Only add to params dict if not None:
```python
if layers is not None:
    params["layers"] = layers
```

---

## Integration with mcp_server.py

To use these export tools in the main server:

```python
# In mcp_server.py

from export_tools_fastmcp import register_export_tools

# After initializing export_commands
export_commands = ExportCommands(board)

# Register all 8 export tools
register_export_tools(mcp, export_commands)
```

---

## Required Backend Implementations

To complete the conversion, add these methods to `python/commands/export.py`:

### 1. export_netlist()
```python
def export_netlist(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Export netlist file"""
    # Implementation using kicad-cli or pcbnew API
    pass
```

### 2. export_position_file()
```python
def export_position_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """Export component position file for assembly"""
    # Implementation using kicad-cli or pcbnew API
    pass
```

---

## Testing Checklist

- [ ] Test export_gerber with various layer combinations
- [ ] Test export_pdf with different page sizes
- [ ] Test export_svg with and without components
- [ ] Test export_3d with STEP format
- [ ] Test export_3d with VRML format
- [ ] Test export_bom with all formats (CSV, XML, HTML, JSON)
- [ ] Test export_netlist (once implemented)
- [ ] Test export_position_file (once implemented)
- [ ] Test export_vrml convenience wrapper

---

## Files Modified/Created

1. **Created**: `export_tools_fastmcp.py` - All 8 export tools converted to FastMCP
2. **Reference**: `src/tools/export.ts` - Original TypeScript implementation
3. **Backend**: `python/commands/export.py` - Existing backend (5/8 methods implemented)
4. **Migration Guide**: `FASTMCP_MIGRATION_GUIDE.md` - Followed strictly for conversion

---

## Notes

1. **Direct Function Calls**: No subprocess communication needed. Export commands are called directly in Python.

2. **Return Type Handling**: FastMCP automatically converts returned dicts to MCP content blocks. No manual serialization needed.

3. **Error Messages**: Using ToolError for user-facing errors maintains clean error reporting to Claude.

4. **Enum Safety**: All TypeScript enums converted to Python Literal types for type safety.

5. **Documentation**: Added comprehensive docstrings following FastMCP best practices.

6. **Missing Methods**: Tools that call missing backend methods include helpful error messages indicating what needs to be implemented.

---

## Success Criteria

✅ All 8 tools converted to FastMCP decorator pattern
✅ Type hints using Literal for enums
✅ Proper error handling with ToolError
✅ Comprehensive docstrings
✅ Optional parameters handled correctly
⚠️ 2 backend methods still need implementation (export_netlist, export_position_file)
✅ Follows FASTMCP_MIGRATION_GUIDE.md patterns exactly

**Conversion Status**: 8/8 tools converted (62.5% fully functional, 37.5% need backend)
