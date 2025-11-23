# KiCad UI Integration: Component Availability & Alternatives
## Right-Click Component → Check Availability & Find Replacements

---

## User Experience Vision

### In KiCad PCB Editor:
```
1. User right-clicks on component "U3" on the board
2. Context menu appears with new option:
   ├─ Edit Properties
   ├─ Move
   ├─ Rotate
   ├─ Delete
   └─ 🆕 Check Component Availability ←

3. User clicks "Check Component Availability"
4. Dialog opens showing:
   ┌─────────────────────────────────────────────┐
   │ Component: U3 (STM32F407VGT6)               │
   ├─────────────────────────────────────────────┤
   │ 📦 Availability                             │
   │                                             │
   │ Mouser:                                     │
   │  ✅ 2,145 units in stock                   │
   │  💰 $10.50 @ 1  |  $9.80 @ 10             │
   │  🔗 View on Mouser                         │
   │                                             │
   │ DigiKey:                                    │
   │  ✅ 1,245 units in stock                   │
   │  💰 $10.85 @ 1  |  $10.12 @ 10            │
   │  🔗 View on DigiKey                        │
   │                                             │
   ├─────────────────────────────────────────────┤
   │ 🔄 Alternatives (5 found)                   │
   │                                             │
   │ ⭐ TPS54360 (Texas Instruments)            │
   │    In stock: 5,247 @ DigiKey               │
   │    Price: $2.45 (20% cheaper!)             │
   │    Same footprint ✓                        │
   │    [Replace with this] [View Details]      │
   │                                             │
   │ MP1584EN (Monolithic Power)                │
   │    In stock: 12,000+ @ Mouser              │
   │    Price: $0.85 (73% cheaper!)             │
   │    ⚠️ Different footprint                  │
   │    [View Details]                           │
   │                                             │
   ├─────────────────────────────────────────────┤
   │ [Refresh] [Check All BOM] [Close]          │
   └─────────────────────────────────────────────┘
```

### In KiCad Schematic Editor:
```
Same workflow:
1. Right-click on component in schematic
2. Select "Check Component Availability"
3. Same dialog appears
4. Can replace component from dialog
```

---

## Architecture

### Dual-Interface System

```
                  ┌─────────────────────┐
                  │   Shared API Layer  │
                  │  (Python Modules)   │
                  │                     │
                  │ - mouser_client.py  │
                  │ - digikey_client.py │
                  │ - base_client.py    │
                  └──────────┬──────────┘
                             │
              ┌──────────────┴───────────────┐
              │                              │
    ┌─────────▼─────────┐         ┌─────────▼──────────┐
    │  KiCad UI Layer   │         │   MCP Server       │
    │  (Action Plugin)  │         │   (Claude)         │
    ├───────────────────┤         ├────────────────────┤
    │ - Context menu    │         │ - Tool handlers    │
    │ - Dialogs (wxPy)  │         │ - JSON responses   │
    │ - Component swap  │         │ - Batch BOM check  │
    └─────────┬─────────┘         └─────────┬──────────┘
              │                             │
    ┌─────────▼─────────┐         ┌─────────▼──────────┐
    │  KiCad GUI        │         │  Claude Desktop    │
    │  (User clicks)    │         │  (NL queries)      │
    └───────────────────┘         └────────────────────┘
```

---

## Implementation Structure

### File Organization

```
KiCad-MCP-Server/
├── python/
│   ├── api_clients/                    # SHARED: API clients
│   │   ├── __init__.py
│   │   ├── base_client.py             # Base class for all APIs
│   │   ├── mouser_client.py           # Mouser API
│   │   ├── digikey_client.py          # DigiKey API
│   │   └── types.py                   # Shared types/dataclasses
│   │
│   ├── kicad_plugins/                  # NEW: KiCad UI integration
│   │   └── component_availability/
│   │       ├── __init__.py
│   │       ├── plugin.py              # KiCad Action Plugin
│   │       ├── context_menu.py        # Right-click menu
│   │       ├── dialogs/
│   │       │   ├── __init__.py
│   │       │   ├── availability_dialog.py  # Main dialog
│   │       │   ├── alternatives_dialog.py  # Alternatives view
│   │       │   └── bom_check_dialog.py    # Full BOM checker
│   │       └── utils/
│   │           ├── component_utils.py # Extract component info
│   │           └── mpn_extractor.py   # Find MPN from footprint/value
│   │
│   ├── commands/                       # MCP command handlers
│   │   ├── distributor.py             # MCP-specific wrapper
│   │   └── ...existing commands...
│   │
│   └── kicad_interface.py             # Register everything
│
├── src/                                # TypeScript MCP tools
│   └── tools/
│       └── distributor.ts             # MCP tool definitions
│
└── .env                                # API keys
```

