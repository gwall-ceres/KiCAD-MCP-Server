# Mouser & DigiKey API Integration Plan
## KiCad MCP Server Distributor Integration

---

## Executive Summary

Add Mouser and DigiKey API integration to the KiCad MCP server to provide:
- Real-time component availability checking
- Pricing information across distributors
- Alternative part recommendations
- BOM validation and cost optimization

**Timeline:** ~1-2 days of focused development
**Impact:** Dramatically improves PCB design workflow with supply chain awareness

---

## Architecture Overview

### Component Structure

```
KiCad MCP Server
├── python/
│   ├── api_clients/          # NEW: API client implementations
│   │   ├── __init__.py
│   │   ├── mouser_client.py  # Mouser API client
│   │   ├── digikey_client.py # DigiKey API client
│   │   └── base_client.py    # Shared base class
│   ├── commands/
│   │   └── distributor.py    # NEW: Distributor command handler
│   └── kicad_interface.py    # Register new commands
├── src/
│   └── tools/
│       └── distributor.ts    # NEW: MCP tool definitions
├── .env                      # API credentials
└── requirements.txt          # Add new dependencies
```

---

## API Overview

### Mouser API

**Base URL:** `https://api.mouser.com/api/v1`
**Authentication:** API Key (passed in header or query param)
**Rate Limits:**
- Search: ~30 calls/minute
- Cart/Order: More restrictive

**Key Endpoints:**
1. **Search API** (`/search/keyword`)
   - Search by keyword/part number
   - Returns up to ~50 results per call
   - JSON/XML response

2. **Part Details** (`/search/partnumber`)
   - Get detailed info for specific part
   - Pricing breaks, stock levels, datasheet

3. **Cart API** (future)
   - Build carts programmatically
   - Useful for BOM ordering

**Authentication:**
```http
GET https://api.mouser.com/api/v1/search/keyword?apiKey=YOUR_KEY
Content-Type: application/json
```

**Example Response:**
```json
{
  "SearchResults": {
    "NumberOfResult": 15,
    "Parts": [
      {
        "ManufacturerPartNumber": "STM32F407VGT6",
        "Manufacturer": "STMicroelectronics",
        "Description": "ARM Microcontrollers - MCU",
        "DataSheetUrl": "https://...",
        "ProductDetailUrl": "https://...",
        "PriceBreaks": [
          {"Quantity": 1, "Price": "$10.50", "Currency": "USD"},
          {"Quantity": 10, "Price": "$9.80", "Currency": "USD"}
        ],
        "Availability": "2,145 In Stock",
        "LeadTime": "5-7 business days"
      }
    ]
  }
}
```

### DigiKey API

**Base URL:** `https://api.digikey.com/v1`
**Authentication:** OAuth 2.0
**Rate Limits:** Depends on account tier

**Key Endpoints:**
1. **Product Search** (`/Search/v3/Products/Keyword`)
   - Comprehensive search
   - Advanced filtering

2. **Product Details** (`/Search/v3/Products/{DigiKeyPartNumber}`)
   - Full product information
   - Real-time pricing/availability

3. **Price & Stock** (OAuth protected)
   - Real-time inventory
   - Quantity breaks

**OAuth Flow:**
```
1. Get client credentials from DigiKey developer portal
2. Exchange for access token
3. Use token in Authorization header
```

**Authentication:**
```http
GET https://api.digikey.com/v1/Search/v3/Products/Keyword
Authorization: Bearer YOUR_ACCESS_TOKEN
X-DIGIKEY-Client-Id: YOUR_CLIENT_ID
Content-Type: application/json
```

**Example Response:**
```json
{
  "ProductsCount": 12,
  "Products": [
    {
      "DigiKeyPartNumber": "497-STM32F407VGT6-ND",
      "ManufacturerPartNumber": "STM32F407VGT6",
      "Manufacturer": {
        "Name": "STMicroelectronics"
      },
      "ProductDescription": "ARM MCU 32-Bit Cortex-M4",
      "DatasheetUrl": "https://...",
      "ProductUrl": "https://...",
      "StandardPricing": [
        {"BreakQuantity": 1, "UnitPrice": 10.85},
        {"BreakQuantity": 10, "UnitPrice": 10.12}
      ],
      "QuantityAvailable": 1245,
      "Parameters": [
        {"Parameter": "Core Processor", "Value": "ARM Cortex-M4"},
        {"Parameter": "Speed", "Value": "168MHz"}
      ]
    }
  ]
}
```

---

## Implementation Plan

### Phase 1: API Client Infrastructure (Day 1, Morning)

#### 1.1: Create Base Client Class

**File:** `python/api_clients/base_client.py`

