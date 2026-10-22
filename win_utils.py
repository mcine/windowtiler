"""
win_utils.py - Windows Win32 API utilities for Poker Window Arranger.
Provides clean Python abstractions for window enumeration, position management,
monitor work areas, and DPI awareness without external binary dependencies.
"""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import List, Optional, Tuple

user32 = ctypes.windll.user32
dwmapi = getattr(ctypes.windll, "dwmapi", None)
kernel32 = ctypes.windll.kernel32

# Win32 Constants
SPI_GETWORKAREA = 0x0030
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SW_RESTORE = 9
SW_SHOWNOACTIVATE = 4
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CHILD = 0x40000000
WS_EX_TOOLWINDOW = 0x00000080
DWMWA_CLOAKED = 14
DWMWA_EXTENDED_FRAME_BOUNDS = 9

# Type definitions for Win32 callbacks and functions
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
MONITORENUMPROC = ctypes.WINFUNCTYPE(
    ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
)

# Set Win32 function signatures to avoid 64-bit parameter truncation
user32.OpenDesktopW.restype = wintypes.HANDLE
user32.OpenDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

user32.SetThreadDesktop.restype = wintypes.BOOL
user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]

user32.CloseDesktop.restype = wintypes.BOOL
user32.CloseDesktop.argtypes = [wintypes.HANDLE]

user32.EnumDesktopWindows.restype = wintypes.BOOL
user32.EnumDesktopWindows.argtypes = [wintypes.HANDLE, WNDENUMPROC, wintypes.LPARAM]

user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]

user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]

user32.IsIconic.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]

user32.IsZoomed.restype = wintypes.BOOL
user32.IsZoomed.argtypes = [wintypes.HWND]

user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]

user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]

user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]

user32.GetWindowRect.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]

user32.SetWindowPos.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]


def attach_to_interactive_desktop() -> None:
    """
    Ensures current thread is attached to the interactive user desktop ('default').
    Allows full window enumeration and placement across subshells, services, and IDE terminals.
    """
    try:
        h_desk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)
    except Exception:
        pass


def enable_dpi_awareness() -> None:
    """Enables Per-Monitor DPI awareness to ensure correct pixel coordinates."""
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


@dataclass(frozen=True)
class Rect:
    """Represents a screen or window rectangle (x, y, width, height)."""
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def to_tuple(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)

    def is_close_to(self, other: "Rect", tolerance: int = 2) -> bool:
        """Checks if two rectangles are practically identical within tolerance pixels."""
        return (
            abs(self.x - other.x) <= tolerance
            and abs(self.y - other.y) <= tolerance
            and abs(self.width - other.width) <= tolerance
            and abs(self.height - other.height) <= tolerance
        )


@dataclass
class WindowInfo:
    """Information about an active top-level window."""
    hwnd: int
    title: str
    class_name: str
    rect: Rect
    is_minimized: bool


@dataclass
class WindowPlacement:
    """Target position and size for a window."""
    hwnd: int
    rect: Rect
    allow_resize: bool = True


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


@dataclass
class MonitorInfo:
    index: int
    device: str
    is_primary: bool
    monitor_rect: Rect
    work_area: Rect


