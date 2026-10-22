"""
strategies/custom_layout.py - Custom layout strategy supporting named files in layouts/ directory.

Features:
  - Loads slot boxes from any layout file in the layouts/ directory (e.g., layouts/testlayout.json).
  - Configurable in config.yaml under strategy: "custom" (or strategy: "<layout_name>").
  - Fits each table into its specified bounding box without changing aspect ratio.
  - Aligns tables to the top-left corner of each slot box.
  - Windows that do not have a box remain strictly in MANUAL CONTROL.
  - Supports multiple monitors (via monitor index or virtual desktop coordinates).
"""

from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

import win_utils
from win_utils import Rect, WindowInfo, WindowPlacement
from strategies.base import ArrangementStrategy
from test_window_launcher import get_layout_dir, load_layout_file, list_layouts


class CustomLayout(ArrangementStrategy):
    """
    Arranges poker tables into custom slot boxes loaded from layouts/ directory.
    Supports multi-monitor setups and preserves aspect ratio.
    """

    name: str = "custom"
    description: str = "Custom slot-based layout loaded from layouts/ directory (multi-monitor)"

    def get_slots(self, config: Dict[str, Any], work_area: Optional[Rect] = None) -> List[Rect]:
        """
        Loads and resolves slot bounding boxes from the configured layout file.
        Resolves monitor offsets if 'monitor' index is specified.
        """
        layout_name = (
            config.get("layout_name")
            or config.get("layout_file")
            or config.get("file")
            or config.get("name")
            or "testlayout"
        )
        layout_dir = get_layout_dir()

        try:
            data, _ = load_layout_file(str(layout_name), layout_dir)
        except Exception:
            # Fallback if named file not found: try first available layout in layouts/
            available = list_layouts(layout_dir)
            if available:
                try:
                    data, _ = load_layout_file(available[0], layout_dir)
                except Exception:
                    return []
            else:
                return []

        # Read slots from data: supports 'slots', 'boxes', 'game_windows', or 'tables'
        raw_slots = (
            data.get("slots")
            or data.get("boxes")
            or data.get("game_windows")
            or data.get("tables")
            or []
        )

        all_monitors = win_utils.get_all_monitors()
        base_x = work_area.x if work_area else 0
        base_y = work_area.y if work_area else 0

        slots: List[Rect] = []

        for item in raw_slots:
            if not isinstance(item, dict):
                continue

            # Extract dimensions: either explicit x, y, width, height or geometry string
            x = item.get("x")
            y = item.get("y")
            w = item.get("width")
            h = item.get("height")

            if w is None or h is None:
                geom = item.get("geometry", "")
                parsed = self._parse_geometry(geom)
                if parsed:
                    w, h, x, y = parsed

            if w is None or h is None or x is None or y is None:
                continue

            w = int(w)
            h = int(h)
            x = int(x)
            y = int(y)

            # Multi-monitor support:
            mon_idx = item.get("monitor")
            if mon_idx is not None and all_monitors:
                try:
                    idx = int(mon_idx)
                    mon = all_monitors[idx] if (0 <= idx < len(all_monitors)) else all_monitors[0]
                    x = mon.work_area.x + x
                    y = mon.work_area.y + y
                except (ValueError, TypeError):
                    pass

            slots.append(Rect(x, y, w, h))

        return slots

    def get_max_spots(self, config: Dict[str, Any]) -> int:
        """
        Returns the number of available slot boxes in the custom layout.
        Windows beyond this number have no box and remain in manual control.
        """
        slots = self.get_slots(config)
        return len(slots) if slots else int(config.get("max_spots", 6))

    def arrange(
        self,
        windows: List[WindowInfo],
        work_area: Rect,
        config: Dict[str, Any],
    ) -> List[WindowPlacement]:
        if not windows:
            return []

        slots = self.get_slots(config, work_area)
        if not slots:
            return []

        keep_aspect_ratio = bool(config.get("keep_aspect_ratio", True))
        cfg_ratio = config.get("aspect_ratio", "auto")
        ratio = self._resolve_aspect_ratio(windows, cfg_ratio)

        # ----------------------------------------------------------------------
        # Fit each window into its slot box:
        # "windows will go to specified slots, to top left corner and resized
        #  so that it fits to the box without changing aspect ratio"
        # ----------------------------------------------------------------------
        target_boxes: List[Rect] = []
        for box in slots:
            if keep_aspect_ratio and ratio > 0:
                # Fit inside box.width, box.height preserving aspect ratio
                w = box.width
                h = int(w / ratio)
                if h > box.height:
                    h = box.height
                    w = int(h * ratio)
            else:
                w = box.width
                h = box.height

            # Placed at top-left corner of the slot box
            target_boxes.append(Rect(box.x, box.y, w, h))

        # ----------------------------------------------------------------------
        # "windows that do not have a box, are manually controlled..."
        # If reuse_mode is set ("last" or "recycle"), all windows are assigned.
        # Otherwise (default empty), only up to len(target_boxes) windows are assigned.
        # ----------------------------------------------------------------------
        reuse_mode = self.get_reuse_mode(config)
        if not reuse_mode:
            active_windows = windows[:len(target_boxes)]
        else:
            active_windows = windows

        # Assign windows to target_boxes preserving any window already in place
        return self.assign_windows_to_spots(active_windows, target_boxes, reuse_mode=reuse_mode)

    @staticmethod
    def _parse_geometry(geom: str) -> Optional[Tuple[int, int, int, int]]:
        """Parses Tkinter/X11 geometry string: WIDTHxHEIGHT+X+Y or WIDTHxHEIGHT-X+Y."""
        if not geom:
            return None
        m = re.match(r"^(\d+)x(\d+)([-+]\d+)([-+]\d+)$", str(geom).strip())
        if m:
            return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        return None
