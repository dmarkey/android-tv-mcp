"""MCP server for Android TV remote control."""

import asyncio
import re

from mcp.server.fastmcp import FastMCP

from .config import load_devices, find_device, delete_device
from .connection import ConnectionManager
from .discovery import discover_devices as _discover_devices

mcp = FastMCP("android-tv-mcp")
manager = ConnectionManager()


@mcp.tool()
async def discover_devices(timeout: float = 5.0) -> str:
    """Scan the local network for Android TV devices using Zeroconf/mDNS.

    Args:
        timeout: How long to scan in seconds (default 5).

    Returns:
        List of discovered devices with name, host, and port.
    """
    devices = await _discover_devices(timeout)
    if not devices:
        return "No Android TV devices found on the network."
    lines = ["Found devices:"]
    for d in devices:
        lines.append(f"  - {d['name']} at {d['host']}:{d['port']}")
    return "\n".join(lines)


@mcp.tool()
async def list_devices() -> str:
    """List all saved/configured Android TV devices."""
    devices = load_devices()
    if not devices:
        return "No saved devices. Use discover_devices and start_pairing to add one."
    lines = ["Saved devices:"]
    for d in devices:
        paired = "paired" if d.get("paired") else "not paired"
        connected = (
            "connected" if d["id"] in manager._connections else "disconnected"
        )
        lines.append(f"  - {d['id']}: {d['name']} ({d['host']}) [{paired}, {connected}]")
    return "\n".join(lines)


@mcp.tool()
async def start_pairing(host: str, device_id: str) -> str:
    """Begin pairing with an Android TV device. The TV will display a 6-digit code.

    Args:
        host: IP address of the Android TV (from discover_devices).
        device_id: A short identifier for this device (e.g. "living_room"). Letters, numbers, underscores only.
    """
    if not re.match(r"^[a-zA-Z0-9_]+$", device_id):
        return "Error: device_id must contain only letters, numbers, and underscores."
    try:
        result = await manager.start_pairing(device_id, host)
        return result + " Please provide the code using finish_pairing."
    except Exception as e:
        return f"Error starting pairing: {e}"


@mcp.tool()
async def finish_pairing(device_id: str, code: str) -> str:
    """Complete pairing by submitting the 6-digit code displayed on the TV.

    Args:
        device_id: The device identifier used in start_pairing.
        code: The 6-digit pairing code shown on the TV screen.
    """
    try:
        return await manager.finish_pairing(device_id, code)
    except Exception as e:
        return f"Error finishing pairing: {e}"


@mcp.tool()
async def connect(device_id: str) -> str:
    """Connect to a previously paired Android TV device.

    Args:
        device_id: The device identifier.
    """
    try:
        info = await manager.connect(device_id)
        if info:
            return f"Connected to {device_id}. Device info: {info}"
        return f"Connected to {device_id}."
    except Exception as e:
        return f"Error connecting: {e}"


@mcp.tool()
async def disconnect(device_id: str) -> str:
    """Disconnect from an Android TV device.

    Args:
        device_id: The device identifier.
    """
    await manager.disconnect(device_id)
    return f"Disconnected from {device_id}."


@mcp.tool()
async def send_key(device_id: str, key: str, direction: str = "SHORT", repeat: int = 1) -> str:
    """Send a remote control key command to an Android TV.

    Args:
        device_id: The device identifier.
        key: The key to send. Common keys:
            Navigation: DPAD_UP, DPAD_DOWN, DPAD_LEFT, DPAD_RIGHT, DPAD_CENTER
            System: HOME, BACK, MENU, POWER
            Volume: VOLUME_UP, VOLUME_DOWN, MUTE
            Media: MEDIA_PLAY_PAUSE, MEDIA_STOP, MEDIA_NEXT, MEDIA_PREVIOUS, MEDIA_REWIND, MEDIA_FAST_FORWARD, MEDIA_RECORD
            Apps: YOUTUBE
            Info: INFO, GUIDE, SEARCH
            Numbers: 0-9
            Colors: PROG_RED, PROG_GREEN, PROG_YELLOW, PROG_BLUE
            Channels: CHANNEL_UP, CHANNEL_DOWN
            Input: DEL
        direction: SHORT (default), START_LONG (begin hold), or END_LONG (release hold).
        repeat: Number of times to send the key (default 1). Useful for volume adjustments.
    """
    try:
        repeat = max(1, min(repeat, 50))
        for i in range(repeat):
            manager.send_key(device_id, key, direction)
            if i < repeat - 1:
                await asyncio.sleep(0.1)
        if repeat > 1:
            return f"Sent {key} ({direction}) x{repeat} to {device_id}."
        return f"Sent {key} ({direction}) to {device_id}."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def send_text(device_id: str, text: str) -> str:
    """Type text on the Android TV (for search fields, text inputs, etc.).

    Args:
        device_id: The device identifier.
        text: The text to type.
    """
    try:
        manager.send_text(device_id, text)
        return f"Sent text to {device_id}."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def launch_app(device_id: str, app_link: str) -> str:
    """Launch an app on the Android TV using a deep link URL.

    Args:
        device_id: The device identifier.
        app_link: The app deep link (e.g. "https://www.youtube.com" for YouTube).
    """
    try:
        manager.launch_app(device_id, app_link)
        return f"Launched {app_link} on {device_id}."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def get_device_status(device_id: str) -> str:
    """Get the current status of a connected Android TV device.

    Args:
        device_id: The device identifier.

    Returns:
        Current power state, active app, volume level, and availability.
    """
    try:
        state = manager.get_state(device_id)
        lines = [
            f"Status for {device_id}:",
            f"  Power: {'on' if state['is_on'] else 'off/standby'}",
            f"  App: {state['current_app'] or 'unknown'}",
            f"  Volume: {state['volume_level']}/{state['volume_max']} {'(muted)' if state['is_muted'] else ''}",
            f"  Available: {state['is_available']}",
        ]
        if state["needs_pairing"]:
            lines.append("  WARNING: Authentication expired, needs re-pairing.")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def remove_device(device_id: str) -> str:
    """Remove a saved device from the configuration.

    Args:
        device_id: The device identifier to remove.
    """
    if device_id in manager._connections:
        await manager.disconnect(device_id)
    if delete_device(device_id):
        return f"Removed device {device_id}."
    return f"Device {device_id} not found."


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