---

## Phase 1: Shared API Clients (Foundation)

### 1.1: Base Types

**File:** `python/api_clients/types.py`

```python
"""Shared data types for distributor APIs"""
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class Distributor(Enum):
    MOUSER = "mouser"
    DIGIKEY = "digikey"

@dataclass
class PriceBreak:
    """Price at specific quantity"""
    quantity: int
    price: float
    currency: str = "USD"

@dataclass
class ComponentAvailability:
    """Component availability info"""
    mpn: str
    manufacturer: str
    description: str
    distributor: Distributor
    stock: int
    price_breaks: List[PriceBreak]
    datasheet_url: Optional[str] = None
    product_url: Optional[str] = None
    lead_time: Optional[str] = None

    @property
    def in_stock(self) -> bool:
        return self.stock > 0

    @property
    def unit_price(self) -> float:
        """Price for quantity 1"""
        if self.price_breaks:
            return self.price_breaks[0].price
        return 0.0

@dataclass
class AlternativeComponent:
    """Alternative/replacement component"""
    mpn: str
    manufacturer: str
    description: str
    availability: List[ComponentAvailability]
    same_footprint: bool
    price_difference: float  # % cheaper/more expensive
    compatibility_notes: List[str]

    @property
    def best_price(self) -> float:
        """Lowest price across distributors"""
        if not self.availability:
            return 0.0
        return min(a.unit_price for a in self.availability)

    @property
    def total_stock(self) -> int:
        """Total stock across distributors"""
        return sum(a.stock for a in self.availability)
```

### 1.2: Mouser Client

**File:** `python/api_clients/mouser_client.py`

```python
"""Mouser Electronics API Client"""
import os
import httpx
from typing import List, Optional
from .base_client import BaseDistributorClient
from .types import ComponentAvailability, PriceBreak, Distributor

class MouserClient(BaseDistributorClient):
    """Client for Mouser Electronics API"""

    BASE_URL = "https://api.mouser.com/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or os.getenv("MOUSER_API_KEY"))

    async def search_component(self, query: str) -> List[ComponentAvailability]:
        """Search for components by MPN or keyword"""

        # Check cache first
        cache_key = f"mouser_search_{query}"
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        url = f"{self.BASE_URL}/search/keyword"
        params = {
            "apiKey": self.api_key
        }
        body = {
            "SearchByKeywordRequest": {
                "keyword": query,
                "records": 10,
                "startingRecord": 0,
                "searchOptions": "",
                "searchWithYourSignUpLanguage": ""
            }
        }

        response = await self._request("POST", url, params=params, json=body)

        results = []
        parts = response.get("SearchResults", {}).get("Parts", [])

        for part in parts:
            # Parse price breaks
            price_breaks = []
            for pb in part.get("PriceBreaks", []):
                price_breaks.append(PriceBreak(
                    quantity=int(pb.get("Quantity", 0)),
                    price=float(pb.get("Price", "0").replace("$", "").replace(",", "")),
                    currency=pb.get("Currency", "USD")
                ))

            # Parse availability
            availability_str = part.get("Availability", "0")
            stock = self._parse_stock_string(availability_str)

            results.append(ComponentAvailability(
                mpn=part.get("ManufacturerPartNumber", ""),
                manufacturer=part.get("Manufacturer", ""),
                description=part.get("Description", ""),
                distributor=Distributor.MOUSER,
                stock=stock,
                price_breaks=price_breaks,
                datasheet_url=part.get("DataSheetUrl"),
                product_url=part.get("ProductDetailUrl"),
                lead_time=part.get("LeadTime")
            ))

        # Cache results
        self._cache_data(cache_key, results)

        return results

    def _parse_stock_string(self, availability: str) -> int:
        """Parse '2,145 In Stock' → 2145"""
        try:
            return int(availability.split()[0].replace(",", ""))
        except:
            return 0
```

### 1.3: DigiKey Client

**File:** `python/api_clients/digikey_client.py`

