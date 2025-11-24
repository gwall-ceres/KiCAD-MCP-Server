/**
 * Distributor API tools for finding automotive/industrial component alternatives
 * Integrates with Mouser and DigiKey APIs to help find aviation-grade replacements
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { logger } from '../logger.js';

// Command function type for Python script calls
type CommandFunction = (command: string, params: Record<string, unknown>) => Promise<any>;

/**
 * Register distributor API tools with the MCP server
 *
 * @param server MCP server instance
 * @param callPythonScript Function to call Python distributor commands
 */
export function registerDistributorTools(server: McpServer, callPythonScript: CommandFunction): void {
  logger.info('Registering distributor API tools');

  // ------------------------------------------------------
  // Find Automotive Alternative Tool
  // ------------------------------------------------------
  server.tool(
    "find_automotive_alternative",
    {
      mpn: z.string().describe("Manufacturer part number to find alternative for (e.g., 'LM2596', 'SI4459BDY')"),
      requirements: z.object({
        temp_range: z.tuple([z.number(), z.number()]).optional()
          .describe("Temperature range [min, max] in Celsius (default: [-40, 125] for aviation)"),
        grades: z.array(z.enum(["automotive", "industrial", "military", "commercial"])).optional()
          .describe("Acceptable component grades (default: ['automotive', 'industrial'])"),
        min_stock: z.number().optional()
          .describe("Minimum stock level required (default: 0)"),
        same_footprint: z.boolean().optional()
          .describe("Require same footprint (default: true)"),
        max_price_increase_pct: z.number().optional()
          .describe("Maximum acceptable price increase percentage (default: 50)")
      }).optional().describe("Component requirements (default: aviation grade)")
    },
    async ({ mpn, requirements }) => {
      logger.debug(`Finding automotive alternative for: ${mpn}`);

      try {
        const result = await callPythonScript("find_automotive_alternative", {
          mpn,
          requirements: requirements || {
            temp_range: [-40, 125],
            grades: ["automotive", "industrial"]
          }
        });

        return {
          content: [{
            type: "text",
            text: JSON.stringify(result, null, 2)
          }]
        };
      } catch (error: any) {
        logger.error(`Error finding alternative for ${mpn}: ${error.message}`);
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: false,
              error: error.message,
              mpn
            }, null, 2)
          }]
        };
      }
    }
  );

  // ------------------------------------------------------
  // Check BOM Aviation Compliance Tool
  // ------------------------------------------------------
  server.tool(
    "check_bom_automotive_compliance",
    {
      temp_min: z.number().optional().describe("Minimum temperature requirement in Celsius (default: -40)"),
      temp_max: z.number().optional().describe("Maximum temperature requirement in Celsius (default: 125)"),
      required_grade: z.array(z.enum(["automotive", "industrial", "military"])).optional()
        .describe("Required component grades (default: ['automotive', 'industrial'])")
    },
    async ({ temp_min, temp_max, required_grade }) => {
      logger.debug('Checking BOM for automotive compliance');

      try {
        const result = await callPythonScript("check_bom_compliance", {
          temp_range: [temp_min || -40, temp_max || 125],
          required_grades: required_grade || ["automotive", "industrial"]
        });

        return {
          content: [{
            type: "text",
            text: JSON.stringify(result, null, 2)
          }]
        };
      } catch (error: any) {
        logger.error(`Error checking BOM compliance: ${error.message}`);
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: false,
              error: error.message
            }, null, 2)
          }]
        };
      }
    }
  );

  // ------------------------------------------------------
  // Search Component by MPN Tool
  // ------------------------------------------------------
  server.tool(
    "search_component",
    {
      mpn: z.string().describe("Manufacturer part number to search for"),
      distributors: z.array(z.enum(["mouser", "digikey", "both"])).optional()
        .describe("Which distributors to search (default: both)")
    },
    async ({ mpn, distributors }) => {
      logger.debug(`Searching for component: ${mpn}`);

      try {
        const result = await callPythonScript("search_component", {
          mpn,
          distributors: distributors || ["both"]
        });

        return {
          content: [{
            type: "text",
            text: JSON.stringify(result, null, 2)
          }]
        };
      } catch (error: any) {
        logger.error(`Error searching for ${mpn}: ${error.message}`);
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: false,
              error: error.message,
              mpn
            }, null, 2)
          }]
        };
      }
    }
  );

  // ------------------------------------------------------
  // Get Component Availability Tool
  // ------------------------------------------------------
  server.tool(
    "get_component_availability",
    {
      mpn: z.string().describe("Manufacturer part number to check availability for")
    },
    async ({ mpn }) => {
      logger.debug(`Checking availability for: ${mpn}`);

      try {
        const result = await callPythonScript("get_availability", {
          mpn
        });

        return {
          content: [{
            type: "text",
            text: JSON.stringify(result, null, 2)
          }]
        };
      } catch (error: any) {
        logger.error(`Error checking availability for ${mpn}: ${error.message}`);
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: false,
              error: error.message,
              mpn
            }, null, 2)
          }]
        };
      }
    }
  );

  // ------------------------------------------------------
  // Find BOM Automotive Alternatives Tool
  // ------------------------------------------------------
  server.tool(
    "find_bom_automotive_alternatives",
    {
      component_types: z.array(z.string()).optional()
        .describe("Component type prefixes to search (e.g., ['U', 'Q'] for ICs and transistors). If not specified, searches all components"),
      priority: z.enum(["HIGH", "MEDIUM", "LOW", "ALL"]).optional()
        .describe("Priority level to filter by (default: ALL)"),
      requirements: z.object({
        grade: z.enum(["automotive", "industrial", "military"]).optional(),
        temp_range: z.tuple([z.number(), z.number()]).optional()
      }).optional().describe("Component requirements")
    },
    async ({ component_types, priority, requirements }) => {
      logger.debug(`Finding automotive alternatives for BOM components`);

      try {
        const result = await callPythonScript("find_bom_alternatives", {
          component_types: component_types || [],
          priority: priority || "ALL",
          requirements: requirements || {}
        });

        return {
          content: [{
            type: "text",
            text: JSON.stringify(result, null, 2)
          }]
        };
      } catch (error: any) {
        logger.error(`Error finding BOM alternatives: ${error.message}`);
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: false,
              error: error.message
            }, null, 2)
          }]
        };
      }
    }
  );

  // ------------------------------------------------------
  // Compare Component Availability Tool
  // ------------------------------------------------------
  server.tool(
    "compare_component_availability",
    {
      components: z.array(z.string()).describe("List of MPNs to compare availability for")
    },
    async ({ components }) => {
      logger.debug(`Comparing availability for ${components.length} components`);

      try {
        const result = await callPythonScript("compare_availability", {
          components
        });

        return {
          content: [{
            type: "text",
            text: JSON.stringify(result, null, 2)
          }]
        };
      } catch (error: any) {
        logger.error(`Error comparing availability: ${error.message}`);
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: false,
              error: error.message
            }, null, 2)
          }]
        };
      }
    }
  );

  // ------------------------------------------------------
  // Generate Substitution Report Tool
  // ------------------------------------------------------
  server.tool(
    "generate_substitution_report",
    {
      from_revision: z.string().optional().describe("Source revision (e.g., 'rev0004')"),
      to_revision: z.string().optional().describe("Target revision (e.g., 'rev0005')"),
      substitutions: z.array(z.object({
        original_mpn: z.string(),
        replacement_mpn: z.string(),
        reference: z.string().optional(),
        reason: z.string().optional()
      })).optional().describe("List of component substitutions to document")
    },
    async ({ from_revision, to_revision, substitutions }) => {
      logger.debug(`Generating substitution report`);

      try {
        const result = await callPythonScript("generate_substitution_report", {
          from_revision,
          to_revision,
          substitutions: substitutions || []
        });

        return {
          content: [{
            type: "text",
            text: JSON.stringify(result, null, 2)
          }]
        };
      } catch (error: any) {
        logger.error(`Error generating substitution report: ${error.message}`);
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: false,
              error: error.message
            }, null, 2)
          }]
        };
      }
    }
  );

  logger.info('Successfully registered 7 distributor API tools');
}
