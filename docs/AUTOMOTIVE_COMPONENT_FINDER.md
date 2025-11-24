# Automotive Component Finder - KiCad MCP Integration
## Find automotive/industrial replacements through Claude Code

---

## Vision: Natural Workflow with Claude

```
You (in Claude Code): "Find automotive alternatives for all ICs in my Astro board"

Claude: [Reads KiCad BOM] → [Queries Mouser/DigiKey APIs] →
        [Filters for automotive grade] → [Compares specs]

Result:
┌──────────────────────────────────────────────────────────┐
│ Found automotive replacements for 8 ICs:                 │
│                                                           │
│ U3: LM2596 → TPS54360-Q1 [AUTOMOTIVE]                   │
│   Current: Commercial, 0-70°C, $3.10                    │
│   Replace: Automotive, -40-125°C, $2.45 ✅ BETTER!      │
│   Stock: 5,247 @ DigiKey                                │
│   Footprint: ✓ Compatible                              │
│   Datasheet: https://...                                │
│                                                           │
│ [Show all] [Update schematic] [Export report]           │
└──────────────────────────────────────────────────────────┘

You: "Update the schematic with these replacements"

Claude: [Updates KiCad schematic] → [Documents changes] →
        [Generates substitution report]
        ✅ Done! Updated 8 components.
```

---

## Architecture: Integrated with Existing KiCad MCP

```
KiCad MCP Server (c:\Users\geoff\...\KiCAD-MCP-Server\)
├── python/
│   ├── api_clients/                 # NEW: Distributor APIs
│   │   ├── __init__.py
│   │   ├── base_client.py
│   │   ├── mouser_client.py
│   │   ├── digikey_client.py
│   │   └── types.py                 # Component data types
│   │
│   ├── commands/
│   │   ├── distributor.py           # NEW: Component finder logic
│   │   ├── export.py                # EXISTING: BOM export
│   │   └── component.py             # EXISTING: Component operations
│   │
│   └── kicad_interface.py           # Register new commands
│
├── src/
│   └── tools/
│       └── distributor.ts           # NEW: MCP tools for Claude
│
└── .env                              # API keys
    MOUSER_API_KEY=...
    DIGIKEY_CLIENT_ID=...
    DIGIKEY_CLIENT_SECRET=...
```

---

## User Workflows

### Workflow 1: Quick Component Check

```
You: "Is U3 available in automotive grade?"

Claude: → Calls find_automotive_alternative("LM2596")
        → Searches Mouser/DigiKey

Result: "Yes! TPS54360-Q1 is automotive grade:
        - Temperature: -40°C to 125°C ✓
        - AEC-Q100 qualified ✓
        - Same footprint ✓
        - In stock: 5,247 units
        - Price: $2.45 (vs $3.10 - actually cheaper!)"
```

### Workflow 2: Batch BOM Upgrade

```
You: "Find automotive replacements for all HIGH priority components in my BOM"

Claude: → Exports current BOM from KiCad
        → Reads your aviation_analysis.csv
        → Finds HIGH priority components (8 ICs, 3 FETs)
        → Searches for automotive alternatives
        → Generates comparison report

Result: "Found automotive alternatives for 11/11 components:

        ✅ All replacements in stock
        ✅ 8 are same or better price
        ✅ All have compatible footprints

        Total cost impact: -$1.20/board (actually cheaper!)

        [View detailed report] [Update schematic]"
```

### Workflow 3: Aviation Compliance Check

```
You: "Check if my BOM meets aviation requirements (-40°C to 125°C)"

Claude: → Analyzes entire BOM
        → Checks temp ratings
        → Identifies non-compliant parts

Result: "BOM Compliance Report:

        ✅ 37 components meet requirements
        ⚠️  8 components need upgrades (see below)
        ❌ 2 components have no automotive alternative

        Recommended action: Upgrade 8 components
        Estimated time: 2-3 hours
        Cost impact: +$1.50/board"
```

### Workflow 4: Component Substitution Documentation

```
You: "Document why we're changing Q1 from SI4459BDY to Si4435BDY"

Claude: → Looks up both parts
        → Compares specs
        → Generates substitution justification

Result: "Substitution Justification:

        FROM: SI4459BDY-T1-GE3
        - Voltage: -30V
        - Current: -7A (single channel)
        - Grade: Commercial
        - Temp: 0°C to 70°C

        TO: Si4435BDY-T1-GE3
        - Voltage: -40V ✓ +33% margin
        - Current: -14A ✓ 2x headroom
        - Grade: Commercial (automotive available as -Q1)
        - Temp: -55°C to 150°C ✓ Aviation compliant

        Reason: Rev0004 lesson #2 - Insufficient voltage margin
        Impact: +$0.35/board
        Risk: LOW (proven part, same footprint)

        [Add to Rev0005 documentation]"
```

