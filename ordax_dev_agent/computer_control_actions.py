"""Typed Windows desktop observation and input for ORDAX Dev.

These actions are intentionally separate from browser control. They operate on
the interactive Windows desktop and therefore must be gated by the Chat App's
project capability policy before being exposed to a model.
"""
from __future__ import annotations

import ctypes
import os
import time
import uuid
from ctypes import wintypes
from pathlib import Path
from typing import Any

from PIL import ImageGrab

from .models import ActionResult


_MOUSE = {
    "left": (0x0002, 0x0004),
    "right": (0x0008, 0x0010),
    "middle": (0x0020, 0x0040),
}
_WHEEL = 0x0800
_HWHEEL = 0x01000

_VK = {
    "backspace": 0x08,
    "tab": 0x09,
    "enter": 0x0D,
    "shift": 0x10,
    "ctrl": 0x11,
    "alt": 0x12,
    "pause": 0x13,
    "capslock": 0x14,
    "escape": 0x1B,
    "space": 0x20,
    "pageup": 0x21,
    "pagedown": 0x22,
    "end": 0x23,
    "home": 0x24,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "insert": 0x2D,
    "delete": 0x2E,
    "win": 0x5B,
}
for _i in range(1, 25):
    _VK[f"f{_i}"] = 0x6F + _i
for _ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
    _VK[_ch.lower()] = ord(_ch)

_KEYEVENTF_KEYUP = 0x0002
_KEYEVENTF_UNICODE = 0x0004
_INPUT_KEYBOARD = 1


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", _INPUTUNION)]