```python
"""DigiKey API Client with OAuth 2.0"""
import os
import httpx
from typing import List, Optional
from datetime import datetime, timedelta
from .base_client import BaseDistributorClient
from .types import ComponentAvailability, PriceBreak, Distributor

class DigiKeyClient(BaseDistributorClient):
    """Client for DigiKey API with OAuth 2.0"""

    BASE_URL = "https://api.digikey.com/v1"
    AUTH_URL = "https://api.digikey.com/v1/oauth2/token"

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.client_id = client_id or os.getenv("DIGIKEY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("DIGIKEY_CLIENT_SECRET")
        super().__init__(api_key=None)  # OAuth uses tokens, not API keys
        self._access_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    async def _ensure_authenticated(self):
        """Get or refresh OAuth token"""
        if self._access_token and self._token_expires:
            if datetime.now() < self._token_expires:
                return  # Token still valid

        # Get new token
        response = await self._http_client.post(
            self.AUTH_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials"
            }
        )
        response.raise_for_status()
        data = response.json()

        self._access_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        self._token_expires = datetime.now() + timedelta(seconds=expires_in - 60)

    async def search_component(self, query: str) -> List[ComponentAvailability]:
        """Search for components"""
        await self._ensure_authenticated()

        # Check cache
        cache_key = f"digikey_search_{query}"
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        url = f"{self.BASE_URL}/Search/v3/Products/Keyword"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "X-DIGIKEY-Client-Id": self.client_id
        }
        body = {
            "Keywords": query,
            "Limit": 10,
            "Offset": 0
        }

        response = await self._request("POST", url, headers=headers, json=body)

        results = []
        products = response.get("Products", [])

        for product in products:
            # Parse price breaks
            price_breaks = []
            for pb in product.get("StandardPricing", []):
                price_breaks.append(PriceBreak(
                    quantity=pb.get("BreakQuantity", 0),
                    price=pb.get("UnitPrice", 0.0),
                    currency="USD"
                ))

            results.append(ComponentAvailability(
                mpn=product.get("ManufacturerPartNumber", ""),
                manufacturer=product.get("Manufacturer", {}).get("Name", ""),
                description=product.get("ProductDescription", ""),
                distributor=Distributor.DIGIKEY,
                stock=product.get("QuantityAvailable", 0),
                price_breaks=price_breaks,
                datasheet_url=product.get("DatasheetUrl"),
                product_url=product.get("ProductUrl")
            ))

        self._cache_data(cache_key, results)
        return results
```

---

## Phase 2: KiCad UI Integration (The Cool Part!)

### 2.1: Action Plugin with Context Menu

**File:** `python/kicad_plugins/component_availability/plugin.py`

```python
"""KiCad Action Plugin for Component Availability Checking"""
import pcbnew
import wx
from typing import Optional
from ...api_clients.mouser_client import MouserClient
from ...api_clients.digikey_client import DigiKeyClient
from .dialogs.availability_dialog import AvailabilityDialog
from .utils.component_utils import extract_component_mpn

class ComponentAvailabilityPlugin(pcbnew.ActionPlugin):
    """Plugin to check component availability from KiCad"""

    def defaults(self):
        self.name = "Component Availability Checker"
        self.category = "BOM Tools"
        self.description = "Check component availability and find alternatives"
        self.show_toolbar_button = True
        self.icon_file_name = "availability_icon.png"

    def Run(self):
        """Called when plugin is run from toolbar"""
        board = pcbnew.GetBoard()

        # Get selected component(s)
        selected = self._get_selected_components(board)

        if not selected:
            wx.MessageBox(
                "No component selected. Please select a component first.",
                "No Selection",
                wx.OK | wx.ICON_INFORMATION
            )
            return

        # Check availability for first selected component
        component = selected[0]
        self._show_availability_dialog(component)

    def _get_selected_components(self, board):
        """Get currently selected components"""
        selected = []
        for module in board.GetFootprints():
            if module.IsSelected():
                selected.append(module)
        return selected

    def _show_availability_dialog(self, component: pcbnew.FOOTPRINT):
        """Show availability dialog for component"""
        # Extract MPN from component properties
        mpn = extract_component_mpn(component)

        if not mpn:
            wx.MessageBox(
                f"Could not find MPN for {component.GetReference()}.\n"
                "Please add 'MPN' or 'Manufacturer_Part_Number' field.",
                "MPN Not Found",
                wx.OK | wx.ICON_WARNING
            )
            return

        # Create and show dialog
        dialog = AvailabilityDialog(None, component, mpn)
        dialog.ShowModal()
        dialog.Destroy()


# Register plugin with KiCad
ComponentAvailabilityPlugin().register()
```

### 2.2: Right-Click Context Menu Integration

**File:** `python/kicad_plugins/component_availability/context_menu.py`

