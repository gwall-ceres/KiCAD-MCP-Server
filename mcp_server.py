#!/usr/bin/env python3
"""
KiCAD FastMCP Server
Pure Python MCP server for KiCAD PCB design automation using FastMCP

This replaces the Node.js + Python subprocess architecture with a single
Python process using the FastMCP library.
"""

import sys
import logging
import os
from typing import Literal, Annotated, Any, Dict
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import FastMCP
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from pydantic import Field

# Configure logging (same as original kicad_interface.py)
log_dir = os.path.join(os.path.expanduser('~'), '.kicad-mcp', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'fastmcp_server.log')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger('kicad_fastmcp')

logger.info("=" * 70)
logger.info("Starting KiCAD FastMCP Server")
logger.info("=" * 70)
logger.info(f"Python version: {sys.version}")
logger.info(f"Python executable: {sys.executable}")
logger.info(f"Platform: {sys.platform}")
logger.info(f"Working directory: {os.getcwd()}")

# Add python directory to path for imports
python_dir = os.path.join(os.path.dirname(__file__), 'python')
if python_dir not in sys.path:
    sys.path.insert(0, python_dir)
    logger.info(f"Added to sys.path: {python_dir}")

# Import platform helper and add KiCAD paths
try:
    from utils.platform_helper import PlatformHelper
    from utils.kicad_process import check_and_launch_kicad, KiCADProcessManager

    logger.info(f"Detecting KiCAD Python paths for {PlatformHelper.get_platform_name()}...")
    paths_added = PlatformHelper.add_kicad_to_python_path()

    if paths_added:
        logger.info("Successfully added KiCAD Python paths to sys.path")
    else:
        logger.warning("No KiCAD Python paths found - attempting to import pcbnew from system path")
except ImportError as e:
    logger.error(f"Failed to import platform helpers: {e}")
    sys.exit(1)

# Import KiCAD's Python API
try:
    logger.info("Attempting to import pcbnew module...")
    import pcbnew  # type: ignore
    logger.info(f"Successfully imported pcbnew module from: {pcbnew.__file__}")
    logger.info(f"pcbnew version: {pcbnew.GetBuildVersion()}")
except ImportError as e:
    logger.error(f"Failed to import pcbnew module: {e}")
    logger.error(f"Current sys.path: {sys.path}")
    logger.error("Please ensure KiCAD 9.0+ is installed with Python support")
    sys.exit(1)

# Import command handlers
try:
    logger.info("Importing command handlers...")
    from commands.project import ProjectCommands
    from commands.board import BoardCommands
    from commands.component import ComponentCommands
    from commands.routing import RoutingCommands
    from commands.design_rules import DesignRuleCommands
    from commands.export import ExportCommands
    from commands.schematic import SchematicManager
    from commands.library import LibraryManager as FootprintLibraryManager, LibraryCommands
    from commands.schematic_dsl import SchematicDSLManager
    from commands.distributor import DistributorCommands
    logger.info("Successfully imported all command handlers")
except ImportError as e:
    logger.error(f"Failed to import command handlers: {e}")
    sys.exit(1)

# Initialize FastMCP server
mcp = FastMCP(
    name="kicad-mcp-server",
    instructions="AI-assisted PCB design with KiCAD. Use tools to create projects, design boards, place components, route traces, and export manufacturing files."
)

logger.info("Initialized FastMCP server")

# ============================================================================
# Global state - command handlers
# ============================================================================
# These will be initialized when a project is created/opened
board = None
footprint_library = FootprintLibraryManager()
project_commands = ProjectCommands(board)
board_commands = BoardCommands(board)
component_commands = ComponentCommands(board, footprint_library)
routing_commands = RoutingCommands(board)
design_rule_commands = DesignRuleCommands(board)
export_commands = ExportCommands(board)
library_commands = LibraryCommands(footprint_library)
distributor_commands = DistributorCommands(board)

logger.info("Initialized command handlers")

def update_board_reference(new_board):
    """Update board reference in all command handlers"""
    global board
    board = new_board
    project_commands.board = board
    board_commands.board = board
    component_commands.board = board
    routing_commands.board = board
    design_rule_commands.board = board
    export_commands.board = board
    distributor_commands.board = board
    logger.info("Updated board reference in all command handlers")


# ============================================================================
# PROJECT TOOLS
# ============================================================================

@mcp.tool
def create_project(
    path: Annotated[str, Field(description="Directory path where project will be created")],
    name: Annotated[str, Field(description="Name of the project")],
    template: Annotated[str, Field(description="Optional template to use")] = "blank"
) -> Dict[str, Any]:
    """Create a new KiCAD project with PCB and schematic files."""
    try:
        result = project_commands.create_project({
            "path": path,
            "projectName": name,
            "template": template
        })

        # Update board reference if successful
        if result.get("success"):
            update_board_reference(project_commands.board)

        return result
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise ToolError(f"Failed to create project: {str(e)}")


@mcp.tool
def open_project(
    filename: Annotated[str, Field(description="Path to .kicad_pro or .kicad_pcb file")]
) -> Dict[str, Any]:
    """Open an existing KiCAD project file."""
    try:
        result = project_commands.open_project({"filename": filename})

        # Update board reference if successful
        if result.get("success"):
            update_board_reference(project_commands.board)

        return result
    except Exception as e:
        logger.error(f"Error opening project: {e}")
        raise ToolError(f"Failed to open project: {str(e)}")