```python
"""Base class for distributor API clients"""
import httpx
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)

class BaseDistributorClient:
    """Base class with common functionality for distributor APIs"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._http_client = httpx.AsyncClient(timeout=30.0)
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(hours=1)

    def is_configured(self) -> bool:
        """Check if API credentials are configured"""
        return bool(self.api_key)

    async def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if still valid"""
        if key in self._cache:
            data, cached_time = self._cache[key]
            if datetime.now() - cached_time < self._cache_ttl:
                return data
            del self._cache[key]
        return None

    def _cache_data(self, key: str, data: Any):
        """Cache data with timestamp"""
        self._cache[key] = (data, datetime.now())

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        try:
            response = await self._http_client.request(
                method,
                url,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise

    async def close(self):
        """Close HTTP client"""
        await self._http_client.aclose()
```

#### 1.2: Create Mouser Client

**File:** `python/api_clients/mouser_client.py`

**Features:**
- Search by keyword/MPN
- Get part details with pricing
- Handle pagination
- Error handling and retries

#### 1.3: Create DigiKey Client

**File:** `python/api_clients/digikey_client.py`

**Features:**
- OAuth 2.0 authentication
- Token refresh logic
- Product search
- Detailed part information
- Parametric search (future)

---

### Phase 2: Command Handler (Day 1, Afternoon)

**File:** `python/commands/distributor.py`

**Class:** `DistributorCommands`

**Methods:**
1. `search_component(query: str, distributor: str = "all")`
   - Search across Mouser and/or DigiKey
   - Return unified results

2. `get_component_availability(mpn: str)`
   - Check stock and pricing for specific MPN
   - Compare across distributors

3. `check_bom_availability(bom_data: List[Dict])`
   - Analyze entire BOM
   - Identify availability issues
   - Calculate total cost

4. `find_alternatives(mpn: str, reason: str)`
   - Find replacement parts
   - Match by specifications
   - Compare pricing/availability

5. `compare_pricing(mpn: str)`
   - Side-by-side price comparison
   - Quantity break analysis
   - Best value recommendations

---

### Phase 3: MCP Tool Wrappers (Day 2, Morning)

**File:** `src/tools/distributor.ts`

**TypeScript Interfaces:**
```typescript
export interface DistributorSearchParams {
  query: string;
  distributor?: "mouser" | "digikey" | "all";
  limit?: number;
}

export interface ComponentAvailabilityParams {
  mpn: string;
}

export interface BOMCheckParams {
  bomData?: Array<{
    reference: string;
    value: string;
    footprint: string;
    mpn?: string;
  }>;
  bomFilePath?: string;
}
```

**MCP Tools:**
1. `search_component` - Search for parts
2. `get_component_availability` - Check availability
3. `check_bom_availability` - Validate BOM
4. `find_component_alternatives` - Find replacements
5. `compare_distributor_pricing` - Price comparison

---

### Phase 4: Configuration & Testing (Day 2, Afternoon)

#### 4.1: Update .env

```env
# Mouser API Configuration
MOUSER_API_KEY=your_api_key_here

# DigiKey API Configuration
DIGIKEY_CLIENT_ID=your_client_id_here
DIGIKEY_CLIENT_SECRET=your_client_secret_here
DIGIKEY_REDIRECT_URI=http://localhost:8080/callback

# Cache settings (optional)
DISTRIBUTOR_CACHE_DURATION=3600  # 1 hour in seconds
```

#### 4.2: Update requirements.txt

```txt
# Existing dependencies...

# Distributor API integration
httpx>=0.28.0
python-dotenv>=1.0.0
pydantic>=2.10.0
```

#### 4.3: Test Suite

Create `tests/test_distributor.py`:
- Test API client initialization
- Test search functionality
- Test availability checking
- Test BOM validation
- Mock API responses for unit tests

---

## Usage Examples

### Example 1: Search for Component

```
User: "Search for STM32F407VGT6 on Mouser and DigiKey"

Claude: [Calls search_component tool]
Result:
Found 15 results across distributors:

Mouser (8 results):
1. STM32F407VGT6 - STMicroelectronics
   Stock: 2,145 units
   Price: $10.50 @ 1, $9.80 @ 10
   Link: https://mouser.com/...

DigiKey (7 results):
2. STM32F407VGT6 - STMicroelectronics
   Stock: 1,245 units
   Price: $10.85 @ 1, $10.12 @ 10
   Link: https://digikey.com/...
```

### Example 2: Check BOM Availability