```python
"""Add context menu item to components"""
import pcbnew
import wx

class AvailabilityContextMenu:
    """Adds 'Check Availability' to right-click menu"""

    @staticmethod
    def register():
        """Register context menu handler"""
        # Note: KiCad 8.0+ has better context menu API
        # This is a simplified version

        # Hook into KiCad's context menu system
        pcbnew.AddContextMenuHandler(
            "Check Component Availability",
            AvailabilityContextMenu._on_check_availability
        )

    @staticmethod
    def _on_check_availability(event):
        """Called when user clicks 'Check Availability'"""
        from .plugin import ComponentAvailabilityPlugin
        plugin = ComponentAvailabilityPlugin()
        plugin.Run()
```

### 2.3: Availability Dialog UI

**File:** `python/kicad_plugins/component_availability/dialogs/availability_dialog.py`

```python
"""Main availability checking dialog"""
import wx
import wx.lib.agw.hyperlink as hl
import asyncio
from typing import List
from ....api_clients.mouser_client import MouserClient
from ....api_clients.digikey_client import DigiKeyClient
from ....api_clients.types import ComponentAvailability, AlternativeComponent

class AvailabilityDialog(wx.Dialog):
    """Dialog showing component availability and alternatives"""

    def __init__(self, parent, component, mpn: str):
        super().__init__(
            parent,
            title=f"Component Availability: {component.GetReference()}",
            size=(700, 600),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )

        self.component = component
        self.mpn = mpn
        self.availability: List[ComponentAvailability] = []
        self.alternatives: List[AlternativeComponent] = []

        self._create_ui()
        self._load_data()

    def _create_ui(self):
        """Create dialog UI"""
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Header
        header = wx.StaticText(
            panel,
            label=f"Component: {self.component.GetReference()} ({self.mpn})"
        )
        header_font = header.GetFont()
        header_font.PointSize += 2
        header_font = header_font.Bold()
        header.SetFont(header_font)
        sizer.Add(header, 0, wx.ALL, 10)

        # Notebook for tabs
        notebook = wx.Notebook(panel)

        # Tab 1: Availability
        self.availability_panel = self._create_availability_panel(notebook)
        notebook.AddPage(self.availability_panel, "📦 Availability")

        # Tab 2: Alternatives
        self.alternatives_panel = self._create_alternatives_panel(notebook)
        notebook.AddPage(self.alternatives_panel, "🔄 Alternatives")

        # Tab 3: Specifications (future)
        # self.specs_panel = self._create_specs_panel(notebook)
        # notebook.AddPage(self.specs_panel, "📋 Specifications")

        sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 10)

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()

        self.refresh_btn = wx.Button(panel, label="Refresh")
        self.refresh_btn.Bind(wx.EVT_BUTTON, self._on_refresh)
        btn_sizer.Add(self.refresh_btn)

        close_btn = wx.Button(panel, wx.ID_CLOSE, "Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        btn_sizer.AddButton(close_btn)
        btn_sizer.Realize()

        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        panel.SetSizer(sizer)

    def _create_availability_panel(self, parent) -> wx.Panel:
        """Create availability display panel"""
        panel = wx.ScrolledWindow(parent)
        panel.SetScrollRate(10, 10)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Loading message
        self.loading_text = wx.StaticText(
            panel,
            label="Loading availability data..."
        )
        sizer.Add(self.loading_text, 0, wx.ALL, 10)

        # Will be populated with distributor info
        self.availability_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.availability_sizer, 1, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(sizer)
        return panel

    def _create_alternatives_panel(self, parent) -> wx.Panel:
        """Create alternatives display panel"""
        panel = wx.ScrolledWindow(parent)
        panel.SetScrollRate(10, 10)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Loading message
        self.alt_loading_text = wx.StaticText(
            panel,
            label="Finding alternatives..."
        )
        sizer.Add(self.alt_loading_text, 0, wx.ALL, 10)

        # Will be populated with alternatives
        self.alternatives_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.alternatives_sizer, 1, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(sizer)
        return panel

    def _load_data(self):
        """Load availability and alternatives data"""
        # Run async data loading in thread
        wx.CallAfter(self._async_load_data)

    def _async_load_data(self):
        """Async load data from APIs"""
        # Create async event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Load availability
            mouser = MouserClient()
            digikey = DigiKeyClient()

            mouser_results = loop.run_until_complete(
                mouser.search_component(self.mpn)
            )
            digikey_results = loop.run_until_complete(
                digikey.search_component(self.mpn)
            )

            self.availability = mouser_results + digikey_results

            # Update UI
            wx.CallAfter(self._update_availability_ui)

        finally:
            loop.close()

    def _update_availability_ui(self):
        """Update availability panel with loaded data"""
        self.loading_text.Hide()

        if not self.availability:
            no_data = wx.StaticText(
                self.availability_panel,
                label="❌ No availability data found"
            )
            self.availability_sizer.Add(no_data, 0, wx.ALL, 10)
        else:
            for avail in self.availability:
                card = self._create_availability_card(avail)
                self.availability_sizer.Add(card, 0, wx.EXPAND | wx.ALL, 5)

        self.availability_panel.Layout()
        self.availability_panel.FitInside()

    def _create_availability_card(self, avail: ComponentAvailability) -> wx.Panel:
        """Create card showing distributor availability"""
        card = wx.Panel(self.availability_panel)
        card.SetBackgroundColour(wx.Colour(240, 240, 240))
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Distributor name
        dist_label = wx.StaticText(
            card,
            label=f"{avail.distributor.value.title()}:"
        )
        font = dist_label.GetFont()
        font = font.Bold()
        dist_label.SetFont(font)
        sizer.Add(dist_label, 0, wx.ALL, 5)

        # Stock status
        if avail.in_stock:
            stock_text = f"✅ {avail.stock:,} units in stock"
            color = wx.Colour(0, 128, 0)
        else:
            stock_text = "❌ Out of stock"
            color = wx.Colour(255, 0, 0)

        stock_label = wx.StaticText(card, label=stock_text)
        stock_label.SetForegroundColour(color)
        sizer.Add(stock_label, 0, wx.LEFT | wx.RIGHT, 10)

        # Pricing
        if avail.price_breaks:
            price_text = "💰 "
            price_text += f"${avail.price_breaks[0].price:.2f} @ 1"
            if len(avail.price_breaks) > 1:
                price_text += f"  |  ${avail.price_breaks[1].price:.2f} @ {avail.price_breaks[1].quantity}"

            price_label = wx.StaticText(card, label=price_text)
            sizer.Add(price_label, 0, wx.LEFT | wx.RIGHT, 10)

        # Link to product page
        if avail.product_url:
            link = hl.HyperLinkCtrl(
                card,
                label="🔗 View on " + avail.distributor.value.title(),
                URL=avail.product_url
            )
            sizer.Add(link, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        card.SetSizer(sizer)
        return card

    def _on_refresh(self, event):
        """Refresh data from APIs"""
        self.availability = []
        self.alternatives = []

        # Clear UI
        self.availability_sizer.Clear(True)
        self.alternatives_sizer.Clear(True)

        # Reload
        self._load_data()
```