@mcp.tool
def save_project(
    path: Annotated[str | None, Field(description="Optional new path to save to")] = None
) -> Dict[str, Any]:
    """Save the current KiCAD project to disk."""
    try:
        params = {}
        if path:
            params["path"] = path
        return project_commands.save_project(params)
    except Exception as e:
        logger.error(f"Error saving project: {e}")
        raise ToolError(f"Failed to save project: {str(e)}")


@mcp.tool
def get_project_info() -> Dict[str, Any]:
    """Get information about the currently open project."""
    try:
        return project_commands.get_project_info({})
    except Exception as e:
        logger.error(f"Error getting project info: {e}")
        raise ToolError(f"Failed to get project info: {str(e)}")


# ============================================================================
# BOARD TOOLS
# ============================================================================

@mcp.tool
def set_board_size(
    width: Annotated[float, Field(description="Board width")],
    height: Annotated[float, Field(description="Board height")],
    unit: Annotated[Literal["mm", "inch"], Field(description="Unit of measurement")]
) -> Dict[str, Any]:
    """Set the size of the PCB board."""
    try:
        return board_commands.set_board_size({
            "width": width,
            "height": height,
            "unit": unit
        })
    except Exception as e:
        logger.error(f"Error setting board size: {e}")
        raise ToolError(f"Failed to set board size: {str(e)}")


@mcp.tool
def add_board_outline(
    shape: Annotated[Literal["rectangle", "circle", "polygon"], Field(description="Shape of the outline")],
    params: Annotated[Dict[str, Any], Field(description="Parameters for the shape (x, y, width, height, etc.)")]
) -> Dict[str, Any]:
    """Add a board outline to the PCB."""
    try:
        return board_commands.add_board_outline({
            "shape": shape,
            "params": params
        })
    except Exception as e:
        logger.error(f"Error adding board outline: {e}")
        raise ToolError(f"Failed to add board outline: {str(e)}")


# ============================================================================
# SCHEMATIC DSL TOOLS
# ============================================================================

@mcp.tool
def get_schematic_index(
    project_path: Annotated[str, Field(description="Path to KiCAD project directory")]
) -> str:
    """Get project-wide schematic index showing all pages and inter-page signals."""
    try:
        return SchematicDSLManager.get_schematic_index({"project_path": project_path})
    except Exception as e:
        logger.error(f"Error getting schematic index: {e}")
        raise ToolError(f"Failed to get schematic index: {str(e)}")


@mcp.tool
def get_schematic_page(
    project_path: Annotated[str, Field(description="Path to KiCAD project directory")],
    page_name: Annotated[str, Field(description="Name of schematic page (without .kicad_sch)")]
) -> str:
    """Get detailed DSL representation of a specific schematic page."""
    try:
        return SchematicDSLManager.get_schematic_page({
            "project_path": project_path,
            "page_name": page_name
        })
    except Exception as e:
        logger.error(f"Error getting schematic page: {e}")
        raise ToolError(f"Failed to get schematic page: {str(e)}")


@mcp.tool
def get_schematic_context(
    project_path: Annotated[str, Field(description="Path to KiCAD project directory")],
    component_ref: Annotated[str | None, Field(description="Component designator (e.g., 'R1', 'U3')")] = None,
    net_name: Annotated[str | None, Field(description="Net name to trace")] = None
) -> str:
    """Get contextual information about a component or net in the schematic."""
    try:
        params = {"project_path": project_path}
        if component_ref:
            params["component_ref"] = component_ref
        if net_name:
            params["net_name"] = net_name
        return SchematicDSLManager.get_schematic_context(params)
    except Exception as e:
        logger.error(f"Error getting schematic context: {e}")
        raise ToolError(f"Failed to get schematic context: {str(e)}")


# ============================================================================
# COMPONENT TOOLS
# ============================================================================

@mcp.tool
def place_component(
    componentId: Annotated[str, Field(description="Identifier for the component to place (e.g., 'R_0603_10k')")],
    position: Annotated[Dict[str, Any], Field(description="Position coordinates and unit (x, y, unit)")],
    reference: Annotated[str | None, Field(description="Optional desired reference (e.g., 'R5')")] = None,
    value: Annotated[str | None, Field(description="Optional component value (e.g., '10k')")] = None,
    footprint: Annotated[str | None, Field(description="Optional specific footprint name")] = None,
    rotation: Annotated[float | None, Field(description="Optional rotation in degrees")] = None,
    layer: Annotated[str | None, Field(description="Optional layer (e.g., 'F.Cu', 'B.SilkS')")] = None
) -> Dict[str, Any]:
    """Place a component on the PCB board with specified position and properties."""
    try:
        params = {
            "componentId": componentId,
            "position": position
        }
        if reference is not None:
            params["reference"] = reference
        if value is not None:
            params["value"] = value
        if footprint is not None:
            params["footprint"] = footprint
        if rotation is not None:
            params["rotation"] = rotation
        if layer is not None:
            params["layer"] = layer

        return component_commands.place_component(params)
    except Exception as e:
        logger.error(f"Error placing component: {e}")
        raise ToolError(f"Failed to place component: {str(e)}")


