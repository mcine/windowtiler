"""
input_hook.py - Global input hook for Window Tiler.
Listens for middle mouse button clicks, modifier combos, and keyboard shortcuts
to trigger the RNG window and toggle auxiliary/other poker windows.
"""

import ctypes
from ctypes import wintypes
import threading
import time
from typing import Callable, Dict, Optional

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Win32 Hook Constants
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
VK_SHIFT = 0x10
VK_CONTROL = 0x11

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]

user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]

user32.CallNextHookEx.restype = ctypes.c_longlong
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]

user32.GetKeyState.restype = ctypes.c_short
user32.GetKeyState.argtypes = [ctypes.c_int]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


VK_MAP = {
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
    "space": 0x20,
    "tab": 0x09,
    "esc": 0x1B,
    "escape": 0x1B,
    "tilde": 0xC0,
    "`": 0xC0,
    "~": 0xC0,
}


def parse_key_to_vk(key_name: str) -> Optional[int]:
    """Parses a key string like 'F8', 'F9', 'Space', 'R' into a Win32 VK code."""
    clean = (key_name or "").strip().lower()
    if not clean:
        return None
    if clean in VK_MAP:
        return VK_MAP[clean]
    if len(clean) == 1 and clean.isalnum():
        return ord(clean.upper())
    return None


class InputHookManager:
    """
    Manages global low-level mouse and keyboard hooks in a dedicated thread.
    Dispatches events for RNG rolls and other windows (lobby) toggle.
    """

    def __init__(
        self,
        on_rng_trigger: Callable[[], None],
        on_other_trigger: Optional[Callable[[], None]] = None,
        enable_middle_mouse: bool = True,
        rng_shortcut: str = "F8",
        other_shortcut: str = "F9",
        shift_middle_triggers_other: bool = True,
        middle_triggers_both: bool = False,
    ):
        self.on_rng_trigger = on_rng_trigger
        self.on_other_trigger = on_other_trigger

        self.enable_middle_mouse = enable_middle_mouse
        self.rng_vk = parse_key_to_vk(rng_shortcut)
        self.other_vk = parse_key_to_vk(other_shortcut)
        self.shift_middle_triggers_other = shift_middle_triggers_other
        self.middle_triggers_both = middle_triggers_both

        self._mouse_hook = None
        self._kb_hook = None
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._running = False

        self._mouse_proc = HOOKPROC(self._mouse_callback)
        self._kb_proc = HOOKPROC(self._kb_callback)

    def update_settings(
        self,
        enable_middle_mouse: bool,
        rng_shortcut: str,
        other_shortcut: str = "F9",
        shift_middle_triggers_other: bool = True,
        middle_triggers_both: bool = False,
    ) -> None:
        """Updates triggering settings dynamically without restarting the thread."""
        self.enable_middle_mouse = enable_middle_mouse
        self.rng_vk = parse_key_to_vk(rng_shortcut)
        self.other_vk = parse_key_to_vk(other_shortcut)
        self.shift_middle_triggers_other = shift_middle_triggers_other
        self.middle_triggers_both = middle_triggers_both

    def _mouse_callback(self, nCode: int, wParam: int, lParam: int) -> int:
        if nCode >= 0 and self.enable_middle_mouse:
            if wParam == WM_MBUTTONDOWN:
                is_shift = bool(user32.GetKeyState(VK_SHIFT) & 0x8000)
                try:
                    if is_shift and self.shift_middle_triggers_other and self.on_other_trigger:
                        # Shift + Middle Click -> Toggle Other Windows (Lobby)
                        self.on_other_trigger()
                    elif self.middle_triggers_both:
                        # User explicitly opted into triggering both
                        self.on_rng_trigger()
                        if self.on_other_trigger:
                            self.on_other_trigger()
                    else:
                        # Standard Middle Click -> Roll/Toggle RNG
                        self.on_rng_trigger()
                except Exception as e:
                    print(f"[InputHook Error] Mouse callback: {e}")

        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def _kb_callback(self, nCode: int, wParam: int, lParam: int) -> int:
        if nCode >= 0:
            if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                kb_struct = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                vk = kb_struct.vkCode

                if self.rng_vk is not None and vk == self.rng_vk:
                    try:
                        self.on_rng_trigger()
                    except Exception as e:
                        print(f"[InputHook Error] Keyboard RNG callback: {e}")

                elif self.other_vk is not None and vk == self.other_vk and self.on_other_trigger:
                    try:
                        self.on_other_trigger()
                    except Exception as e:
                        print(f"[InputHook Error] Keyboard Other Windows callback: {e}")

        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    def start(self) -> None:
        """Starts the hook message pump in a background daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="WindowTiler-Hook")
        self._thread.start()

    def _run_loop(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()

        self._mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._mouse_proc, None, 0)
        self._kb_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._kb_proc, None, 0)

        msg = wintypes.MSG()
        while self._running and user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._mouse_hook:
            user32.UnhookWindowsHookEx(self._mouse_hook)
            self._mouse_hook = None
        if self._kb_hook:
            user32.UnhookWindowsHookEx(self._kb_hook)
            self._kb_hook = None

    def stop(self) -> None:
        """Stops the hook message loop and uninstalls hooks."""
        if not self._running:
            return
        self._running = False
        if self._thread_id:
            WM_QUIT = 0x0012
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
