# KiCAD FastMCP Server Test Procedure

## Overview
This document tracks the testing of the KiCAD FastMCP Server refactor. The server has been converted from a mixed Node.js + Python architecture to pure Python using the FastMCP library.

### Key Changes in This Refactor:
1. **Pure Python Architecture** - Eliminated Node.js dependency
2. **FastMCP Framework** - Using FastMCP for MCP server implementation
3. **Schematic DSL Tools** - New tools for schematic analysis (get_schematic_index, get_schematic_page, get_schematic_context)
4. **Distributor Integration** - New tools for DigiKey and Mouser API integration

### Test Files
- **Comprehensive Test Script**: `tests/test_all_kicad_tools.py`
  - Run with: `"C:\Program Files\KiCad\9.0\bin\python.exe" tests/test_all_kicad_tools.py`
  - Creates a temporary test project to exercise all KiCad API functions
  - Uses timeout protection to catch blocking modal dialogs
  - Results saved to `test_results.json`
- **Test Project**: `c:\Users\geoff\Desktop\projects\kicad-astro-daughterboard2\Astro-DB_rev00005\Astro-DB_rev00005.kicad_pro`

---

## Comprehensive Test Results

### Final Test Summary (2024-11-24)

```
============================================================
TEST SUMMARY
============================================================
Total:   41
Passed:  41
Failed:  0
Timeout: 0
Skipped: 0
```

**Note**: `set_active_layer` and `add_layer` were removed from the MCP server as they require GUI and don't work headlessly.

---

## Test Categories

### 1. Project Management Tools
| Tool | Status | Notes |
|------|--------|-------|
| `create_project` | ✅ Passed | Creates new project with board file |
| `get_project_info` | ✅ Passed | Returns project name, path, title, date, revision |
| `save_project` | ✅ Passed | Saves project to disk |
| `open_project` | ✅ Passed | Opens .kicad_pro file successfully |

### 2. Board Tools
| Tool | Status | Notes |
|------|--------|-------|
| `set_board_size` | ✅ Passed | Sets board dimensions (100x80 mm tested) |
| `get_board_info` | ✅ Passed | Returns board size, layer info (25 layers) |
| `get_layer_list` | ✅ Passed | Returns all layers with name, type, id |
| `get_board_extents` | ✅ Passed | Returns board bounding box |
| `add_mounting_hole` | ✅ Passed | Adds 3.2mm mounting hole |
| `add_board_text` | ✅ Passed | Adds silkscreen text |

### 3. Routing Tools
| Tool | Status | Notes |
|------|--------|-------|
| `add_net` | ✅ Passed | Creates GND and VCC nets |
| `route_trace` | ✅ Passed | Routes trace with 0.25mm width |
| `add_via` | ✅ Passed | Adds via (fixed KiCad 9 GetWidth() API) |
| `add_copper_pour` | ✅ Passed | Creates zone with 4 corner points |
| `get_nets_list` | ✅ Passed | Returns net names (fixed KiCad 9 GetClassName() API) |

### 4. Component Tools
| Tool | Status | Notes |
|------|--------|-------|
| `get_component_list` | ✅ Passed | Lists all components on board |
| `place_component` | ✅ Passed | Places R1 with R_0603 footprint |
| `find_component` | ✅ Passed | Finds component by reference |
| `get_component_properties` | ✅ Passed | Returns reference, value, footprint, position |
| `move_component` | ✅ Passed | Moves component to new position |
| `rotate_component` | ✅ Passed | Rotates component to 90° |
| `edit_component` | ✅ Passed | Updates component value |
| `duplicate_component` | ✅ Passed | Duplicates component (fixed KiCad 9 API) |
| `delete_component` | ✅ Passed | Removes component from board |

### 5. Library Tools
| Tool | Status | Notes |
|------|--------|-------|
| `list_libraries` | ✅ Passed | Found 153 libraries |
| `search_footprints` | ✅ Passed | Found 10 footprints matching *0603* |
| `list_library_footprints` | ✅ Passed | Lists footprints in specific library |
| `get_footprint_info` | ✅ Passed | Returns footprint path and details |