@mcp.tool
def move_component(
    reference: Annotated[str, Field(description="Reference designator of the component (e.g., 'R5')")],
    position: Annotated[Dict[str, Any], Field(description="New position coordinates and unit (x, y, unit)")],
    rotation: Annotated[float | None, Field(description="Optional new rotation in degrees")] = None
) -> Dict[str, Any]:
    """Move a component to a new position on the PCB."""
    try:
        params = {
            "reference": reference,
            "position": position
        }
        if rotation is not None:
            params["rotation"] = rotation

        return component_commands.move_component(params)
    except Exception as e:
        logger.error(f"Error moving component: {e}")
        raise ToolError(f"Failed to move component: {str(e)}")


@mcp.tool
def rotate_component(
    reference: Annotated[str, Field(description="Reference designator of the component (e.g., 'R5')")],
    angle: Annotated[float, Field(description="Rotation angle in degrees (absolute, not relative)")]
) -> Dict[str, Any]:
    """Rotate a component to a specific angle on the PCB."""
    try:
        return component_commands.rotate_component({
            "reference": reference,
            "angle": angle
        })
    except Exception as e:
        logger.error(f"Error rotating component: {e}")
        raise ToolError(f"Failed to rotate component: {str(e)}")


@mcp.tool
def delete_component(
    reference: Annotated[str, Field(description="Reference designator of the component to delete (e.g., 'R5')")]
) -> Dict[str, Any]:
    """Delete a component from the PCB by its reference designator."""
    try:
        return component_commands.delete_component({
            "reference": reference
        })
    except Exception as e:
        logger.error(f"Error deleting component: {e}")
        raise ToolError(f"Failed to delete component: {str(e)}")


@mcp.tool
def edit_component(
    reference: Annotated[str, Field(description="Reference designator of the component (e.g., 'R5')")],
    newReference: Annotated[str | None, Field(description="Optional new reference designator")] = None,
    value: Annotated[str | None, Field(description="Optional new component value")] = None,
    footprint: Annotated[str | None, Field(description="Optional new footprint")] = None
) -> Dict[str, Any]:
    """Edit properties of an existing component on the PCB."""
    try:
        params = {"reference": reference}
        if newReference is not None:
            params["newReference"] = newReference
        if value is not None:
            params["value"] = value
        if footprint is not None:
            params["footprint"] = footprint

        return component_commands.edit_component(params)
    except Exception as e:
        logger.error(f"Error editing component: {e}")
        raise ToolError(f"Failed to edit component: {str(e)}")


@mcp.tool
def find_component(
    reference: Annotated[str | None, Field(description="Reference designator to search for")] = None,
    value: Annotated[str | None, Field(description="Component value to search for")] = None
) -> Dict[str, Any]:
    """Find a component on the PCB by reference designator or value."""
    try:
        params = {}
        if reference is not None:
            params["reference"] = reference
        if value is not None:
            params["value"] = value

        return component_commands.find_component(params)
    except Exception as e:
        logger.error(f"Error finding component: {e}")
        raise ToolError(f"Failed to find component: {str(e)}")


@mcp.tool
def get_component_properties(
    reference: Annotated[str, Field(description="Reference designator of the component (e.g., 'R5')")]
) -> Dict[str, Any]:
    """Get all properties of a component on the PCB."""
    try:
        return component_commands.get_component_properties({
            "reference": reference
        })
    except Exception as e:
        logger.error(f"Error getting component properties: {e}")
        raise ToolError(f"Failed to get component properties: {str(e)}")


@mcp.tool
def add_component_annotation(
    reference: Annotated[str, Field(description="Reference designator of the component (e.g., 'R5')")],
    annotation: Annotated[str, Field(description="Annotation or comment text to add")],
    visible: Annotated[bool | None, Field(description="Whether the annotation should be visible on the PCB")] = None
) -> Dict[str, Any]:
    """Add an annotation or comment to a component on the PCB."""
    try:
        params = {
            "reference": reference,
            "annotation": annotation
        }
        if visible is not None:
            params["visible"] = visible

        return component_commands.add_component_annotation(params)
    except Exception as e:
        logger.error(f"Error adding component annotation: {e}")
        raise ToolError(f"Failed to add component annotation: {str(e)}")


@mcp.tool
def group_components(
    references: Annotated[list[str], Field(description="Reference designators of components to group")],
    groupName: Annotated[str, Field(description="Name for the component group")]
) -> Dict[str, Any]:
    """Group multiple components together on the PCB."""
    try:
        return component_commands.group_components({
            "references": references,
            "groupName": groupName
        })
    except Exception as e:
        logger.error(f"Error grouping components: {e}")
        raise ToolError(f"Failed to group components: {str(e)}")


@mcp.tool
def replace_component(
    reference: Annotated[str, Field(description="Reference designator of the component to replace")],
    newComponentId: Annotated[str, Field(description="ID of the new component to use")],
    newFootprint: Annotated[str | None, Field(description="Optional new footprint")] = None,
    newValue: Annotated[str | None, Field(description="Optional new component value")] = None
) -> Dict[str, Any]:
    """Replace a component with a different component on the PCB."""
    try:
        params = {
            "reference": reference,
            "newComponentId": newComponentId
        }
        if newFootprint is not None:
            params["newFootprint"] = newFootprint
        if newValue is not None:
            params["newValue"] = newValue

        return component_commands.replace_component(params)
    except Exception as e:
        logger.error(f"Error replacing component: {e}")
        raise ToolError(f"Failed to replace component: {str(e)}")


# ============================================================================
# ROUTING TOOLS
# ============================================================================