class ComputerControlActions:
    @staticmethod
    def _windows_only() -> None:
        if os.name != "nt":
            raise ValueError("computer control is currently available only on Windows")

    @staticmethod
    def _user32():
        ComputerControlActions._windows_only()
        return ctypes.windll.user32

    def _computer_artifact_path(self, project) -> Path:
        root = (self.config.state_dir / "artifacts" / project.slug).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root / f"computer-{uuid.uuid4().hex}.png"

    @staticmethod
    def _window_info(hwnd: int) -> dict[str, Any] | None:
        user32 = ctypes.windll.user32
        if not hwnd or not user32.IsWindowVisible(hwnd):
            return None
        length = int(user32.GetWindowTextLengthW(hwnd))
        if length <= 0:
            return None
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title:
            return None
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return {
            "handle": f"0x{int(hwnd):X}",
            "title": title[:1000],
            "pid": int(pid.value),
            "rect": {
                "left": int(rect.left),
                "top": int(rect.top),
                "right": int(rect.right),
                "bottom": int(rect.bottom),
                "width": max(0, int(rect.right - rect.left)),
                "height": max(0, int(rect.bottom - rect.top)),
            },
            "foreground": int(hwnd) == int(user32.GetForegroundWindow()),
        }

    @staticmethod
    def _parse_handle(raw: Any) -> int:
        if isinstance(raw, int):
            value = raw
        else:
            text = str(raw or "").strip().lower()
            try:
                value = int(text, 16) if text.startswith("0x") else int(text)
            except ValueError as error:
                raise ValueError("window handle must be an integer or 0x-prefixed value") from error
        if value <= 0:
            raise ValueError("window handle must be positive")
        return value

    def computer_windows(self, payload: dict[str, Any]) -> ActionResult:
        self._project(payload)
        try:
            self._windows_only()
        except ValueError as error:
            return ActionResult(False, str(error))
        max_items = max(1, min(int(payload.get("max_items", 100)), 500))
        items: list[dict[str, Any]] = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def callback(hwnd, _lparam):
            info = self._window_info(int(hwnd))
            if info is not None:
                items.append(info)
            return len(items) < max_items

        callback_ref = callback_type(callback)
        ctypes.windll.user32.EnumWindows(callback_ref, 0)
        items.sort(key=lambda item: (not item["foreground"], item["title"].casefold()))
        return ActionResult(
            True,
            "desktop windows ready",
            {"windows": items[:max_items], "truncated": len(items) >= max_items},
        )

    def computer_active_window(self, payload: dict[str, Any]) -> ActionResult:
        self._project(payload)
        try:
            hwnd = int(self._user32().GetForegroundWindow())
        except ValueError as error:
            return ActionResult(False, str(error))
        info = self._window_info(hwnd)
        if info is None:
            return ActionResult(False, "foreground window is unavailable")
        return ActionResult(True, "foreground window ready", info)

    def computer_screenshot(self, payload: dict[str, Any]) -> ActionResult:
        project = self._project(payload)
        try:
            self._windows_only()
        except ValueError as error:
            return ActionResult(False, str(error))
        mode = str(payload.get("mode") or "desktop").strip().lower()
        if mode not in {"desktop", "active_window"}:
            return ActionResult(False, "mode must be desktop or active_window")
        target = self._computer_artifact_path(project)
        try:
            if mode == "active_window":
                hwnd = int(self._user32().GetForegroundWindow())
                info = self._window_info(hwnd)
                if info is None:
                    return ActionResult(False, "foreground window is unavailable")
                rect = info["rect"]
                bbox = (rect["left"], rect["top"], rect["right"], rect["bottom"])
                image = ImageGrab.grab(bbox=bbox, all_screens=True)
            else:
                image = ImageGrab.grab(all_screens=True)
            image.save(target, "PNG")
        except Exception as error:
            return ActionResult(False, f"desktop screenshot failed: {type(error).__name__}: {error}")
        width, height = image.size
        return ActionResult(
            True,
            "desktop screenshot captured",
            {
                "project": project.slug,
                "mode": mode,
                "artifact_name": target.name,
                "image_path": str(target),
                "width": int(width),
                "height": int(height),
                "size_bytes": int(target.stat().st_size),
            },
        )

    def computer_focus_window(self, payload: dict[str, Any]) -> ActionResult:
        self._project(payload)
        try:
            user32 = self._user32()
            hwnd = self._parse_handle(payload.get("handle"))
        except ValueError as error:
            return ActionResult(False, str(error))
        if not user32.IsWindow(hwnd):
            return ActionResult(False, "window handle does not exist")
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.BringWindowToTop(hwnd)
        ok = bool(user32.SetForegroundWindow(hwnd))
        time.sleep(0.05)
        info = self._window_info(hwnd)
        return ActionResult(
            bool(ok or (info and info.get("foreground"))),
            "window focused" if ok or (info and info.get("foreground")) else "window focus was rejected by Windows",
            info or {"handle": f"0x{hwnd:X}"},
        )

    def computer_click(self, payload: dict[str, Any]) -> ActionResult:
        self._project(payload)
        try:
            user32 = self._user32()
        except ValueError as error:
            return ActionResult(False, str(error))
        try:
            x = int(payload.get("x"))
            y = int(payload.get("y"))
            clicks = int(payload.get("clicks", 1))
        except (TypeError, ValueError):
            return ActionResult(False, "x, y and clicks must be integers")
        button = str(payload.get("button") or "left").lower()
        if button not in _MOUSE:
            return ActionResult(False, "button must be left, right or middle")
        if not 1 <= clicks <= 3:
            return ActionResult(False, "clicks must be between 1 and 3")
        if not user32.SetCursorPos(x, y):
            return ActionResult(False, "Windows rejected cursor positioning")
        down, up = _MOUSE[button]
        for _ in range(clicks):
            user32.mouse_event(down, 0, 0, 0, 0)
            user32.mouse_event(up, 0, 0, 0, 0)
            if clicks > 1:
                time.sleep(0.05)
        return ActionResult(True, "desktop click sent", {"x": x, "y": y, "button": button, "clicks": clicks})

    def computer_scroll(self, payload: dict[str, Any]) -> ActionResult:
        self._project(payload)
        try:
            user32 = self._user32()
            amount = int(payload.get("amount"))
        except ValueError as error:
            return ActionResult(False, str(error))
        except (TypeError, ValueError):
            return ActionResult(False, "amount must be an integer")
        horizontal = bool(payload.get("horizontal", False))
        if amount == 0 or abs(amount) > 100:
            return ActionResult(False, "amount must be between -100 and 100 and non-zero")
        flag = _HWHEEL if horizontal else _WHEEL
        user32.mouse_event(flag, 0, 0, int(amount * 120), 0)
        return ActionResult(True, "desktop scroll sent", {"amount": amount, "horizontal": horizontal})

    @staticmethod
    def _send_unicode(text: str) -> None:
        user32 = ctypes.windll.user32
        units = text.encode("utf-16-le")
        for index in range(0, len(units), 2):
            scan = int.from_bytes(units[index:index + 2], "little")
            down = _INPUT(type=_INPUT_KEYBOARD, ki=_KEYBDINPUT(0, scan, _KEYEVENTF_UNICODE, 0, None))
            up = _INPUT(type=_INPUT_KEYBOARD, ki=_KEYBDINPUT(0, scan, _KEYEVENTF_UNICODE | _KEYEVENTF_KEYUP, 0, None))
            if user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(_INPUT)) != 1:
                raise OSError("Windows rejected unicode key down")
            if user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(_INPUT)) != 1:
                raise OSError("Windows rejected unicode key up")

    def computer_type(self, payload: dict[str, Any]) -> ActionResult:
        self._project(payload)
        try:
            self._windows_only()
        except ValueError as error:
            return ActionResult(False, str(error))
        text = payload.get("text")
        if not isinstance(text, str):
            return ActionResult(False, "text must be a string")
        if not text or len(text.encode("utf-8")) > 64 * 1024:
            return ActionResult(False, "text must contain 1..65536 UTF-8 bytes")
        try:
            self._send_unicode(text)
        except OSError as error:
            return ActionResult(False, f"desktop typing failed: {error}")
        return ActionResult(True, "desktop text sent", {"characters": len(text)})

    def computer_hotkey(self, payload: dict[str, Any]) -> ActionResult:
        self._project(payload)
        try:
            user32 = self._user32()
        except ValueError as error:
            return ActionResult(False, str(error))
        keys = payload.get("keys")
        if not isinstance(keys, list) or not 1 <= len(keys) <= 6:
            return ActionResult(False, "keys must contain 1..6 key names")
        normalized = [str(item or "").strip().lower() for item in keys]
        if any(key not in _VK for key in normalized):
            invalid = [key for key in normalized if key not in _VK]
            return ActionResult(False, "unsupported hotkey key(s): " + ", ".join(invalid))
        values = [_VK[key] for key in normalized]
        for vk in values:
            user32.keybd_event(vk, 0, 0, 0)
        for vk in reversed(values):
            user32.keybd_event(vk, 0, _KEYEVENTF_KEYUP, 0)
        return ActionResult(True, "desktop hotkey sent", {"keys": normalized})
