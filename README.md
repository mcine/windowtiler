# Window Tiler

**Window Tiler** is a non-intrusive Windows desktop tiling manager built to assist my poker hobby, but there is nothing poker specific in this project.

Window tiling apps are currently subscriptions and paying monthly for tiling is not for me. So I vibecoded my own. I don't really care how it works and vibe coding quality is fine at least for now. I will end this manual editing now and enjoy the AI documention.

It automatically organizes poker tables with **zero screen waste**, strictly preserves native **aspect ratios**, positions auxiliary windows (lobbies, cashiers, tournament lobbies, notes) at the bottom without resizing, and provides an instant on-screen **Random Number Generator (RNG)** decision HUD.


---

## Table of Contents

1. [Key Features](#key-features)
2. [Quick Start](#quick-start)
3. [How Window Tiler Works](#how-window-tiler-works)
4. [Layout Strategies](#layout-strategies)
   - [Side-by-Side (Default)](#1-side-by-side-strategy-default)
   - [Custom Layouts & Multi-Monitor](#2-custom-layouts-directory-layouts)
   - [Reuse Window Slots (Overflow Handling)](#3-reuse-window-slots-overflow-handling)
5. [Auxiliary Windows (Lobbies & Cashier)](#auxiliary-windows-lobbies-cashier-notes)
6. [RNG Decision HUD](#rng-decision-hud)
7. [Test Window Launcher](#test-window-launcher-interactive-simulator)
8. [Configuration Reference (`config.yaml`)](#configuration-reference-configyaml)
9. [Running Unit Tests](#running-unit-tests)
10. [FAQ & Troubleshooting](#faq--troubleshooting)

---

## Key Features

- **Strict Aspect Ratio Preservation**: Tables maintain their natural dimensions (e.g. 16:10 / 1.625) without stretching, distorted felt graphics, or warped fonts.
- **Zero Screen Waste & Seamless Seams**: Tables seamlessly snap to screen edges and neighboring tables with 0-pixel gaps, compensating for Windows 10/11 invisible DWM drop-shadow borders. In 2-table side-by-side mode, tables completely fill the screen width with zero gap.
- **In-Place Stability**: If your windows are already in the correct positions, Window Tiler executes **zero Win32 API window movements**. No jitter, no flickering, no reshuffling, and no focus stealing.
- **Table Limit & Overflow Slot Reuse**: Configurable maximum arranged spots (default: 6 spots) and overflow handling via `reuse_window_slots` (`""` to ignore/keep manual control, `"last"` to stack overflow on the last slot, or `"recycle"` to loop back to slot 0, slot 1, etc.).
- **Natural Vertical Spacing**: If widescreen aspect ratio constraints leave vertical headroom, the extra space is positioned at the **bottom** of the screen rather than creating unnatural voids between table rows.
- **Auxiliary Window & Cashier Protection**:
  - Lobbies and notes are aligned along the bottom at their natural size without being resized (position changes only).
  - Cashier and banking windows are protected and will never be pushed behind tables or hidden during transactions.
  - Fast bring-to-front toggles via **`F9`** or **`Shift + Middle Click`**.
- **Floating RNG HUD**: Frameless, draggable, on-top decision tool (0–100) with a colored threshold slider (Green when roll > threshold, Red when roll &le; threshold) toggled via **`F8`** or **`Middle Mouse Click`**.
- **Custom Layouts & Multi-Monitor Support**: Define custom slot bounding boxes across one or more monitors in `layouts/*.json` or `.yaml`. Tables fit top-left aligned inside designated boxes while preserving aspect ratio.
- **Live Configuration Hot-Reloading**: Automatically detects edits to `config.yaml` every 10 seconds and reloads without needing to restart the software.

---

## Quick Start

### 1. Requirements
- Windows 10 or Windows 11 (64-bit recommended)
- Python 3.10+ (tested on Python 3.13)

### 2. Installation
Clone or download this repository, open PowerShell in the project directory, and install dependencies:

```powershell
# Navigate to the project directory
cd c:\misc\code\pokerwindows

# Install requirements
py -m pip install -r requirements.txt
```

*(Dependencies include: `pywin32`, `pyyaml`, `pytest`)*

### 3. Running Window Tiler
Start the Window Tiler background manager:

```powershell
py app.py
```

Window Tiler will immediately start scanning for matching poker windows and apply the configured layout.

### 4. Interactive Simulation & Testing
You can safely test and fine-tune your layouts without opening real poker clients or risking money by using the included **Test Window Launcher**:

```powershell
py test_window_launcher.py
```

---

## How Window Tiler Works

Window Tiler runs a non-blocking background loop:
1. **Window Identification**: Scans open windows matching your simple string list filters (`titles:` such as `Hold'em`, `Omaha`, `Table`) while ignoring excluded applications (`exclude:` such as browsers, IDEs, Explorer).
2. **Pre-Flight Stability Check (`is_placement_needed`)**: Compares every window's current visible screen coordinates against its target position. If all windows are already within tolerance (&le; 4 pixels), **no Win32 repositioning commands are executed**.
3. **Smart Spot Persistence**: Assigns windows to layout spots based on proximity and existing assignments, ensuring tables don't swap places or jump around during regular gameplay.
4. **Active Focus Respect**: Protects whatever window you are actively interacting with (such as the Cashier or lobby) without stealing focus or forcing tables on top.

---

## Layout Strategies

Configure the active strategy in [`config.yaml`](file:///c:/misc/code/pokerwindows/config.yaml#L52):

```yaml
game_windows:
  strategy: "default" # Options: 'default', 'custom', 'grid', 'stack'
```

### 1. Default Layout

The **`default`** layout arranges tables side-by-side with zero pixel gaps between columns:
- **1 Table**: Positioned at top-left, scaled to fit work area height.
- **2 Tables**: Divides and fills 100% of the screen width with zero gaps between the two columns and screen edges.
- **3 to 4 Tables**: 2 columns &times; 2 rows with configurable vertical overlap (default 200px) that keeps bet controls visible while using 0-pixel gap between adjacent columns and allocating any leftover horizontal space to the right side. Old windows fill the top row horizontally first (Top-Left then Top-Right), new windows fill the bottom row vertically, and newly opened tables go to the back behind older tables.
- **5 to 6 Tables**: 3 columns &times; 2 rows with vertical overlap (default 50px). Leftover vertical space is allocated to the bottom of the screen.

### 2. Custom Layouts (Directory: `layouts/`)

Save and load arbitrary window geometries:
- Place layouts in `layouts/<name>.json` (or `.yaml`).
- Each layout contains an array of slot boxes with `x`, `y`, `width`, `height`. Window Tiler generates display titles automatically in window detection order.
- Tables fit top-left aligned inside designated boxes while preserving aspect ratio.
- Excess tables beyond defined boxes remain unarranged in manual control (unless `reuse_window_slots` is configured).

### 3. Reuse Window Slots (Overflow Handling)

When you have more open tables than available spots or boxes, configure how overflow tables are handled via `reuse_window_slots` in `config.yaml`:

```yaml
game_windows:
  reuse_window_slots: ""  # Options: "" (empty, default), "last" or "last slot", "recycle"
```

- **`""` (Empty / Default - Ignore Overflow)**:
  Tables beyond the available spots/boxes remain strictly in **manual control** (unarranged). If any arranged table closes, the next open table automatically steps in to fill the vacated spot.
- **`"last"` or `"last slot"`**:
  All overflow tables are placed into the **last slot**.
- **`"recycle"`**:
  Recycles slots in order: the 1st overflow table is placed into the **1st slot**, the 2nd into the **2nd slot**, and so on.

---

## Auxiliary Windows (Lobbies, Cashier, Notes)

Auxiliary poker windows are managed alongside game tables:
- **Position Only (No Resizing)**: Window Tiler strictly changes window positions (`x`, `y`) without resizing them (`SWP_NOSIZE`). The natural width and height of lobbies, cashiers, and note windows are preserved 100%.
- **Side-by-Side Bottom Alignment**: Auxiliary windows are placed side-by-side along the bottom edge of the screen.
- **Adjacent Multi-Window Placement**: When a second auxiliary window is open (e.g. player notes or cashier), it is positioned directly adjacent to the first window along the bottom edge (`x = win1.x + win1.width + gap`).
- **Dynamic Space Reservation**:
  - **$\le 2$ Game Tables**: Space is reserved at the bottom so lobbies remain visible side-by-side with your tables.
  - **$> 2$ Game Tables**: Game tables expand to fill the entire screen, and lobbies rest in the background.
- **Cashier Protection**: Cashiers, deposits, and banking windows are protected so they are **never sent to the background** or hidden while you are performing transactions.
- **Quick-View Controls**:
  - Press **`F9`** anytime to bring all auxiliary windows to the front.
  - Press **`Shift + Middle Click`** to pop auxiliary windows to the front without disturbing your betting controls.

---

## RNG Decision HUD

Window Tiler features an integrated Random Number Generator (RNG) HUD for mixed-strategy decisions (e.g. 70% Call / 30% Fold):

- **Visual Decision Rule**:
  - Displays a random number between **0 and 100** in large bold font.
  - Dynamic color feedback: **GREEN** if `Roll > Slider Threshold`, **RED** if `Roll <= Slider Threshold`.
- **Threshold Slider**: Drag the interactive slider to set your required frequency.
- **Auto Re-Roll**: Automatically rolls every 10 seconds, or rolls instantly on click or window focus.
- **Activation Shortcuts**:
  - Press **`F8`** or click your **Middle Mouse Button** anywhere to instantly display or toggle the RNG window.
  - Always stays on top of tables when visible.

---

## Test Window Launcher (Interactive Simulator)

The test launcher (`test_window_launcher.py`) provides an interactive GUI to test, visualize, and save window layouts:

```powershell
# Open the test launcher GUI
py test_window_launcher.py

# Launch directly loading a saved layout preset
py test_window_launcher.py --load testlayout
```

### Features of the Launcher:
- **One-Click Presets**: Quickly spawn `[1]`, `[2]`, `[3]`, `[4]`, `[6]`, or `[8]` simulated poker tables.
- **Auxiliary Spawning**: One-click buttons to spawn simulated "Lobby" and "Cashier" windows.
- **Layout Manager (Save / Load / Delete)**:
  - **Save**: Type a layout name and click **💾 Save Layout** to save slot coordinates (`x`, `y`, `width`, `height`) to `layouts/<name>.json`. Titles, subtitles, colors, and geometries are not saved.
  - **Load**: Select a layout from the dropdown and click **📂 Load Layout** (or press Enter) to respawn windows into the defined slots. Titles and colors are generated automatically by the tool in detection order.
  - **Delete**: Click **🗑 Delete** to remove obsolete layout files from disk.
- **Keyboard Shortcuts in Control Panel**:
  - `G`: Add a game table
  - `D`: Remove the last game table
  - `1` through `8`: Spawn corresponding number of tables

---

## Configuration Reference (`config.yaml`)

Edit `config.yaml` to customize settings. Changes are hot-reloaded automatically every 10 seconds:

```yaml
# ==============================================================================
# 1. GAME WINDOWS
# ==============================================================================
game_windows:
  filter:
    # List of strings: if any string is part of the title, it is counted as a game window
    titles:
      - "Hold'em"
      - "Omaha"
      - "Tournament"
      - "Table"
      - "NLH"

    # Exclude strings: if any string is part of the title, the window is ignored
    exclude:
      - "Lobby"
      - "Cashier"
      - "Tournament Lobby"
      - "File Explorer"
      - "Visual Studio"
      - "WhatsApp"
      - "Discord"

    # Win32 Class Name strings (optional list)
    classes: []

    # Exclude Win32 Class Names
    exclude_classes:
      - "CabinetWClass"
      - "Chrome_WidgetWin_1"
      - "CASCADIA_HOSTING_WINDOW_C"
      - "ConsoleWindowClass"
      - "Progman"
      - "WorkerW"

    case_sensitive: false
    sort_by: "hwnd"

  strategy: "default" # 'default', 'custom', 'grid', or 'stack'

# ==============================================================================
# 2. OTHER POKER WINDOWS (Lobbies, Cashier, Notes)
# ==============================================================================
other_windows:
  enabled: true
  filter:
    titles:
      - "Lobby"
      - "Cashier"
      - "Tournament Lobby"
      - "Notes"
      - "HUD"

    exclude:
      - "File Explorer"
      - "Visual Studio"
      - "WhatsApp"
      - "Discord"
      - "PuTTY"

    classes: []

    exclude_classes:
      - "CabinetWClass"
      - "Chrome_WidgetWin_1"

  layout:
    strategy: "other_bottom"
    gap: 0
    resize: false # Strict position-only (no resizing)
    alignment: "left"
```

---

## Running Unit Tests

Run the full pytest suite:

```powershell
py -3.13 -m pytest -v
```

---

## FAQ & Troubleshooting

### Q: Why do my other/auxiliary windows not get resized?
**A:** By design, Window Tiler only updates the positions (`x`, `y`) of auxiliary windows (lobbies, note windows, cashiers) placing them side-by-side along the bottom. Windows Win32 API `SWP_NOSIZE` is used so their original dimensions and layouts are never modified.

### Q: Why do tables have vertical overlap in 4-table mode?
**A:** Standard poker tables maintain a widescreen ~16:10 aspect ratio. Stacking two full-height tables vertically would either make them too small or distort their graphics. The vertical overlap (configurable via `vertical_overlap_4_tables: 200`) ensures table felts are large and legible while keeping all betting buttons and action controls visible.