@mcp.tool
def add_net(
    name: Annotated[str, Field(description="Net name")],
    netClass: Annotated[str | None, Field(description="Net class name")] = None
) -> Dict[str, Any]:
    """Create a new net on the PCB.

    Args:
        name: Net name (e.g., "GND", "VCC", "USB_D+")
        netClass: Optional net class name to assign this net to
    """
    try:
        params = {"name": name}
        if netClass:
            params["netClass"] = netClass
        return routing_commands.add_net(params)
    except Exception as e:
        logger.error(f"Error adding net: {e}")
        raise ToolError(f"Failed to add net: {str(e)}")


@mcp.tool
def route_trace(
    start: Annotated[Dict[str, Any], Field(description="Start position with x, y coordinates and optional unit")],
    end: Annotated[Dict[str, Any], Field(description="End position with x, y coordinates and optional unit")],
    layer: Annotated[str, Field(description="PCB layer (e.g., 'F.Cu', 'B.Cu')")],
    width: Annotated[float, Field(description="Trace width in mm")],
    net: Annotated[str, Field(description="Net name for this trace")]
) -> Dict[str, Any]:
    """Route a trace between two points on the PCB.

    Args:
        start: Start position dict with 'x' and 'y' coordinates, optional 'unit'
        end: End position dict with 'x' and 'y' coordinates, optional 'unit'
        layer: PCB layer name (e.g., 'F.Cu' for front copper, 'B.Cu' for back copper)
        width: Trace width in millimeters
        net: Net name to assign to this trace
    """
    try:
        return routing_commands.route_trace({
            "start": start,
            "end": end,
            "layer": layer,
            "width": width,
            "net": net
        })
    except Exception as e:
        logger.error(f"Error routing trace: {e}")
        raise ToolError(f"Failed to route trace: {str(e)}")


@mcp.tool
def add_via(
    position: Annotated[Dict[str, Any], Field(description="Via position with x, y coordinates and optional unit")],
    net: Annotated[str, Field(description="Net name for this via")],
    viaType: Annotated[str | None, Field(description="Via type: 'through', 'blind', or 'buried'")] = None
) -> Dict[str, Any]:
    """Add a via to the PCB to connect traces between layers.

    Args:
        position: Position dict with 'x' and 'y' coordinates, optional 'unit'
        net: Net name to assign to this via
        viaType: Optional via type - 'through' (default), 'blind', or 'buried'
    """
    try:
        params = {
            "position": position,
            "net": net
        }
        if viaType:
            params["viaType"] = viaType
        return routing_commands.add_via(params)
    except Exception as e:
        logger.error(f"Error adding via: {e}")
        raise ToolError(f"Failed to add via: {str(e)}")


@mcp.tool
def add_copper_pour(
    layer: Annotated[str, Field(description="PCB layer for the copper pour")],
    net: Annotated[str, Field(description="Net name (typically 'GND' or power net)")],
    clearance: Annotated[float | None, Field(description="Clearance in mm")] = None
) -> Dict[str, Any]:
    """Add a copper pour (ground/power plane) to the PCB.

    Args:
        layer: PCB layer name (e.g., 'F.Cu', 'B.Cu')
        net: Net name for this copper pour (typically 'GND', 'VCC', '+3V3', etc.)
        clearance: Optional clearance value in millimeters
    """
    try:
        params = {
            "layer": layer,
            "net": net
        }
        if clearance is not None:
            params["clearance"] = clearance
        return routing_commands.add_copper_pour(params)
    except Exception as e:
        logger.error(f"Error adding copper pour: {e}")
        raise ToolError(f"Failed to add copper pour: {str(e)}")


# ============================================================================
# REMAINING BOARD TOOLS
# ============================================================================

@mcp.tool
def add_layer(
    name: Annotated[str, Field(description="Layer name")],
    type: Annotated[Literal["copper", "technical", "user", "signal"], Field(description="Layer type")],
    position: Annotated[Literal["top", "bottom", "inner"], Field(description="Layer position")],
    number: Annotated[int | None, Field(description="Layer number (for inner layers)")] = None
) -> Dict[str, Any]:
    """Add a new layer to the PCB board.

    Args:
        name: Name of the layer
        type: Type of layer (copper, technical, user, signal)
        position: Position of layer (top, bottom, inner)
        number: Optional layer number for inner layers
    """
    try:
        params = {
            "name": name,
            "type": type,
            "position": position
        }
        if number is not None:
            params["number"] = number
        return board_commands.add_layer(params)
    except Exception as e:
        logger.error(f"Error adding layer: {e}")
        raise ToolError(f"Failed to add layer: {str(e)}")


@mcp.tool
def set_active_layer(
    layer: Annotated[str, Field(description="Layer name to set as active")]
) -> Dict[str, Any]:
    """Set the active layer for PCB operations.

    Args:
        layer: Name of the layer to activate (e.g., 'F.Cu', 'B.Cu', 'F.SilkS')
    """
    try:
        return board_commands.set_active_layer({"layer": layer})
    except Exception as e:
        logger.error(f"Error setting active layer: {e}")
        raise ToolError(f"Failed to set active layer: {str(e)}")


@mcp.tool
def get_board_info() -> Dict[str, Any]:
    """Get information about the current PCB board.

    Returns board properties including dimensions, layer count, component count, etc.
    """
    try:
        return board_commands.get_board_info({})
    except Exception as e:
        logger.error(f"Error getting board info: {e}")
        raise ToolError(f"Failed to get board info: {str(e)}")


