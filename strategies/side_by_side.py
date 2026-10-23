"""
strategies/side_by_side.py - Window arrangement strategy keeping aspect ratio.

Layout rules:
  - Preserves table aspect ratio at all times across all window counts.
  - Windows already in place are preserved and NOT re-adjusted or reshuffled.
  - 1 table: Takes up to half screen width (or full if configured), maintaining aspect ratio.
  - 2 tables: Side-by-side (Left and Right). Resized to fill half screen width each with 0 gap,
    maintaining aspect ratio.
  - 3 to 4 tables: 2 columns (Left and Right) x 2 rows (Top and Bottom) with vertical overlap,
    touching screen edges.
  - > 4 tables: 6 spots (3 columns horizontally x 2 rows vertically), evenly overlapped.
    Excess tables (> 6) remain unarranged in the background.
    When tables close, spots refill so always 6 are arranged.
"""

from typing import Any, Dict, List, Optional
from win_utils import Rect, WindowInfo, WindowPlacement
from strategies.base import ArrangementStrategy


class SideBySideLayout(ArrangementStrategy):
    """
    Arranges poker tables into 1, 2, 4, or 6 spots, strictly preserving table aspect ratios.
    Windows already in place are kept in their spots and not re-adjusted.
    """

    name: str = "default"
    description: str = "Default layout (side-by-side, aspect ratio preserved)"

    def arrange(
        self,
        windows: List[WindowInfo],
        work_area: Rect,
        config: Dict[str, Any],
    ) -> List[WindowPlacement]:
        if not windows:
            return []

        gap = int(config.get("gap", 0))
        max_spots = int(config.get("max_spots", 6))
        keep_aspect_ratio = bool(config.get("keep_aspect_ratio", True))
        cfg_ratio = config.get("aspect_ratio", "auto")
        vertical_overlap = int(config.get("vertical_overlap", 50))
        single_window_slot = str(config.get("single_window_slot", "left")).lower()
        reuse_mode = self.get_reuse_mode(config)

        # 4-window mode vertical overlap: can be configured independently via vertical_overlap_4_tables
        # Defaults to a bigger overlap (200px) when not specified, or inherits vertical_overlap if explicitly given
        v_overlap_4_cfg = config.get("vertical_overlap_4_tables", config.get("vertical_overlap_4", None))
        if v_overlap_4_cfg is not None:
            vertical_overlap_4 = int(v_overlap_4_cfg)
        elif "vertical_overlap" in config:
            vertical_overlap_4 = int(config["vertical_overlap"])
        else:
            vertical_overlap_4 = 200

        # If reuse_mode is empty (default), only arrange up to max_spots
        if not reuse_mode:
            active_windows = windows[:max_spots]
            n_base = len(active_windows)
        else:
            active_windows = windows
            n_base = min(len(windows), max_spots)

        total_w = work_area.width
        total_h = work_area.height
        base_x = work_area.x
        base_y = work_area.y

        # Determine Aspect Ratio (width / height)
        ratio = self._resolve_aspect_ratio(windows, cfg_ratio)

        # ----------------------------------------------------------------------
        # Case A: 1 or 2 Windows (1 Row: Side-by-Side Left and Right)
        # ----------------------------------------------------------------------
        if n_base <= 2:
            # 2 window version fills the whole screen width (half screen width each)
            table_w = (total_w - gap) // 2
            w_right = total_w - table_w - gap

            if keep_aspect_ratio and ratio > 0:
                table_h = min(total_h, int(table_w / ratio))
            else:
                table_h = total_h

            if n_base == 1:
                if single_window_slot == "right":
                    x = base_x + total_w - table_w
                elif single_window_slot == "center":
                    x = base_x + (total_w - table_w) // 2
                elif single_window_slot == "full":
                    w_full = total_w
                    h_full = min(total_h, int(w_full / ratio)) if (keep_aspect_ratio and ratio > 0) else total_h
                    x_full = base_x + (total_w - w_full) // 2
                    return self.assign_windows_to_spots(active_windows, [Rect(x_full, base_y, w_full, h_full)], reuse_mode=reuse_mode)
                else:  # 'left' default
                    x = base_x
                return self.assign_windows_to_spots(active_windows, [Rect(x, base_y, table_w, table_h)], reuse_mode=reuse_mode)

            # n_base == 2: Left window at base_x, Right window at base_x + table_w + gap
            # Fills the entire screen width: base_x to base_x + total_w with zero horizontal gap
            spots_2 = [
                Rect(base_x, base_y, table_w, table_h),
                Rect(base_x + table_w + gap, base_y, w_right, table_h),
            ]
            return self.assign_windows_to_spots(active_windows, spots_2, reuse_mode=reuse_mode)

        # ----------------------------------------------------------------------
        # Case B: 3 or 4 Windows (2 Columns x 2 Rows with Vertical Overlap)
        # ----------------------------------------------------------------------
        if n_base <= 4:
            if keep_aspect_ratio and ratio > 0:
                table_h = min(total_h, (total_h + vertical_overlap_4) // 2)
                table_w = int(table_h * ratio)
                if table_w > (total_w - gap) // 2:
                    table_w = (total_w - gap) // 2
                    table_h = int(table_w / ratio)
            else:
                table_w = (total_w - gap) // 2
                table_h = (total_h + vertical_overlap_4) // 2

            # Left column at base_x, right column directly adjacent with gap
            # Any remaining horizontal space (gap) is placed on the right side
            cols_x = [
                base_x,
                base_x + table_w + gap,
            ]
            step_y = (table_h - vertical_overlap_4) if vertical_overlap_4 > 0 else (table_h + gap)
            rows_y = [
                base_y,
                base_y + min(total_h - table_h, max(0, step_y)),
            ]

            if n_base == 3:
                # 2 on top (horizontal: left, right), 1 on bottom left (vertical)
                spots_3 = [
                    Rect(cols_x[0], rows_y[0], table_w, table_h),  # 0: Top-Left
                    Rect(cols_x[1], rows_y[0], table_w, table_h),  # 1: Top-Right
                    Rect(cols_x[0], rows_y[1], table_w, table_h),  # 2: Bottom-Left
                ]
                return self.assign_windows_to_spots(active_windows, spots_3, reuse_mode=reuse_mode)

            # n_base == 4: 4 corners (2 left, 2 right)
            spots_4 = [
                Rect(cols_x[0], rows_y[0], table_w, table_h),
                Rect(cols_x[1], rows_y[0], table_w, table_h),
                Rect(cols_x[0], rows_y[1], table_w, table_h),
                Rect(cols_x[1], rows_y[1], table_w, table_h),
            ]
            return self.assign_windows_to_spots(active_windows, spots_4, reuse_mode=reuse_mode)

        # ----------------------------------------------------------------------
        # Case C: > 4 Windows (6 Spots: 3 Columns Horizontally x 2 Rows Vertically)
        # ----------------------------------------------------------------------
        if keep_aspect_ratio and ratio > 0:
            table_h = min(total_h, (total_h + vertical_overlap) // 2)
            table_w = int(table_h * ratio)
            if table_w > total_w:
                table_w = total_w
                table_h = int(table_w / ratio)
        else:
            table_w = (total_w - 2 * gap) // 3
            table_h = (total_h + vertical_overlap) // 2

        col_step = (total_w - table_w) / 2.0 if total_w > table_w else 0.0
        cols_x = [
            base_x,
            base_x + int(col_step),
            base_x + total_w - table_w,
        ]
        step_y = (table_h - vertical_overlap) if vertical_overlap > 0 else (table_h + gap)
        rows_y = [
            base_y,
            base_y + min(total_h - table_h, max(0, step_y)),
        ]

        six_spots = [
            Rect(cols_x[0], rows_y[0], table_w, table_h),  # Spot 0: Top-Left
            Rect(cols_x[1], rows_y[0], table_w, table_h),  # Spot 1: Top-Center
            Rect(cols_x[2], rows_y[0], table_w, table_h),  # Spot 2: Top-Right
            Rect(cols_x[0], rows_y[1], table_w, table_h),  # Spot 3: Bottom-Left
            Rect(cols_x[1], rows_y[1], table_w, table_h),  # Spot 4: Bottom-Center
            Rect(cols_x[2], rows_y[1], table_w, table_h),  # Spot 5: Bottom-Right
        ]

        return self.assign_windows_to_spots(active_windows, six_spots, reuse_mode=reuse_mode)

    def _resolve_aspect_ratio(self, windows: List[WindowInfo], cfg_ratio: Any) -> float:
        """Determines the target aspect ratio (width / height) for poker windows."""
        if cfg_ratio not in ("auto", "", None):
            try:
                val = float(cfg_ratio)
                if val > 0:
                    return val
            except (ValueError, TypeError):
                pass

        for w in windows:
            if w.rect.height > 0:
                measured = w.rect.width / w.rect.height
                if 1.1 <= measured <= 2.2:
                    return measured

        return 1.625
