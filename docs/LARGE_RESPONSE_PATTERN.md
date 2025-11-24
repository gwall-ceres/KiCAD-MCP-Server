# Large Response Handling Pattern

## Problem

When MCP tools return large datasets (e.g., 1000+ DRC violations), they can overflow the LLM's context window and cause performance issues.

## Solution Pattern

For tools that can return large datasets, follow this two-step pattern:

### 1. Write to Disk + Return File Path

The primary tool writes data to a file and returns only:
- Summary statistics
- File path for full data
- Metadata (timestamp, totals, etc.)

### 2. Paginated Read Access

A companion tool provides paginated access to the data with:
- `limit`: Maximum items to return (default: 100, max: 500)
- `offset`: Skip N items for pagination (default: 0)
- `summary_only`: Return only summary without data
- Automatic fallback to file path when data exceeds threshold

## Implemented Examples

### DRC Violations

**Primary Tool:** `run_drc`
```python
# Runs DRC check, saves to file
run_drc() -> {
    "success": True,
    "message": "Found 1896 DRC violations",
    "summary": {
        "total": 1896,
        "by_severity": {"error": 1368, "warning": 528},
        "by_type": {...}
    },
    "violationsFile": "path/to/board_drc_violations.json",  # ← File path
    "reportPath": null
}
```

**Read Tool:** `get_drc_violations`
```python
# Returns summary + file path if >100 violations
get_drc_violations(severity="error") -> {
    "success": True,
    "total": 1368,
    "summary": {...},
    "violationsFile": "path/to/board_drc_violations.json",  # ← File path
    "hint": "Use limit/offset to paginate, or Read tool to access file"
}

# OR with pagination for smaller requests
get_drc_violations(severity="error", limit=50, offset=0) -> {
    "success": True,
    "violations": [...50 items...],
    "total": 1368,
    "returned": 50,
    "offset": 0,
    "has_more": True,
    "violationsFile": "path/to/board_drc_violations.json"  # ← Still includes file path
}
```

**Implementation:**
- File: `python/commands/design_rules.py`
- Lines: 179-475

## When to Use This Pattern

Use this pattern when:

1. **Response size can exceed 100 items** - DRC violations, component lists, net lists
2. **Data is structured and filterable** - Can be paginated or filtered by type/severity
3. **Data persists between calls** - Result doesn't change frequently (DRC, BOM analysis)
4. **LLM needs overview first** - Summary helps LLM decide what to query in detail

## Pattern Benefits

1. **Prevents context overflow** - Large datasets don't flood the LLM context
2. **Faster initial response** - Summary loads instantly
3. **Selective deep-dive** - LLM can paginate or read specific sections
4. **File-based fallback** - LLM can use Read tool to access full data
5. **Explicit data size** - LLM knows total count before requesting details

## Implementation Checklist

When adding a new tool that may return large datasets:

- [ ] Primary tool writes full data to JSON file in project directory
- [ ] Primary tool returns summary + `{data}File` path field
- [ ] Companion read tool accepts `limit`, `offset`, `summary_only` parameters
- [ ] Read tool returns file path when result exceeds 100 items
- [ ] Read tool includes `has_more`, `total`, `returned` pagination metadata
- [ ] Tool documentation mentions pagination and file-based access
- [ ] File follows naming convention: `{board_name}_{data_type}.json`

## Tools That Should Use This Pattern

### Already Implemented
- ✅ `run_drc` / `get_drc_violations`

### Candidates for Implementation
- `get_all_designators` - Could return 500+ components
- `get_schematic_components_with_parameters` - Large BOMs
- `get_all_nets` - Complex boards have 1000+ nets
- BOM export tools - When returning data instead of file-only

### Not Needed
- `find_component` - Always returns specific items (1-10 max)
- `get_component_properties` - Single component only
- `get_board_info` - Small summary only

## Usage Example (LLM Perspective)

```
User: "Check the DRC violations for my board"

LLM:
1. Calls run_drc()
   → Gets summary: 1896 violations, file path
2. Sees >100 violations, doesn't call get_drc_violations() immediately
3. Responds: "Found 1896 DRC violations (1368 errors, 528 warnings).
   Top issues: clearance violations (518), hole clearance (201)..."

User: "Show me the first 10 clearance violations"

LLM:
1. Calls get_drc_violations(severity="error", limit=10, offset=0)
   → Gets first 10 specific violations
2. Displays them to user
```

## File Format Standard

All data files should follow this structure:

```json
{
  "board": "/path/to/board.kicad_pcb",
  "timestamp": "2025-11-24T12:34:56",
  "total_{items}": 1896,
  "{item}_counts": {
    "by_type": {...},
    "by_severity": {...}
  },
  "{items}": [
    // Array of actual data items
  ]
}
```

Example: `board_name_drc_violations.json`
```json
{
  "board": "/path/to/board.kicad_pcb",
  "timestamp": "2025-11-24T12:34:56",
  "total_violations": 1896,
  "violation_counts": {
    "clearance": 518,
    "hole_clearance": 201
  },
  "severity_counts": {
    "error": 1368,
    "warning": 528
  },
  "violations": [
    {
      "type": "clearance",
      "severity": "error",
      "message": "Clearance violation...",
      "location": {"x": 0, "y": 0, "unit": "mm"}
    }
  ]
}
```

## Related Patterns

### Other Codebase Patterns
- `search_footprints` uses `limit` parameter (but no pagination/offset)
- Export tools return file paths only (no summary data)

### Future Enhancements
- Streaming responses for real-time data
- Compression for very large datasets
- SQL-based filtering for complex queries