```
User: "Check component availability for my current board"

Claude: [Exports BOM, calls check_bom_availability]
Result:
BOM Analysis (45 components):
✅ 42 components in stock
⚠️ 2 components low stock (<100 units)
  - C15 (0.1uF 0603): 45 units at Mouser
  - R22 (10k 0402): 78 units at DigiKey
❌ 1 component out of stock
  - U3 (LM2596): 0 units (lead time: 12 weeks)

Total BOM cost estimate:
- Quantity 1: $127.50
- Quantity 10: $1,185.00
- Quantity 100: $11,240.00

Recommendation: Find alternative for U3
```

### Example 3: Find Alternatives

```
User: "Find alternatives for U3 since it's out of stock"

Claude: [Calls find_alternatives tool]
Result:
Found 5 suitable alternatives for LM2596:

1. TPS54360 (Texas Instruments) ⭐ Best Match
   - In stock: 5,247 units @ DigiKey
   - Price: $2.45 (20% cheaper!)
   - Same footprint: TO-263
   - Better efficiency: 95% vs 90%
   - Datasheet: https://...

2. MP1584EN (Monolithic Power)
   - In stock: 12,000+ units @ Mouser
   - Price: $0.85 (73% cheaper!)
   - ⚠️ Different footprint (requires layout change)

Would you like me to update U3 with TPS54360?
```

---

## API Key Setup Instructions

### Mouser API Key

1. Go to https://www.mouser.com/api-hub/
2. Sign up for a free account
3. Navigate to "Search API"
4. Click "Get API Key"
5. Fill out the application form:
   - Company: Your company or "Personal Project"
   - Use case: "PCB Design Automation"
6. You'll receive API key via email (usually within 24 hours)
7. Add to `.env`: `MOUSER_API_KEY=your_key_here`

**Rate Limits (Free Tier):**
- 1,000 requests/day
- 30 requests/minute
- Cached results help minimize API calls

### DigiKey API Credentials

1. Go to https://developer.digikey.com/
2. Create account and verify email
3. Click "Create Application"
4. Fill out form:
   - Name: "KiCad MCP Integration"
   - Description: "PCB design tool integration"
   - Redirect URI: `http://localhost:8080/callback`
5. Select scopes:
   - Product Information
   - Pricing and Availability
6. Submit application
7. Once approved, you'll receive:
   - Client ID
   - Client Secret
8. Add to `.env`:
   ```
   DIGIKEY_CLIENT_ID=your_client_id
   DIGIKEY_CLIENT_SECRET=your_client_secret
   ```

**OAuth Note:** DigiKey uses OAuth 2.0, which is more complex than Mouser's API key. The client will handle token refresh automatically.

**Rate Limits:**
- Varies by account tier
- Free tier: ~1000 requests/day
- Production tier: Higher limits available

---

## Benefits & Features

### For Design Workflow
- ✅ Real-time availability checking during design
- ✅ Identify obsolete parts before ordering
- ✅ Cost optimization across distributors
- ✅ Automatic alternative part recommendations
- ✅ Lead time awareness

### For BOM Management
- ✅ One-click BOM validation
- ✅ Multi-distributor price comparison
- ✅ Quantity break optimization
- ✅ Total cost estimation
- ✅ Stock level monitoring

### For Supply Chain
- ✅ Reduce risk of unavailable parts
- ✅ Plan for long lead times
- ✅ Identify second sources
- ✅ Track lifecycle status
- ✅ Automated distributor comparison

---

## Future Enhancements

### Phase 2 Features (Post-Launch)
1. **Automatic cart building** - Add BOM to Mouser/DigiKey cart
2. **Historical pricing** - Track price trends over time
3. **Stock alerts** - Notify when parts become available
4. **Parametric search** - Find parts by specifications
5. **Component lifecycle** - Track NRND/obsolescence status
6. **Batch BOM checking** - Check multiple projects at once
7. **Export quotes** - Generate distributor quotes
8. **Inventory management** - Track your own stock

### Additional Distributors
- Newark/Farnell
- Arrow Electronics
- RS Components
- LCSC (for China manufacturing)
- TME (Europe)

---

## Success Criteria

After implementation, users should be able to:

1. ✅ Ask "What's the current availability for STM32F407VGT6?"
2. ✅ Ask "Check if all my BOM components are in stock"
3. ✅ Ask "Find a cheaper alternative for U3"
4. ✅ Ask "Compare Mouser vs DigiKey pricing for my BOM"
5. ✅ Ask "What's the total cost for 100 boards?"
6. ✅ Ask "Which components have long lead times?"

---

## Next Steps

**Ready to implement?** The plan is:

**Day 1:**
- Morning: Build API clients (base, Mouser, DigiKey)
- Afternoon: Create command handler with all 5 methods

**Day 2:**
- Morning: Create TypeScript MCP tool wrappers
- Afternoon: Testing, documentation, polish

**Estimated Time:** 12-16 hours of focused development

Let me know when you're ready to start, and I'll begin with the API clients!