@mcp.tool
def get_layer_list() -> Dict[str, Any]:
    """Get a list of all layers in the PCB board.

    Returns all layer names, types, and properties.
    """
    try:
        return board_commands.get_layer_list({})
    except Exception as e:
        logger.error(f"Error getting layer list: {e}")
        raise ToolError(f"Failed to get layer list: {str(e)}")


@mcp.tool
def add_mounting_hole(
    position: Annotated[Dict[str, Any], Field(description="Position with x, y coordinates and unit")],
    diameter: Annotated[float, Field(description="Diameter of the hole in mm or inches")],
    padDiameter: Annotated[float | None, Field(description="Optional diameter of the pad around the hole")] = None
) -> Dict[str, Any]:
    """Add a mounting hole to the PCB board.

    Args:
        position: Dictionary with 'x', 'y', and 'unit' keys
        diameter: Hole diameter
        padDiameter: Optional pad diameter (defaults to 2x hole diameter)
    """
    try:
        params = {
            "position": position,
            "diameter": diameter
        }
        if padDiameter is not None:
            params["padDiameter"] = padDiameter
        return board_commands.add_mounting_hole(params)
    except Exception as e:
        logger.error(f"Error adding mounting hole: {e}")
        raise ToolError(f"Failed to add mounting hole: {str(e)}")


@mcp.tool
def add_board_text(
    text: Annotated[str, Field(description="Text content to add")],
    position: Annotated[Dict[str, Any], Field(description="Position with x, y coordinates and unit")],
    layer: Annotated[str, Field(description="Layer to place the text on")],
    size: Annotated[float, Field(description="Text size in mm")],
    thickness: Annotated[float | None, Field(description="Line thickness in mm")] = None,
    rotation: Annotated[float | None, Field(description="Rotation angle in degrees")] = None,
    style: Annotated[Literal["normal", "italic", "bold"] | None, Field(description="Text style")] = None
) -> Dict[str, Any]:
    """Add text annotation to the PCB board.

    Args:
        text: Text string to add
        position: Dictionary with 'x', 'y', and 'unit' keys
        layer: Layer name (e.g., 'F.SilkS', 'B.SilkS', 'Dwgs.User')
        size: Text height in mm
        thickness: Optional line thickness
        rotation: Optional rotation angle (0-360 degrees)
        style: Optional text style (normal, italic, bold)
    """
    try:
        params = {
            "text": text,
            "position": position,
            "layer": layer,
            "size": size
        }
        if thickness is not None:
            params["thickness"] = thickness
        if rotation is not None:
            params["rotation"] = rotation
        if style is not None:
            params["style"] = style
        return board_commands.add_text(params)
    except Exception as e:
        logger.error(f"Error adding board text: {e}")
        raise ToolError(f"Failed to add board text: {str(e)}")


@mcp.tool
def add_zone(
    layer: Annotated[str, Field(description="Layer for the zone (e.g., 'F.Cu', 'B.Cu')")],
    net: Annotated[str, Field(description="Net name for the zone (e.g., 'GND', 'VCC')")],
    points: Annotated[list[Dict[str, float]], Field(description="Array of points defining the zone outline")],
    unit: Annotated[Literal["mm", "inch"], Field(description="Unit of measurement for coordinates")],
    clearance: Annotated[float | None, Field(description="Clearance value in mm")] = None,
    minWidth: Annotated[float | None, Field(description="Minimum width in mm")] = None,
    padConnection: Annotated[Literal["thermal", "solid", "none"] | None, Field(description="Pad connection type")] = None
) -> Dict[str, Any]:
    """Add a copper pour zone to the PCB board.

    Args:
        layer: Layer name for the zone
        net: Net name to assign to the zone
        points: List of coordinate dictionaries with 'x' and 'y' keys (at least 3 points)
        unit: Unit of measurement for coordinates
        clearance: Optional clearance distance from other objects
        minWidth: Optional minimum width for zone fills
        padConnection: Optional pad connection type (thermal relief, solid, or none)
    """
    try:
        params = {
            "layer": layer,
            "net": net,
            "points": points,
            "unit": unit
        }
        if clearance is not None:
            params["clearance"] = clearance
        if minWidth is not None:
            params["minWidth"] = minWidth
        if padConnection is not None:
            params["padConnection"] = padConnection
        return routing_commands.add_copper_pour(params)
    except Exception as e:
        logger.error(f"Error adding zone: {e}")
        raise ToolError(f"Failed to add zone: {str(e)}")


@mcp.tool
def get_board_extents(
    unit: Annotated[Literal["mm", "inch"] | None, Field(description="Unit of measurement for the result")] = None
) -> Dict[str, Any]:
    """Get the bounding box extents of the PCB board.

    Returns the minimum and maximum x,y coordinates that encompass all board elements.

    Args:
        unit: Optional unit of measurement (defaults to mm)
    """
    try:
        params = {}
        if unit is not None:
            params["unit"] = unit
        return board_commands.get_board_extents(params)
    except Exception as e:
        logger.error(f"Error getting board extents: {e}")
        raise ToolError(f"Failed to get board extents: {str(e)}")