---

## MCP Tools (What Claude Can Do)

### 1. `find_automotive_alternative`
**Purpose:** Find automotive/industrial replacement for ONE component

**Usage:**
```typescript
User: "Find automotive alternative for LM2596"
Claude calls: find_automotive_alternative({
  mpn: "LM2596",
  requirements: {
    temperature_range: [-40, 125],
    grade: ["automotive", "industrial"],
    same_footprint: true
  }
})
```

**Returns:**
```json
{
  "original": {
    "mpn": "LM2596",
    "grade": "commercial",
    "temp_range": [0, 70]
  },
  "alternatives": [
    {
      "mpn": "TPS54360-Q1",
      "grade": "automotive",
      "temp_range": [-40, 125],
      "footprint_compatible": true,
      "price": 2.45,
      "stock": 5247,
      "distributor": "digikey",
      "datasheet_url": "https://..."
    }
  ]
}
```

### 2. `check_bom_automotive_compliance`
**Purpose:** Analyze entire BOM for automotive compliance

**Usage:**
```typescript
User: "Check my BOM for aviation requirements"
Claude calls: check_bom_automotive_compliance({
  temp_min: -40,
  temp_max: 125,
  required_grade: ["automotive", "industrial"]
})
```

**Returns:**
```json
{
  "compliant": 37,
  "non_compliant": 8,
  "no_alternative": 2,
  "summary": {
    "total_cost_impact": 1.50,
    "components_to_upgrade": [
      {
        "reference": "U3",
        "current_mpn": "LM2596",
        "recommended_mpn": "TPS54360-Q1",
        "reason": "Temperature range insufficient",
        "priority": "HIGH"
      }
    ]
  }
}
```

### 3. `find_bom_automotive_alternatives`
**Purpose:** Batch find alternatives for multiple components

**Usage:**
```typescript
User: "Find automotive alternatives for all ICs"
Claude calls: find_bom_automotive_alternatives({
  component_types: ["U"],  // ICs only
  priority: "HIGH",
  requirements: {
    grade: "automotive",
    temp_range: [-40, 125]
  }
})
```

### 4. `compare_component_availability`
**Purpose:** Check availability and lead times

**Usage:**
```typescript
User: "Are all automotive replacements in stock?"
Claude calls: compare_component_availability({
  components: ["TPS54360-Q1", "Si4435BDY-Q1", ...]
})
```

### 5. `generate_substitution_report`
**Purpose:** Document component changes (Rev0004 lesson!)

**Usage:**
```typescript
User: "Document all component changes for Rev0005"
Claude calls: generate_substitution_report({
  from_revision: "rev0004",
  to_revision: "rev0005"
})
```

---

## Implementation Plan

### Day 1: API Clients Foundation (4-6 hours)

**Files to create:**
```
python/api_clients/
├── base_client.py         # Base class with caching, rate limiting
├── mouser_client.py       # Mouser API integration
├── digikey_client.py      # DigiKey OAuth + API
└── types.py               # Component, PriceBreak, etc.
```

**Features:**
- API authentication (Mouser key, DigiKey OAuth)
- Rate limiting (respect API limits)
- Caching (1 hour TTL)
- Error handling
- Search by MPN
- Get detailed specs

### Day 2: Component Matching Logic (4-6 hours)

**File:** `python/commands/distributor.py`

**Key functions:**
1. `find_automotive_alternative(mpn, requirements)`
   - Search Mouser/DigiKey for alternatives
   - Filter by grade (automotive/industrial)
   - Filter by temp range
   - Compare footprints
   - Score alternatives (price, availability, specs)

2. `check_aviation_compliance(component)`
   - Verify temperature rating
   - Check if AEC-Q qualified
   - Identify grade (commercial/industrial/automotive)

3. `compare_components(original, alternative)`
   - Side-by-side spec comparison
   - Footprint compatibility check
   - Price/availability comparison

### Day 3: MCP Tools + Claude Integration (3-4 hours)

**File:** `src/tools/distributor.ts`

**Register MCP tools:**
- `find_automotive_alternative`
- `check_bom_automotive_compliance`
- `find_bom_automotive_alternatives`
- `compare_component_availability`
- `generate_substitution_report`

**Integration with existing tools:**
- Use `export_bom` to get current BOM
- Use `get_component_properties` to read component details
- Can call schematic update tools to apply changes

### Day 4: Testing + Polish (2-3 hours)

**Test with your Astro Daughterboard:**
1. Export BOM from KiCad
2. Run aviation compliance check
3. Find alternatives for HIGH priority components
4. Verify footprint compatibility
5. Generate substitution report

---

## Example Session: Your Astro Board Respin