### 6. Design Rules Tools
| Tool | Status | Notes |
|------|--------|-------|
| `get_design_rules` | ✅ Passed | Returns clearance, track width (0.2mm), via sizes |
| `set_design_rules` | ✅ Passed | Updates design rules |
| `run_drc` | ✅ Passed | Runs DRC and reports violations |
| `get_drc_violations` | ✅ Passed | Returns paginated violations |

### 7. Export Tools
| Tool | Status | Notes |
|------|--------|-------|
| `export_bom` | ✅ Passed | Exports CSV with component count |
| `export_gerber` | ✅ Passed | Exports 25 Gerber + drill files |
| `export_pdf` | ✅ Passed | Exports PDF with all layers |
| `export_svg` | ✅ Passed | Exports SVG vector graphics |

### 8. Schematic DSL Tools (NEW)
| Tool | Status | Notes |
|------|--------|-------|
| `get_schematic_index` | ✅ Passed | Returns 13 pages with component counts |
| `get_schematic_page` | ✅ Passed | Returns DSL format with components and nets |
| `get_schematic_context` | ✅ Passed | Returns component context with neighbors |

### 9. Distributor Tools (NEW)
| Tool | Status | Notes |
|------|--------|-------|
| `search_component` | ✅ Passed | Searches Mouser/DigiKey by MPN |
| `get_component_availability` | ✅ Passed | Returns stock and pricing from distributors |

---

## Bugs Fixed During Testing

### 1. add_via - GetWidth() KiCad 9 API Change
**File**: `python/commands/routing.py`
**Issue**: `PCB_VIA::GetWidth()` requires layer argument in KiCad 9
**Fix**:
```python
# Get via size - in KiCAD 9, GetWidth() requires a layer argument
try:
    via_size = via.GetWidth(from_id) / 1000000
except TypeError:
    # Fallback for older KiCAD versions
    via_size = via.GetWidth() / 1000000
```

### 2. get_nets_list - GetClassName() Renamed
**File**: `python/commands/routing.py`
**Issue**: `NETINFO_ITEM.GetClassName()` renamed to `GetNetClassName()` in KiCad 9
**Fix**:
```python
# GetClassName was renamed in KiCAD 9
try:
    net_class = net.GetClassName()
except AttributeError:
    try:
        net_class = net.GetNetClassName()
    except AttributeError:
        net_class = "Default"
```

### 3. duplicate_component - SetFootprintName() Not Available
**File**: `python/commands/component.py`
**Issue**: Creating new FOOTPRINT and calling SetFootprintName() fails
**Fix**: Use `source.Duplicate()` to clone footprint correctly:
```python
# Clone the source footprint using KiCAD's Clone method
new_module = source.Duplicate()
new_module.SetReference(new_reference)
```

---

## Environment Requirements

- KiCAD 9.0+ installed with Python support
- Python 3.11+ (bundled with KiCad 9)
- FastMCP library
- `.env` file with API keys for distributor tools:
  - `MOUSER_API_KEY` - Working
  - `DIGIKEY_CLIENT_ID` - Optional
  - `DIGIKEY_CLIENT_SECRET` - Optional

---

## How to Run Tests

### Using KiCad's Bundled Python
```bash
"C:\Program Files\KiCad\9.0\bin\python.exe" tests/test_all_kicad_tools.py
```

### Test Output
- Console shows pass/fail status for each test
- Results saved to `test_results.json`
- Temporary test project created and cleaned up automatically
- Each test has 10-second timeout to catch blocking dialogs

---

## Status Legend
- ⬜ Not Tested
- ✅ Passed
- ❌ Failed
- ⏭️ Skipped (Known API limitation)
- ⚠️ Partial/Issues

---

## Summary

**Total Tests: 41**
**Passed: 41**
**Failed: 0**
**Skipped: 0**

The KiCAD FastMCP server refactor is fully functional. All major features tested:
1. ✅ Project management (create, open, save, info)
2. ✅ Board operations (size, layers, text, mounting holes)
3. ✅ Routing (nets, traces, vias, copper pours)
4. ✅ Component management (place, move, rotate, edit, duplicate, delete)
5. ✅ Library operations (list, search, footprint info)
6. ✅ Design rules and DRC
7. ✅ Export (Gerber, PDF, SVG, BOM)
8. ✅ Schematic DSL tools (NEW)
9. ✅ Distributor integration (NEW)