@mcp.tool
def get_board_2d_view(
    layers: Annotated[list[str] | None, Field(description="Optional array of layer names to include")] = None,
    width: Annotated[int | None, Field(description="Optional width of the image in pixels")] = None,
    height: Annotated[int | None, Field(description="Optional height of the image in pixels")] = None,
    format: Annotated[Literal["png", "jpg", "svg"] | None, Field(description="Image format")] = None
) -> Dict[str, Any]:
    """Get a 2D rendered view of the PCB board.

    Returns an image of the board showing specified layers.

    Args:
        layers: Optional list of layer names to render (default: all visible layers)
        width: Optional image width in pixels
        height: Optional image height in pixels
        format: Optional image format (default: png)
    """
    try:
        params = {}
        if layers is not None:
            params["layers"] = layers
        if width is not None:
            params["width"] = width
        if height is not None:
            params["height"] = height
        if format is not None:
            params["format"] = format
        return board_commands.get_board_2d_view(params)
    except Exception as e:
        logger.error(f"Error getting board 2D view: {e}")
        raise ToolError(f"Failed to get board 2D view: {str(e)}")


# ============================================================================
# DESIGN RULE TOOLS
# ============================================================================

@mcp.tool
def set_design_rules(
    clearance: Annotated[float | None, Field(description="Minimum clearance between copper items (mm)")] = None,
    trackWidth: Annotated[float | None, Field(description="Default track width (mm)")] = None,
    viaDiameter: Annotated[float | None, Field(description="Default via diameter (mm)")] = None,
    viaDrill: Annotated[float | None, Field(description="Default via drill size (mm)")] = None,
    microViaDiameter: Annotated[float | None, Field(description="Default micro via diameter (mm)")] = None,
    microViaDrill: Annotated[float | None, Field(description="Default micro via drill size (mm)")] = None,
    minTrackWidth: Annotated[float | None, Field(description="Minimum track width (mm)")] = None,
    minViaDiameter: Annotated[float | None, Field(description="Minimum via diameter (mm)")] = None,
    minViaDrill: Annotated[float | None, Field(description="Minimum via drill size (mm)")] = None,
    minMicroViaDiameter: Annotated[float | None, Field(description="Minimum micro via diameter (mm)")] = None,
    minMicroViaDrill: Annotated[float | None, Field(description="Minimum micro via drill size (mm)")] = None,
    minHoleDiameter: Annotated[float | None, Field(description="Minimum hole diameter (mm)")] = None,
    requireCourtyard: Annotated[bool | None, Field(description="Whether to require courtyards for all footprints")] = None,
    courtyardClearance: Annotated[float | None, Field(description="Minimum clearance between courtyards (mm)")] = None
) -> Dict[str, Any]:
    """Set design rule parameters for the PCB."""
    try:
        params = {}
        if clearance is not None:
            params["clearance"] = clearance
        if trackWidth is not None:
            params["trackWidth"] = trackWidth
        if viaDiameter is not None:
            params["viaDiameter"] = viaDiameter
        if viaDrill is not None:
            params["viaDrill"] = viaDrill
        if microViaDiameter is not None:
            params["microViaDiameter"] = microViaDiameter
        if microViaDrill is not None:
            params["microViaDrill"] = microViaDrill
        if minTrackWidth is not None:
            params["minTrackWidth"] = minTrackWidth
        if minViaDiameter is not None:
            params["minViaDiameter"] = minViaDiameter
        if minViaDrill is not None:
            params["minViaDrill"] = minViaDrill
        if minMicroViaDiameter is not None:
            params["minMicroViaDiameter"] = minMicroViaDiameter
        if minMicroViaDrill is not None:
            params["minMicroViaDrill"] = minMicroViaDrill
        if minHoleDiameter is not None:
            params["minHoleDiameter"] = minHoleDiameter
        if requireCourtyard is not None:
            params["requireCourtyard"] = requireCourtyard
        if courtyardClearance is not None:
            params["courtyardClearance"] = courtyardClearance
        return design_rule_commands.set_design_rules(params)
    except Exception as e:
        logger.error(f"Error setting design rules: {e}")
        raise ToolError(f"Failed to set design rules: {str(e)}")


@mcp.tool
def get_design_rules() -> Dict[str, Any]:
    """Get the current design rule parameters from the PCB."""
    try:
        return design_rule_commands.get_design_rules({})
    except Exception as e:
        logger.error(f"Error getting design rules: {e}")
        raise ToolError(f"Failed to get design rules: {str(e)}")


@mcp.tool
def run_drc(
    reportPath: Annotated[str | None, Field(description="Optional path to save the DRC report")] = None
) -> Dict[str, Any]:
    """Run Design Rule Check (DRC) on the current PCB."""
    try:
        params = {}
        if reportPath:
            params["reportPath"] = reportPath
        return design_rule_commands.run_drc(params)
    except Exception as e:
        logger.error(f"Error running DRC: {e}")
        raise ToolError(f"Failed to run DRC: {str(e)}")


@mcp.tool
def get_drc_violations(
    severity: Annotated[Literal["error", "warning", "all"] | None, Field(description="Filter violations by severity")] = None,
    limit: Annotated[int | None, Field(description="Maximum number of violations to return (default: 100, max: 500)")] = None,
    offset: Annotated[int | None, Field(description="Number of violations to skip for pagination (default: 0)")] = None,
    summary_only: Annotated[bool | None, Field(description="If True, return only summary without violations list (default: False)")] = None
) -> Dict[str, Any]:
    """Get list of DRC violations from the current board.

    For large result sets (>100 violations), this automatically returns only summary
    statistics and the file path. Use limit/offset parameters to paginate through results,
    or read the violations file directly with the Read tool."""
    try:
        params = {}
        if severity:
            params["severity"] = severity
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if summary_only is not None:
            params["summary_only"] = summary_only
        return design_rule_commands.get_drc_violations(params)
    except Exception as e:
        logger.error(f"Error getting DRC violations: {e}")
        raise ToolError(f"Failed to get DRC violations: {str(e)}")


