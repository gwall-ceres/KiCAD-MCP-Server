# Export Tools Quick Reference

## Tool Signatures

### 1. export_gerber
```python
def export_gerber(
    outputDir: str,                    # Required
    layers: List[str] | None = None,   # Optional
    useProtelExtensions: bool | None = None,
    generateDrillFiles: bool | None = None,
    generateMapFile: bool | None = None,
    useAuxOrigin: bool | None = None
) -> Dict[str, Any]
```

**Example**:
```python
export_gerber(
    outputDir="/output/gerbers",
    generateDrillFiles=True,
    layers=["F.Cu", "B.Cu", "F.SilkS"]
)
```

---

### 2. export_pdf
```python
def export_pdf(
    outputPath: str,                   # Required
    layers: List[str] | None = None,   # Optional
    blackAndWhite: bool | None = None,
    frameReference: bool | None = None,
    pageSize: Literal["A4", "A3", "A2", "A1", "A0",
                      "Letter", "Legal", "Tabloid"] | None = None
) -> Dict[str, Any]
```

**Example**:
```python
export_pdf(
    outputPath="/output/board.pdf",
    pageSize="A4",
    blackAndWhite=False
)
```

---

### 3. export_svg
```python
def export_svg(
    outputPath: str,                   # Required
    layers: List[str] | None = None,   # Optional
    blackAndWhite: bool | None = None,
    includeComponents: bool | None = None
) -> Dict[str, Any]
```

**Example**:
```python
export_svg(
    outputPath="/output/board.svg",
    includeComponents=True,
    layers=["F.Cu", "F.SilkS"]
)
```

---

### 4. export_3d
```python
def export_3d(
    outputPath: str,                   # Required
    format: Literal["STEP", "STL", "VRML", "OBJ"],  # Required
    includeComponents: bool | None = None,
    includeCopper: bool | None = None,
    includeSolderMask: bool | None = None,
    includeSilkscreen: bool | None = None
) -> Dict[str, Any]
```

**Example**:
```python
export_3d(
    outputPath="/output/board.step",
    format="STEP",
    includeComponents=True,
    includeCopper=True
)
```

---

### 5. export_bom
```python
def export_bom(
    outputPath: str,                   # Required
    format: Literal["CSV", "XML", "HTML", "JSON"],  # Required
    groupByValue: bool | None = None,
    includeAttributes: List[str] | None = None
) -> Dict[str, Any]
```

**Example**:
```python
export_bom(
    outputPath="/output/bom.csv",
    format="CSV",
    groupByValue=True,
    includeAttributes=["Manufacturer", "MPN"]
)
```

---

### 6. export_netlist
```python
def export_netlist(
    outputPath: str,                   # Required
    format: Literal["KiCad", "Spice", "Cadstar",
                    "OrcadPCB2"] | None = None
) -> Dict[str, Any]
```

**Example**:
```python
export_netlist(
    outputPath="/output/netlist.net",
    format="KiCad"
)
```

**Status**: ⚠️ Backend not implemented yet

---

### 7. export_position_file
```python
def export_position_file(
    outputPath: str,                   # Required
    format: Literal["CSV", "ASCII"] | None = None,
    units: Literal["mm", "inch"] | None = None,
    side: Literal["top", "bottom", "both"] | None = None
) -> Dict[str, Any]
```

**Example**:
```python
export_position_file(
    outputPath="/output/positions.csv",
    format="CSV",
    units="mm",
    side="both"
)
```

**Status**: ⚠️ Backend not implemented yet

---

### 8. export_vrml
```python
def export_vrml(
    outputPath: str,                   # Required
    includeComponents: bool | None = None,
    useRelativePaths: bool | None = None
) -> Dict[str, Any]
```

**Example**:
```python
export_vrml(
    outputPath="/output/board.wrl",
    includeComponents=True,
    useRelativePaths=False
)
```

---

## Common Return Format

All export tools return:
```python
{
    "success": bool,
    "message": str,
    "file": {
        "path": str,
        "format": str,
        # ... additional fields
    }
}
```

On error:
```python
{
    "success": False,
    "message": str,
    "errorDetails": str
}
```

---

## Integration Code

```python
from export_tools_fastmcp import register_export_tools

# In mcp_server.py after initializing export_commands:
export_commands = ExportCommands(board)
register_export_tools(mcp, export_commands)
```

---

## Layer Name Examples

Common KiCAD layer names:
- `"F.Cu"` - Front copper
- `"B.Cu"` - Back copper
- `"F.SilkS"` - Front silkscreen
- `"B.SilkS"` - Back silkscreen
- `"F.Mask"` - Front solder mask
- `"B.Mask"` - Back solder mask
- `"Edge.Cuts"` - Board outline

---

## File Extensions

| Export Type | Typical Extension |
|-------------|------------------|
| Gerber | .gbr, .gbl, .gtl |
| Drill | .drl, .cnc |
| PDF | .pdf |
| SVG | .svg |
| STEP | .step, .stp |
| STL | .stl |
| VRML | .wrl, .vrml |
| BOM | .csv, .xml, .html, .json |
| Netlist | .net |
| Position | .csv, .txt |

---

## Common Use Cases

### Manufacturing Package
```python
# 1. Export Gerber files
export_gerber(
    outputDir="/mfg/gerbers",
    generateDrillFiles=True,
    generateMapFile=True
)

# 2. Export BOM
export_bom(
    outputPath="/mfg/bom.csv",
    format="CSV",
    groupByValue=True
)

# 3. Export position file
export_position_file(
    outputPath="/mfg/positions.csv",
    format="CSV",
    units="mm"
)
```

### Documentation
```python
# 1. Export PDF
export_pdf(
    outputPath="/docs/board.pdf",
    pageSize="A4",
    layers=["F.Cu", "B.Cu", "F.SilkS", "B.SilkS"]
)

# 2. Export 3D model
export_3d(
    outputPath="/docs/board.step",
    format="STEP",
    includeComponents=True
)
```

### Design Review
```python
# Export SVG for each layer
for layer in ["F.Cu", "B.Cu", "F.SilkS", "B.SilkS"]:
    export_svg(
        outputPath=f"/review/{layer}.svg",
        layers=[layer],
        includeComponents=True
    )
```

---

## Error Handling

All tools raise `ToolError` on failure:
```python
from fastmcp.exceptions import ToolError

try:
    result = export_gerber(outputDir="/output")
    if result["success"]:
        print(f"Files exported to: {result['outputDir']}")
except ToolError as e:
    print(f"Export failed: {e}")
```