---

## Phase 3: MCP Integration (Claude Interface)

Same distributor command handler and MCP tools as before, but now they share the same API clients!

**Users can choose:**
- 🖱️ **In KiCad**: Right-click component → Check availability
- 💬 **In Claude**: "Check BOM availability for my board"

---

## Installation & Setup

### For KiCad Plugin:

```bash
# 1. Copy plugin to KiCad plugin directory
# Windows: %APPDATA%/kicad/8.0/scripting/plugins/
cp -r python/kicad_plugins/component_availability ~/.kicad/8.0/scripting/plugins/

# 2. Add API keys to environment or config file
# Create: ~/.kicad/8.0/api_keys.env
MOUSER_API_KEY=your_key_here
DIGIKEY_CLIENT_ID=your_id_here
DIGIKEY_CLIENT_SECRET=your_secret_here

# 3. Restart KiCad
# Plugin will appear in Tools menu and right-click menu
```

### Usage in KiCad:

**Method 1: Right-click**
1. Right-click any component
2. Select "Check Component Availability"
3. Dialog opens with real-time data

**Method 2: Toolbar**
1. Select component(s)
2. Click "Check Availability" toolbar button
3. Same dialog opens

**Method 3: Menu**
1. Tools → Component Availability → Check Selected
2. Dialog opens

---

## Next Steps

Want me to start building this? I recommend:

**Day 1: Core Infrastructure**
- Build shared API clients (base, Mouser, DigiKey)
- Test API connections
- Build data types

**Day 2: KiCad UI**
- Build Action Plugin
- Create availability dialog
- Add context menu integration

**Day 3: Polish & MCP**
- Add alternatives dialog
- Build MCP command handler
- Create TypeScript MCP tools
- Testing

**Timeline:** ~2-3 days of focused work

Ready to start? 🚀