def get_all_monitors() -> List[MonitorInfo]:
    """Enumerates all active display monitors and their usable work areas."""
    monitors: List[MonitorInfo] = []

    def _callback(h_monitor, hdc, lprc, dw_data):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(h_monitor, ctypes.byref(info)):
            m = info.rcMonitor
            w = info.rcWork
            monitors.append(
                MonitorInfo(
                    index=len(monitors),
                    device=info.szDevice,
                    is_primary=bool(info.dwFlags & 1),
                    monitor_rect=Rect(m.left, m.top, m.right - m.left, m.bottom - m.top),
                    work_area=Rect(w.left, w.top, w.right - w.left, w.bottom - w.top),
                )
            )
        return 1

    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_callback), 0)

    if not monitors:
        rect = wintypes.RECT()
        user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
        fallback_rect = Rect(rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
        monitors.append(
            MonitorInfo(
                index=0,
                device="DISPLAY_PRIMARY",
                is_primary=True,
                monitor_rect=fallback_rect,
                work_area=fallback_rect,
            )
        )
    return monitors


def get_monitor_work_area(monitor_index: int = 0) -> Rect:
    """Returns the usable work area (excluding taskbar) for the given monitor index."""
    monitors = get_all_monitors()
    if 0 <= monitor_index < len(monitors):
        return monitors[monitor_index].work_area

    for m in monitors:
        if m.is_primary:
            return m.work_area
    return monitors[0].work_area if monitors else Rect(0, 0, 1920, 1080)


def get_window_rect(hwnd: int) -> Rect:
    """Gets the rectangle of a window."""
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return Rect(r.left, r.top, r.right - r.left, r.bottom - r.top)


def get_window_extended_frame_bounds(hwnd: int) -> Optional[Rect]:
    """Gets the true visible bounds of a window excluding DWM drop shadows."""
    if dwmapi:
        r = wintypes.RECT()
        hr = dwmapi.DwmGetWindowAttribute(
            hwnd,
            DWMWA_EXTENDED_FRAME_BOUNDS,
            ctypes.byref(r),
            ctypes.sizeof(r),
        )
        if hr == 0:
            return Rect(r.left, r.top, r.right - r.left, r.bottom - r.top)
    return None


def is_window_cloaked(hwnd: int) -> bool:
    """Returns True if window is cloaked (e.g. on another virtual desktop)."""
    if dwmapi:
        cloaked = wintypes.DWORD()
        hr = dwmapi.DwmGetWindowAttribute(
            hwnd,
            DWMWA_CLOAKED,
            ctypes.byref(cloaked),
            ctypes.sizeof(cloaked),
        )
        if hr == 0 and cloaked.value != 0:
            return True
    return False


def get_all_top_level_windows() -> List[WindowInfo]:
    """
    Enumerates all top-level windows on the system.
    Supports both standard EnumWindows and EnumDesktopWindows on interactive desktop.
    """
    attach_to_interactive_desktop()

    raw_hwnds: List[int] = []

    def _enum_proc(hwnd, lparam):
        raw_hwnds.append(hwnd)
        return True

    cb = WNDENUMPROC(_enum_proc)

    # Standard EnumWindows
    user32.EnumWindows(cb, 0)

    # Fallback if needed
    if not raw_hwnds:
        h_desktop = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if h_desktop:
            user32.EnumDesktopWindows(h_desktop, cb, 0)
            user32.CloseDesktop(h_desktop)

    results: List[WindowInfo] = []

    for hwnd in raw_hwnds:
        if not user32.IsWindowVisible(hwnd):
            continue

        if is_window_cloaked(hwnd):
            continue

        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        if style & WS_CHILD:
            continue

        ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if ex_style & WS_EX_TOOLWINDOW:
            continue

        title_len = user32.GetWindowTextLengthW(hwnd)
        if title_len == 0:
            continue
        buf = ctypes.create_unicode_buffer(title_len + 1)
        user32.GetWindowTextW(hwnd, buf, title_len + 1)
        title = buf.value.strip()
        if not title:
            continue

        cls_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls_buf, 256)
        class_name = cls_buf.value

        is_minimized = bool(user32.IsIconic(hwnd))
        frame = get_window_extended_frame_bounds(hwnd)
        rect = frame if (frame and frame.width > 0 and frame.height > 0) else get_window_rect(hwnd)

        results.append(
            WindowInfo(
                hwnd=hwnd,
                title=title,
                class_name=class_name,
                rect=rect,
                is_minimized=is_minimized,
            )
        )

    return results


_bottom_hwnds: set = set()


def reset_bottom_state() -> None:
    """Resets the internal set of windows placed in the background."""
    _bottom_hwnds.clear()


