"""
strategies/grid.py - Grid arrangement strategy (e.g., 2x2, 3x2, or auto).
"""

import math
from typing import Any, Dict, List
from win_utils import Rect, WindowInfo, WindowPlacement
from strategies.base import ArrangementStrategy


class GridLayout(ArrangementStrategy):
    """
    Arranges windows in a grid with configurable columns and rows.
    If rows/columns are set to 0 or 'auto', it calculates an optimal grid.
    """

    name: str = "grid"
    description: str = "Arranges windows in an NxM grid"

    def arrange(
        self,
        windows: List[WindowInfo],
        work_area: Rect,
        config: Dict[str, Any],
    ) -> List[WindowPlacement]:
        if not windows:
            return []

        n = len(windows)
        gap = int(config.get("gap", 2))
        cfg_cols = int(config.get("columns", 0))
        cfg_rows = int(config.get("rows", 0))

        # Auto-compute columns & rows if not specified
        if cfg_cols <= 0 and cfg_rows <= 0:
            if n <= 2:
                cols = n
                rows = 1
            elif n <= 4:
                cols = 2
                rows = 2
            elif n <= 6:
                cols = 3
                rows = 2
            else:
                cols = math.ceil(math.sqrt(n))
                rows = math.ceil(n / cols)
        elif cfg_cols > 0 and cfg_rows <= 0:
            cols = cfg_cols
            rows = math.ceil(n / cols)
        elif cfg_rows > 0 and cfg_cols <= 0:
            rows = cfg_rows
            cols = math.ceil(n / rows)
        else:
            cols = cfg_cols
            rows = cfg_rows

        total_w = work_area.width
        total_h = work_area.height
        base_x = work_area.x
        base_y = work_area.y

        cell_w = max(100, (total_w - (cols - 1) * gap) // cols)
        cell_h = max(100, (total_h - (rows - 1) * gap) // rows)

        grid_spots: List[Rect] = []
        for r in range(rows):
            for c in range(cols):
                x = base_x + c * (cell_w + gap)
                y = base_y + r * (cell_h + gap)
                w = cell_w if c < cols - 1 else (total_w - (x - base_x))
                h = cell_h if r < rows - 1 else (total_h - (y - base_y))
                grid_spots.append(Rect(x=x, y=y, width=w, height=h))

        reuse_mode = self.get_reuse_mode(config)
        if not reuse_mode:
            active_windows = windows[:len(grid_spots)]
        else:
            active_windows = windows

        return self.assign_windows_to_spots(active_windows, grid_spots, reuse_mode=reuse_mode)