# ============================================================================
# EXPORT TOOLS
# ============================================================================

@mcp.tool
def export_gerber(
    outputDir: Annotated[str, Field(description="Directory to save Gerber files")],
    layers: Annotated[list[str] | None, Field(description="Optional array of layer names to export")] = None,
    useProtelExtensions: Annotated[bool | None, Field(description="Use Protel filename extensions")] = None,
    generateDrillFiles: Annotated[bool | None, Field(description="Generate drill files")] = None,
    generateMapFile: Annotated[bool | None, Field(description="Generate a map file")] = None,
    useAuxOrigin: Annotated[bool | None, Field(description="Use auxiliary axis as origin")] = None
) -> Dict[str, Any]:
    """Export Gerber manufacturing files."""
    try:
        params = {"outputDir": outputDir}
        if layers is not None:
            params["layers"] = layers
        if useProtelExtensions is not None:
            params["useProtelExtensions"] = useProtelExtensions
        if generateDrillFiles is not None:
            params["generateDrillFiles"] = generateDrillFiles
        if generateMapFile is not None:
            params["generateMapFile"] = generateMapFile
        if useAuxOrigin is not None:
            params["useAuxOrigin"] = useAuxOrigin
        return export_commands.export_gerber(params)
    except Exception as e:
        logger.error(f"Error exporting Gerber: {e}")
        raise ToolError(f"Failed to export Gerber: {str(e)}")


@mcp.tool
def export_pdf(
    outputPath: Annotated[str, Field(description="Path to save the PDF file")],
    layers: Annotated[list[str] | None, Field(description="Optional array of layer names to include")] = None,
    blackAndWhite: Annotated[bool | None, Field(description="Export in black and white")] = None,
    frameReference: Annotated[bool | None, Field(description="Include frame reference")] = None,
    pageSize: Annotated[Literal["A4", "A3", "A2", "A1", "A0", "Letter", "Legal", "Tabloid"] | None, Field(description="Page size")] = None
) -> Dict[str, Any]:
    """Export PDF document of the PCB."""
    try:
        params = {"outputPath": outputPath}
        if layers is not None:
            params["layers"] = layers
        if blackAndWhite is not None:
            params["blackAndWhite"] = blackAndWhite
        if frameReference is not None:
            params["frameReference"] = frameReference
        if pageSize is not None:
            params["pageSize"] = pageSize
        return export_commands.export_pdf(params)
    except Exception as e:
        logger.error(f"Error exporting PDF: {e}")
        raise ToolError(f"Failed to export PDF: {str(e)}")


@mcp.tool
def export_svg(
    outputPath: Annotated[str, Field(description="Path to save the SVG file")],
    layers: Annotated[list[str] | None, Field(description="Optional array of layer names to include")] = None,
    blackAndWhite: Annotated[bool | None, Field(description="Export in black and white")] = None,
    includeComponents: Annotated[bool | None, Field(description="Include component outlines")] = None
) -> Dict[str, Any]:
    """Export SVG graphics of the PCB."""
    try:
        params = {"outputPath": outputPath}
        if layers is not None:
            params["layers"] = layers
        if blackAndWhite is not None:
            params["blackAndWhite"] = blackAndWhite
        if includeComponents is not None:
            params["includeComponents"] = includeComponents
        return export_commands.export_svg(params)
    except Exception as e:
        logger.error(f"Error exporting SVG: {e}")
        raise ToolError(f"Failed to export SVG: {str(e)}")


@mcp.tool
def export_3d(
    outputPath: Annotated[str, Field(description="Path to save the 3D model file")],
    format: Annotated[Literal["STEP", "STL", "VRML", "OBJ"], Field(description="3D model format")],
    includeComponents: Annotated[bool | None, Field(description="Include 3D component models")] = None,
    includeCopper: Annotated[bool | None, Field(description="Include copper layers")] = None,
    includeSolderMask: Annotated[bool | None, Field(description="Include solder mask")] = None,
    includeSilkscreen: Annotated[bool | None, Field(description="Include silkscreen")] = None
) -> Dict[str, Any]:
    """Export 3D model of the PCB."""
    try:
        params = {"outputPath": outputPath, "format": format}
        if includeComponents is not None:
            params["includeComponents"] = includeComponents
        if includeCopper is not None:
            params["includeCopper"] = includeCopper
        if includeSolderMask is not None:
            params["includeSolderMask"] = includeSolderMask
        if includeSilkscreen is not None:
            params["includeSilkscreen"] = includeSilkscreen
        return export_commands.export_3d(params)
    except Exception as e:
        logger.error(f"Error exporting 3D: {e}")
        raise ToolError(f"Failed to export 3D: {str(e)}")