def is_placement_needed(
    placement: WindowPlacement,
    compensate_borders: bool = False,
    send_to_bottom: bool = False,
    restore_minimized: bool = False,
) -> bool:
    """
    Checks whether a window actually needs to be moved, resized, or have its z-order adjusted.
    This check is 100% READ-ONLY and performs ZERO modifications on the window.
    Returns True if an adjustment is required, False if the window is already in place.
    """
    hwnd = placement.hwnd
    target = placement.rect
    allow_resize = getattr(placement, "allow_resize", True)

    if not user32.IsWindow(hwnd):
        return False

    is_min = bool(user32.IsIconic(hwnd))
    if is_min:
        return bool(restore_minimized)

    is_zoomed = bool(user32.IsZoomed(hwnd))
    if is_zoomed:
        return True

    current_os_rect = get_window_rect(hwnd)
    frame = get_window_extended_frame_bounds(hwnd)
    current_visible = frame if (frame and frame.width > 0 and frame.height > 0) else current_os_rect

    if not allow_resize:
        is_in_place = (abs(current_visible.x - target.x) <= 4 and abs(current_visible.y - target.y) <= 4)
    else:
        check_rect = current_visible if compensate_borders else current_os_rect
        is_in_place = check_rect.is_close_to(target, tolerance=4)

    if is_in_place:
        if send_to_bottom:
            fg_hwnd = user32.GetForegroundWindow()
            if fg_hwnd == hwnd:
                return False  # User is using this window; do not send to bottom
            if hwnd in _bottom_hwnds:
                return False  # Already in place and already in background
            return True  # Needs initial send to bottom
        else:
            return False

    return True


def apply_window_placement(
    placement: WindowPlacement,
    restore_minimized: bool = False,
    bring_to_front: bool = False,
    compensate_borders: bool = False,
    send_to_bottom: bool = False,
) -> bool:
    """
    Applies the target placement (position and size) to a window ONLY if needed.
    Does absolutely nothing if the window is already in place.
    """
    if not is_placement_needed(
        placement,
        compensate_borders=compensate_borders,
        send_to_bottom=send_to_bottom,
        restore_minimized=restore_minimized,
    ):
        return False

    attach_to_interactive_desktop()

    hwnd = placement.hwnd
    target = placement.rect
    allow_resize = getattr(placement, "allow_resize", True)

    is_min = bool(user32.IsIconic(hwnd))
    if is_min:
        if restore_minimized:
            user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
        else:
            return False

    # If maximized, restore window to normal size without activating or bringing to top
    if user32.IsZoomed(hwnd):
        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)

    current_os_rect = get_window_rect(hwnd)
    frame = get_window_extended_frame_bounds(hwnd)

    target_x = target.x
    target_y = target.y
    target_w = target.width
    target_h = target.height

    if compensate_borders and frame:
        border_left = frame.x - current_os_rect.x
        border_top = frame.y - current_os_rect.y
        border_right = current_os_rect.right - frame.right
        border_bottom = current_os_rect.bottom - frame.bottom

        # Compensate for invisible drop shadow borders so the VISIBLE frame aligns to target
        if 0 <= border_left <= 40 and 0 <= border_right <= 40:
            target_x = target.x - border_left
            target_w = target.width + border_left + border_right
        if 0 <= border_top <= 40 and 0 <= border_bottom <= 40:
            target_y = target.y - border_top
            target_h = target.height + border_top + border_bottom

    flags = SWP_NOACTIVATE
    if not allow_resize:
        flags |= SWP_NOSIZE

    hwnd_insert_after = 0
    if send_to_bottom:
        fg_hwnd = user32.GetForegroundWindow()
        if fg_hwnd == hwnd:
            flags |= SWP_NOZORDER
        else:
            hwnd_insert_after = 1  # HWND_BOTTOM
    elif not bring_to_front:
        flags |= SWP_NOZORDER

    success = bool(user32.SetWindowPos(hwnd, hwnd_insert_after, target_x, target_y, target_w, target_h, flags))
    if success:
        if send_to_bottom:
            _bottom_hwnds.add(hwnd)
        else:
            _bottom_hwnds.discard(hwnd)
    return success
