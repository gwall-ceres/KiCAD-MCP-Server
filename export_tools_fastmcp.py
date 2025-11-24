#!/usr/bin/env python3
"""
Export Tools for KiCAD FastMCP Server
Converted from TypeScript to Python FastMCP

These tools handle exporting PCB data to various formats including:
- Gerber files
- PDF documents
- SVG graphics
- 3D models (STEP, STL, VRML, OBJ)
- Bill of Materials (BOM)
- Netlists
- Position files
- VRML models
"""

from typing import Literal, Annotated, Dict, Any, List
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field
import logging

logger = logging.getLogger('kicad_fastmcp')

# Assuming export_commands is initialized globally in mcp_server.py
# from commands.export import ExportCommands
# export_commands = ExportCommands(board)


def register_export_tools(mcp: FastMCP, export_commands):
    """Register all export tools with the FastMCP server

    Args:
        mcp: FastMCP server instance
        export_commands: ExportCommands instance
    """

    # ============================================================================
    # EXPORT GERBER TOOL
    # ============================================================================

    @mcp.tool
    def export_gerber(
        outputDir: Annotated[str, Field(description="Directory to save Gerber files")],
        layers: Annotated[List[str] | None, Field(description="Optional array of layer names to export (default: all)")] = None,
        useProtelExtensions: Annotated[bool | None, Field(description="Whether to use Protel filename extensions")] = None,
        generateDrillFiles: Annotated[bool | None, Field(description="Whether to generate drill files")] = None,
        generateMapFile: Annotated[bool | None, Field(description="Whether to generate a map file")] = None,
        useAuxOrigin: Annotated[bool | None, Field(description="Whether to use auxiliary axis as origin")] = None
    ) -> Dict[str, Any]:
        """Export Gerber files for PCB manufacturing.

        Gerber files are the industry standard for PCB fabrication. This tool
        generates all necessary fabrication files including copper layers,
        solder mask, silkscreen, and drill files.

        Args:
            outputDir: Directory to save Gerber files
            layers: Optional array of layer names to export (default: all)
            useProtelExtensions: Whether to use Protel filename extensions
            generateDrillFiles: Whether to generate drill files
            generateMapFile: Whether to generate a map file
            useAuxOrigin: Whether to use auxiliary axis as origin

        Returns:
            Dict with success status, generated files list, and output directory
        """
        try:
            logger.debug(f"Exporting Gerber files to: {outputDir}")

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

            result = export_commands.export_gerber(params)

            if not result.get("success"):
                raise ToolError(result.get("message", "Gerber export failed"))

            return result
        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Error exporting Gerber files: {e}")
            raise ToolError(f"Failed to export Gerber files: {str(e)}")


    # ============================================================================
    # EXPORT PDF TOOL
    # ============================================================================

    @mcp.tool
    def export_pdf(
        outputPath: Annotated[str, Field(description="Path to save the PDF file")],
        layers: Annotated[List[str] | None, Field(description="Optional array of layer names to include (default: all)")] = None,
        blackAndWhite: Annotated[bool | None, Field(description="Whether to export in black and white")] = None,
        frameReference: Annotated[bool | None, Field(description="Whether to include frame reference")] = None,
        pageSize: Annotated[
            Literal["A4", "A3", "A2", "A1", "A0", "Letter", "Legal", "Tabloid"] | None,
            Field(description="Page size")
        ] = None
    ) -> Dict[str, Any]:
        """Export PCB layout to PDF document.

        Creates a PDF document containing the specified PCB layers. Useful for
        documentation, design reviews, and archival purposes.

        Args:
            outputPath: Path to save the PDF file
            layers: Optional array of layer names to include (default: all)
            blackAndWhite: Whether to export in black and white
            frameReference: Whether to include frame reference
            pageSize: Page size (A4, A3, A2, A1, A0, Letter, Legal, Tabloid)

        Returns:
            Dict with success status, file path, and export details
        """
        try:
            logger.debug(f"Exporting PDF to: {outputPath}")

            params = {"outputPath": outputPath}
            if layers is not None:
                params["layers"] = layers
            if blackAndWhite is not None:
                params["blackAndWhite"] = blackAndWhite
            if frameReference is not None:
                params["frameReference"] = frameReference
            if pageSize is not None:
                params["pageSize"] = pageSize

            result = export_commands.export_pdf(params)

            if not result.get("success"):
                raise ToolError(result.get("message", "PDF export failed"))

            return result
        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Error exporting PDF: {e}")
            raise ToolError(f"Failed to export PDF: {str(e)}")


    # ============================================================================
    # EXPORT SVG TOOL
    # ============================================================================

    @mcp.tool
    def export_svg(
        outputPath: Annotated[str, Field(description="Path to save the SVG file")],
        layers: Annotated[List[str] | None, Field(description="Optional array of layer names to include (default: all)")] = None,
        blackAndWhite: Annotated[bool | None, Field(description="Whether to export in black and white")] = None,
        includeComponents: Annotated[bool | None, Field(description="Whether to include component outlines")] = None
    ) -> Dict[str, Any]:
        """Export PCB layout to SVG (Scalable Vector Graphics) format.

        Creates vector graphics files that can be used in documentation, web pages,
        or further edited in vector graphics software.

        Args:
            outputPath: Path to save the SVG file
            layers: Optional array of layer names to include (default: all)
            blackAndWhite: Whether to export in black and white
            includeComponents: Whether to include component outlines

        Returns:
            Dict with success status and file path
        """
        try:
            logger.debug(f"Exporting SVG to: {outputPath}")

            params = {"outputPath": outputPath}
            if layers is not None:
                params["layers"] = layers
            if blackAndWhite is not None:
                params["blackAndWhite"] = blackAndWhite
            if includeComponents is not None:
                params["includeComponents"] = includeComponents

            result = export_commands.export_svg(params)

            if not result.get("success"):
                raise ToolError(result.get("message", "SVG export failed"))

            return result
        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Error exporting SVG: {e}")
            raise ToolError(f"Failed to export SVG: {str(e)}")


    # ============================================================================
    # EXPORT 3D MODEL TOOL
    # ============================================================================

    @mcp.tool
    def export_3d(
        outputPath: Annotated[str, Field(description="Path to save the 3D model file")],
        format: Annotated[
            Literal["STEP", "STL", "VRML", "OBJ"],
            Field(description="3D model format")
        ],
        includeComponents: Annotated[bool | None, Field(description="Whether to include 3D component models")] = None,
        includeCopper: Annotated[bool | None, Field(description="Whether to include copper layers")] = None,
        includeSolderMask: Annotated[bool | None, Field(description="Whether to include solder mask")] = None,
        includeSilkscreen: Annotated[bool | None, Field(description="Whether to include silkscreen")] = None
    ) -> Dict[str, Any]:
        """Export 3D model of the PCB in various formats.

        Creates 3D models suitable for mechanical CAD integration, visualization,
        or 3D printing. STEP format is recommended for mechanical design integration.

        Args:
            outputPath: Path to save the 3D model file
            format: 3D model format (STEP, STL, VRML, OBJ)
            includeComponents: Whether to include 3D component models
            includeCopper: Whether to include copper layers
            includeSolderMask: Whether to include solder mask
            includeSilkscreen: Whether to include silkscreen

        Returns:
            Dict with success status and file path
        """
        try:
            logger.debug(f"Exporting 3D model to: {outputPath} (format: {format})")

            params = {
                "outputPath": outputPath,
                "format": format
            }
            if includeComponents is not None:
                params["includeComponents"] = includeComponents
            if includeCopper is not None:
                params["includeCopper"] = includeCopper
            if includeSolderMask is not None:
                params["includeSolderMask"] = includeSolderMask
            if includeSilkscreen is not None:
                params["includeSilkscreen"] = includeSilkscreen

            result = export_commands.export_3d(params)

            if not result.get("success"):
                raise ToolError(result.get("message", "3D model export failed"))

            return result
        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Error exporting 3D model: {e}")
            raise ToolError(f"Failed to export 3D model: {str(e)}")


    # ============================================================================
    # EXPORT BOM TOOL
    # ============================================================================

    @mcp.tool
    def export_bom(
        outputPath: Annotated[str, Field(description="Path to save the BOM file")],
        format: Annotated[
            Literal["CSV", "XML", "HTML", "JSON"],
            Field(description="BOM file format")
        ],
        groupByValue: Annotated[bool | None, Field(description="Whether to group components by value")] = None,
        includeAttributes: Annotated[
            List[str] | None,
            Field(description="Optional array of additional attributes to include")
        ] = None
    ) -> Dict[str, Any]:
        """Export Bill of Materials (BOM) listing all components.

        Generates a BOM file in various formats for procurement, assembly, and
        documentation. Can group identical components and include custom attributes.

        Args:
            outputPath: Path to save the BOM file
            format: BOM file format (CSV, XML, HTML, JSON)
            groupByValue: Whether to group components by value
            includeAttributes: Optional array of additional attributes to include

        Returns:
            Dict with success status, file path, and component count
        """
        try:
            logger.debug(f"Exporting BOM to: {outputPath} (format: {format})")

            params = {
                "outputPath": outputPath,
                "format": format
            }
            if groupByValue is not None:
                params["groupByValue"] = groupByValue
            if includeAttributes is not None:
                params["includeAttributes"] = includeAttributes

            result = export_commands.export_bom(params)

            if not result.get("success"):
                raise ToolError(result.get("message", "BOM export failed"))

            return result
        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Error exporting BOM: {e}")
            raise ToolError(f"Failed to export BOM: {str(e)}")


    # ============================================================================
    # EXPORT NETLIST TOOL
    # ============================================================================

    @mcp.tool
    def export_netlist(
        outputPath: Annotated[str, Field(description="Path to save the netlist file")],
        format: Annotated[
            Literal["KiCad", "Spice", "Cadstar", "OrcadPCB2"] | None,
            Field(description="Netlist format (default: KiCad)")
        ] = None
    ) -> Dict[str, Any]:
        """Export netlist describing electrical connections.

        Creates a netlist file showing all electrical connections between components.
        Useful for simulation, PCB layout, and design verification.

        Args:
            outputPath: Path to save the netlist file
            format: Netlist format (KiCad, Spice, Cadstar, OrcadPCB2)

        Returns:
            Dict with success status and file path
        """
        try:
            logger.debug(f"Exporting netlist to: {outputPath}")

            params = {"outputPath": outputPath}
            if format is not None:
                params["format"] = format

            # Check if export_netlist exists in export_commands
            if not hasattr(export_commands, 'export_netlist'):
                raise ToolError(
                    "export_netlist not implemented in backend. "
                    "This method needs to be added to commands/export.py"
                )

            result = export_commands.export_netlist(params)

            if not result.get("success"):
                raise ToolError(result.get("message", "Netlist export failed"))

            return result
        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Error exporting netlist: {e}")
            raise ToolError(f"Failed to export netlist: {str(e)}")


    # ============================================================================
    # EXPORT POSITION FILE TOOL
    # ============================================================================

    @mcp.tool
    def export_position_file(
        outputPath: Annotated[str, Field(description="Path to save the position file")],
        format: Annotated[
            Literal["CSV", "ASCII"] | None,
            Field(description="File format (default: CSV)")
        ] = None,
        units: Annotated[
            Literal["mm", "inch"] | None,
            Field(description="Units to use (default: mm)")
        ] = None,
        side: Annotated[
            Literal["top", "bottom", "both"] | None,
            Field(description="Which board side to include (default: both)")
        ] = None
    ) -> Dict[str, Any]:
        """Export component position file for assembly machines.

        Creates a position file (also called pick-and-place file) containing
        X/Y coordinates and rotation for all components. Used by automated
        assembly equipment.

        Args:
            outputPath: Path to save the position file
            format: File format (CSV or ASCII)
            units: Units to use (mm or inch)
            side: Which board side to include (top, bottom, or both)

        Returns:
            Dict with success status and file path
        """
        try:
            logger.debug(f"Exporting position file to: {outputPath}")

            params = {"outputPath": outputPath}
            if format is not None:
                params["format"] = format
            if units is not None:
                params["units"] = units
            if side is not None:
                params["side"] = side

            # Check if export_position_file exists in export_commands
            if not hasattr(export_commands, 'export_position_file'):
                raise ToolError(
                    "export_position_file not implemented in backend. "
                    "This method needs to be added to commands/export.py"
                )

            result = export_commands.export_position_file(params)

            if not result.get("success"):
                raise ToolError(result.get("message", "Position file export failed"))

            return result
        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Error exporting position file: {e}")
            raise ToolError(f"Failed to export position file: {str(e)}")


    # ============================================================================
    # EXPORT VRML TOOL
    # ============================================================================

    @mcp.tool
    def export_vrml(
        outputPath: Annotated[str, Field(description="Path to save the VRML file")],
        includeComponents: Annotated[bool | None, Field(description="Whether to include 3D component models")] = None,
        useRelativePaths: Annotated[bool | None, Field(description="Whether to use relative paths for 3D models")] = None
    ) -> Dict[str, Any]:
        """Export 3D model in VRML format.

        VRML (Virtual Reality Modeling Language) is a legacy 3D format still
        used by some visualization and simulation tools.

        Args:
            outputPath: Path to save the VRML file
            includeComponents: Whether to include 3D component models
            useRelativePaths: Whether to use relative paths for 3D models

        Returns:
            Dict with success status and file path
        """
        try:
            logger.debug(f"Exporting VRML to: {outputPath}")

            params = {"outputPath": outputPath}
            if includeComponents is not None:
                params["includeComponents"] = includeComponents
            if useRelativePaths is not None:
                params["useRelativePaths"] = useRelativePaths

            # Note: VRML export is handled by export_3d with format="VRML"
            # This is a convenience wrapper
            params["format"] = "VRML"

            result = export_commands.export_3d(params)

            if not result.get("success"):
                raise ToolError(result.get("message", "VRML export failed"))

            return result
        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Error exporting VRML: {e}")
            raise ToolError(f"Failed to export VRML: {str(e)}")


    logger.info("Registered 8 export tools")


# ============================================================================
# STANDALONE USAGE (if this file is used independently)
# ============================================================================

if __name__ == "__main__":
    print("This module provides export tools for KiCAD FastMCP Server.")
    print("It should be imported and used with register_export_tools(mcp, export_commands)")
    print("\nAvailable export tools:")
    print("  1. export_gerber       - Export Gerber files for manufacturing")
    print("  2. export_pdf          - Export PCB layout to PDF")
    print("  3. export_svg          - Export PCB layout to SVG")
    print("  4. export_3d           - Export 3D model (STEP/STL/VRML/OBJ)")
    print("  5. export_bom          - Export Bill of Materials")
    print("  6. export_netlist      - Export netlist (NOT YET IMPLEMENTED)")
    print("  7. export_position_file - Export position file (NOT YET IMPLEMENTED)")
    print("  8. export_vrml         - Export VRML 3D model")