```
You: "I need to upgrade my Astro board to automotive grade for aviation.
     Can you help me find replacements?"

Claude: "Sure! Let me analyze your current BOM."
        [Exports BOM from KiCad]
        [Runs aviation compliance check]

        "I found 8 components that need upgrading:

        HIGH PRIORITY (need automotive grade):
        - U3 (LM2596): Buck converter
        - Q1 (SI4459BDY): Main power switch
        - Q6 (FDMC8010): Motor driver FET

        MEDIUM PRIORITY (industrial acceptable):
        - U5, U7, U12: Various ICs

        Let me search for automotive alternatives..."
        [Searches Mouser/DigiKey for each]

        "Great news! Found automotive replacements for all 8:

        ✅ U3: LM2596 → TPS54360-Q1
           - $2.45 (cheaper!)
           - 5,247 in stock
           - Same footprint
           - -40°C to 125°C

        ✅ Q1: SI4459BDY → Si4435BDY
           - $2.45 (+$0.35)
           - 1,247 in stock
           - Same footprint
           - -40V rating (better margin!)

        [Show all 8] [Update schematic] [Export report]"

You: "Show me the full comparison for U3"

Claude: "TPS54360-Q1 vs LM2596:

        Voltage:
        - LM2596: 45V max
        - TPS54360-Q1: 42V max ✓ (adequate for 26V system)

        Current:
        - LM2596: 3A
        - TPS54360-Q1: 3.5A ✓ (better)

        Efficiency:
        - LM2596: ~90%
        - TPS54360-Q1: ~95% ✓ (5% better!)

        Temperature:
        - LM2596: 0°C to 70°C ❌
        - TPS54360-Q1: -40°C to 125°C ✅

        Grade:
        - LM2596: Commercial
        - TPS54360-Q1: Automotive (AEC-Q100) ✅

        Footprint:
        - Both: TO-263 ✓ Drop-in replacement

        Price:
        - LM2596: $3.10
        - TPS54360-Q1: $2.45 ✅ Save $0.65!

        Recommendation: ✅ REPLACE
        This solves your aviation requirements AND is cheaper."

You: "Perfect! Update the schematic with all 8 replacements and
     generate a substitution report for documentation"

Claude: [Updates KiCad schematic]
        [Generates substitution report]
        [Updates BOM]

        "✅ Done! Updated 8 components in Power_Misc.kicad_sch

        Changes documented in:
        - Rev0005-Component-Substitutions.md
        - Updated BOM: Astro-DB_rev00005_automotive.csv

        Next steps:
        1. Review changes in KiCad
        2. Run DRC check
        3. Order updated BOM from Mouser/DigiKey

        Total cost impact: +$1.20/board (still cheaper than expected!)"
```

---

## API Keys Setup

### Mouser API (Free)
1. Sign up: https://www.mouser.com/api-hub/
2. Request API key (approved in 24-48 hours)
3. Add to `.env`: `MOUSER_API_KEY=your_key_here`

**Rate limits:**
- 1,000 requests/day
- 30 requests/minute

### DigiKey API (Free)
1. Sign up: https://developer.digikey.com/
2. Create application
3. Get Client ID + Secret
4. Add to `.env`:
   ```
   DIGIKEY_CLIENT_ID=your_id
   DIGIKEY_CLIENT_SECRET=your_secret
   ```

**Rate limits:**
- 1,000 requests/day (free tier)

---

## Benefits for Your Workflow

### For Rev0005 Respin:
- ✅ Find automotive alternatives in **minutes** (not hours)
- ✅ Verify availability before committing
- ✅ Document substitutions (Rev0004 lesson #8)
- ✅ Compare prices across distributors
- ✅ Check footprint compatibility

### For Future Designs:
- ✅ Reusable for any aviation/automotive board
- ✅ Works with any KiCad project
- ✅ Natural language queries through Claude
- ✅ Community contribution ready

### For Documentation:
- ✅ Auto-generate substitution reports
- ✅ Track why parts changed
- ✅ Export for reviews/audits

---

## Timeline

**This Week:**
- Monday: Get API keys
- Tuesday-Wednesday: Build API clients + matching logic
- Thursday: MCP tools + testing with your board
- Friday: Polish + documentation

**Realistic:** 2-3 days of focused development

---

## Next Steps

1. **Get API keys** (can start today)
   - Mouser: https://www.mouser.com/api-hub/
   - DigiKey: https://developer.digikey.com/

2. **I'll build the tool** in your KiCad MCP Server
   - Integrates with existing BOM export
   - Works through Claude Code naturally
   - Tests with your Astro board

3. **You test and refine**
   - Try on your Rev0005 BOM
   - Provide feedback on results
   - Add aviation-specific requirements

**Ready to start?** Should I begin building the API clients while you get the API keys set up?