@mcp.tool
def export_bom(
    outputPath: Annotated[str, Field(description="Path to save the BOM file")],
    format: Annotated[Literal["CSV", "XML", "HTML", "JSON"], Field(description="BOM file format")],
    groupByValue: Annotated[bool | None, Field(description="Group components by value")] = None,
    includeAttributes: Annotated[list[str] | None, Field(description="Additional attributes to include")] = None
) -> Dict[str, Any]:
    """Export Bill of Materials (BOM)."""
    try:
        params = {"outputPath": outputPath, "format": format}
        if groupByValue is not None:
            params["groupByValue"] = groupByValue
        if includeAttributes is not None:
            params["includeAttributes"] = includeAttributes
        return export_commands.export_bom(params)
    except Exception as e:
        logger.error(f"Error exporting BOM: {e}")
        raise ToolError(f"Failed to export BOM: {str(e)}")


# ============================================================================
# UI MANAGEMENT TOOLS
# ============================================================================

@mcp.tool
def check_kicad_ui() -> Dict[str, Any]:
    """Check if KiCAD UI is currently running."""
    try:
        manager = KiCADProcessManager()
        is_running = manager.is_running()
        processes = manager.get_process_info() if is_running else []

        return {
            "success": True,
            "running": is_running,
            "processes": processes,
            "message": "KiCAD is running" if is_running else "KiCAD is not running"
        }
    except Exception as e:
        logger.error(f"Error checking KiCAD UI: {e}")
        raise ToolError(f"Failed to check KiCAD UI: {str(e)}")


@mcp.tool
def launch_kicad_ui(
    projectPath: Annotated[str | None, Field(description="Optional path to project file to open")] = None,
    autoLaunch: Annotated[bool, Field(description="Whether to auto-launch if not running")] = False
) -> Dict[str, Any]:
    """Launch KiCAD UI application."""
    try:
        path_obj = Path(projectPath) if projectPath else None
        result = check_and_launch_kicad(path_obj, autoLaunch)

        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"Error launching KiCAD UI: {e}")
        raise ToolError(f"Failed to launch KiCAD UI: {str(e)}")


# ============================================================================
# DISTRIBUTOR TOOLS
# ============================================================================

@mcp.tool
async def search_component(
    query: Annotated[str, Field(description="MPN or keyword to search for")],
    distributors: Annotated[list[str] | None, Field(description="Optional list of distributors to search (mouser, digikey, octopart)")] = None
) -> Dict[str, Any]:
    """Search for components by MPN or keyword across Mouser, DigiKey, and Octopart."""
    try:
        params = {"query": query}
        if distributors is not None:
            params["distributors"] = distributors
        return await distributor_commands.search_component(params)
    except Exception as e:
        logger.error(f"Error searching component: {e}")
        raise ToolError(f"Failed to search component: {str(e)}")


@mcp.tool
async def get_component_availability(
    mpn: Annotated[str, Field(description="Manufacturer part number")],
    distributors: Annotated[list[str] | None, Field(description="Optional list of distributors to check")] = None
) -> Dict[str, Any]:
    """Get detailed availability and pricing for a specific component."""
    try:
        params = {"mpn": mpn}
        if distributors is not None:
            params["distributors"] = distributors
        return await distributor_commands.get_component_availability(params)
    except Exception as e:
        logger.error(f"Error getting component availability: {e}")
        raise ToolError(f"Failed to get component availability: {str(e)}")


@mcp.tool
async def check_bom_availability(
    bomPath: Annotated[str | None, Field(description="Optional path to BOM file")] = None
) -> Dict[str, Any]:
    """Check availability and pricing for all components in the current BOM."""
    try:
        params = {}
        if bomPath is not None:
            params["bomPath"] = bomPath
        return await distributor_commands.check_bom_availability(params)
    except Exception as e:
        logger.error(f"Error checking BOM availability: {e}")
        raise ToolError(f"Failed to check BOM availability: {str(e)}")


@mcp.tool
async def find_component_alternatives(
    mpn: Annotated[str, Field(description="Manufacturer part number to find alternatives for")],
    reason: Annotated[str, Field(description="Reason for finding alternatives (obsolete, out of stock, cost reduction, etc.)")]
) -> Dict[str, Any]:
    """Find alternative components for a specific part."""
    try:
        return await distributor_commands.find_component_alternatives({
            "mpn": mpn,
            "reason": reason
        })
    except Exception as e:
        logger.error(f"Error finding component alternatives: {e}")
        raise ToolError(f"Failed to find component alternatives: {str(e)}")


@mcp.tool
async def validate_bom_lifecycle(
    bomPath: Annotated[str | None, Field(description="Optional path to BOM file")] = None
) -> Dict[str, Any]:
    """Validate lifecycle status of all components in the BOM."""
    try:
        params = {}
        if bomPath is not None:
            params["bomPath"] = bomPath
        return await distributor_commands.validate_bom_lifecycle(params)
    except Exception as e:
        logger.error(f"Error validating BOM lifecycle: {e}")
        raise ToolError(f"Failed to validate BOM lifecycle: {str(e)}")


@mcp.tool
async def compare_distributor_pricing(
    mpn: Annotated[str, Field(description="Manufacturer part number")]
) -> Dict[str, Any]:
    """Compare pricing across different distributors for a component."""
    try:
        return await distributor_commands.compare_distributor_pricing({"mpn": mpn})
    except Exception as e:
        logger.error(f"Error comparing distributor pricing: {e}")
        raise ToolError(f"Failed to compare distributor pricing: {str(e)}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("FastMCP Server Ready - Starting STDIO transport")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 70)

    # Run the server with STDIO transport (default)
    mcp.run()
