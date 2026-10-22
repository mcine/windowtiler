"""
tests/test_rng.py - Tests for the Random Number Generator (RNG) logic and input hooks.
"""

from rng_window import RNGWindow
from input_hook import parse_key_to_vk


def test_rng_threshold_color_rules():
    """
    User requirement:
    'if random number is bigger than this value, the number is green
    and if not, number is red... default value is 50 and it can be configured. ...'
    """
    config = {
        "default_threshold": 50,
        "auto_update_seconds": 10.0,
        "stay_on_top": True,
    }
    rng = RNGWindow(config)
    assert rng.threshold == 50

    # Test numbers vs threshold 50
    rng.threshold = 50

    # 1. Bigger than threshold -> GREEN
    rng.current_number = 75
    assert rng.current_number > rng.threshold
    # Verification of green color rule
    is_green = rng.current_number > rng.threshold
    color = rng.COLOR_GREEN if is_green else rng.COLOR_RED
    assert color == rng.COLOR_GREEN

    # 2. Equal or lower than threshold -> RED
    rng.current_number = 50
    assert not (rng.current_number > rng.threshold)
    color = rng.COLOR_GREEN if (rng.current_number > rng.threshold) else rng.COLOR_RED
    assert color == rng.COLOR_RED

    rng.current_number = 12
    assert not (rng.current_number > rng.threshold)
    color = rng.COLOR_GREEN if (rng.current_number > rng.threshold) else rng.COLOR_RED
    assert color == rng.COLOR_RED

    # 3. Dynamic slider threshold adjustment
    rng._on_slider_change("70")
    assert rng.threshold == 70

    rng.current_number = 65  # Now <= 70 -> RED
    assert (rng.COLOR_GREEN if rng.current_number > rng.threshold else rng.COLOR_RED) == rng.COLOR_RED

    rng.current_number = 71  # Now > 70 -> GREEN
    assert (rng.COLOR_GREEN if rng.current_number > rng.threshold else rng.COLOR_RED) == rng.COLOR_GREEN


def test_parse_key_to_vk():
    assert parse_key_to_vk("F8") == 0x77
    assert parse_key_to_vk("F9") == 0x78
    assert parse_key_to_vk("f1") == 0x70
    assert parse_key_to_vk("F12") == 0x7B
    assert parse_key_to_vk("Space") == 0x20
    assert parse_key_to_vk("r") == ord("R")
    assert parse_key_to_vk("R") == ord("R")
    assert parse_key_to_vk("") is None


def test_rng_position_calculation():
    class DummyRoot:
        def winfo_screenwidth(self):
            return 1920

        def winfo_screenheight(self):
            return 1080

    root = DummyRoot()

    # Top center (default)
    rng_tc = RNGWindow({"position": "top_center", "offset_y": 0})
    x, y = rng_tc.calculate_position(root, 240, 250)
    assert x == (1920 - 240) // 2  # 840
    assert y == 0

    # Center
    rng_c = RNGWindow({"position": "center"})
    x, y = rng_c.calculate_position(root, 240, 250)
    assert x == (1920 - 240) // 2
    assert y == (1080 - 250) // 2

    # Custom
    rng_cust = RNGWindow({"position": "custom", "custom_x": 100, "custom_y": 50})
    x, y = rng_cust.calculate_position(root, 240, 250)
    assert (x, y) == (100, 50)
