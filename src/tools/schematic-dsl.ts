/**
 * Schematic DSL tools for KiCAD MCP server
 *
 * Provides high-level schematic analysis using LLM-optimized DSL format.
 * Extracts circuit information from KiCAD schematics in a compact, structured format.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';

export function registerSchematicDSLTools(server: McpServer, callKicadScript: Function) {
  /**
   * Get schematic index - overview of all pages
   */
  server.tool(
    "get_schematic_index",
    "Get project-wide schematic index showing all pages, component counts, and inter-page signals. Use this first to understand the overall structure before diving into specific pages.",
    {
      project_path: z.string().describe("Path to KiCAD project directory containing .kicad_sch files"),
    },
    async (args: { project_path: string }) => {
      const result = await callKicadScript("get_schematic_index", args);

      if (result.success) {
        return {
          content: [{
            type: "text",
            text: result.index
          }]
        };
      } else {
        return {
          content: [{
            type: "text",
            text: `Error: ${result.error}\n\n${result.details || ''}`
          }],
          isError: true
        };
      }
    }
  );

  /**
   * Get schematic page - detailed DSL for specific page
   */
  server.tool(
    "get_schematic_page",
    "Get detailed DSL representation of a specific schematic page with components, pins, and nets. The DSL format is ~10x more compact than raw KiCAD data while preserving all essential circuit information.",
    {
      project_path: z.string().describe("Path to KiCAD project directory"),
      page_name: z.string().describe("Name of schematic page (without .kicad_sch extension), e.g., 'battery_charger', 'Power_Supplies'"),
    },
    async (args: { project_path: string; page_name: string }) => {
      const result = await callKicadScript("get_schematic_page", args);

      if (result.success) {
        return {
          content: [{
            type: "text",
            text: `# Page: ${result.page_name}\n\n${result.dsl}`
          }]
        };
      } else {
        const errorMsg = `Error: ${result.error}\n\n${result.hint || ''}\n\n${result.details || ''}`;
        return {
          content: [{
            type: "text",
            text: errorMsg
          }],
          isError: true
        };
      }
    }
  );

  /**
   * Get schematic context - component or net context
   */
  server.tool(
    "get_schematic_context",
    "Get contextual information about a specific component or net. Component mode shows connections and related nets. Net mode shows all components connected to a net across all pages. Useful for tracing signals and debugging connections.",
    {
      project_path: z.string().describe("Path to KiCAD project directory"),
      component_ref: z.string().optional().describe("Component designator to analyze (e.g., 'Q1', 'U200', 'R15')"),
      net_name: z.string().optional().describe("Net name to trace (e.g., 'GND', 'VBUS', '/battery_charger/CHARGER_VOUT')"),
    },
    async (args: { project_path: string; component_ref?: string; net_name?: string }) => {
      const result = await callKicadScript("get_schematic_context", args);

      if (result.success) {
        const header = result.context_type === 'component'
          ? `# Component Context: ${result.context_id}`
          : `# Net Context: ${result.context_id}`;

        return {
          content: [{
            type: "text",
            text: `${header}\n\n${result.context}`
          }]
        };
      } else {
        return {
          content: [{
            type: "text",
            text: `Error: ${result.error}\n\n${result.details || ''}`
          }],
          isError: true
        };
      }
    }
  );
}
