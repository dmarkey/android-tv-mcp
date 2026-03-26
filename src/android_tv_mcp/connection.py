"""Connection manager for Android TV devices."""

import logging
from dataclasses import dataclass, field

from androidtvremote2 import (
    AndroidTVRemote,
    CannotConnect,
    ConnectionClosed,
    InvalidAuth,
)

from .config import get_cert_paths, find_device, upsert_device, load_discovered_apps, save_discovered_apps

_LOGGER = logging.getLogger(__name__)

CLIENT_NAME = "Android TV MCP"


@dataclass
class DeviceState:
    is_on: bool = False
    current_app: str = ""
    volume_level: int = 0
    volume_max: int = 100
    is_muted: bool = False
    is_available: bool = False
    needs_pairing: bool = False
    discovered_apps: set[str] = field(default_factory=set)


class ConnectionManager:
    """Manages connections to Android TV devices."""

    def __init__(self) -> None:
        self._connections: dict[str, AndroidTVRemote] = {}
        self._state: dict[str, DeviceState] = {}
        self._pairing_remotes: dict[str, AndroidTVRemote] = {}

    def _make_callbacks(self, device_id: str) -> None:
        """Register state callbacks on a remote."""
        remote = self._connections[device_id]
        state = self._state[device_id]

        def on_is_on(is_on: bool) -> None:
            state.is_on = is_on

        def on_current_app(app: str) -> None:
            state.current_app = app
            if app and app not in state.discovered_apps:
                state.discovered_apps.add(app)
                save_discovered_apps(device_id, state.discovered_apps)

        def on_volume_info(info: dict) -> None:
            state.volume_level = info.get("level", 0)
            state.volume_max = info.get("max", 100)
            state.is_muted = info.get("muted", False)

        def on_is_available(available: bool) -> None:
            state.is_available = available

        remote.add_is_on_updated_callback(on_is_on)
        remote.add_current_app_updated_callback(on_current_app)
        remote.add_volume_info_updated_callback(on_volume_info)
        remote.add_is_available_updated_callback(on_is_available)

    async def connect(self, device_id: str) -> dict:
        """Connect to a previously paired device. Returns device info."""
        if device_id in self._connections:
            remote = self._connections[device_id]
            return remote.device_info or {}

        device = find_device(device_id)
        if not device:
            raise ValueError(f"Device '{device_id}' not found in config")

        cert_path, key_path = get_cert_paths(device_id)
        remote = AndroidTVRemote(CLIENT_NAME, cert_path, key_path, device["host"])

        self._state[device_id] = DeviceState(discovered_apps=load_discovered_apps(device_id))
        self._connections[device_id] = remote
        self._make_callbacks(device_id)

        try:
            await remote.async_connect()
        except InvalidAuth:
            del self._connections[device_id]
            del self._state[device_id]
            raise ValueError(
                f"Authentication invalid for '{device_id}'. Need to pair again."
            )
        except (CannotConnect, ConnectionClosed) as exc:
            del self._connections[device_id]
            del self._state[device_id]
            raise ValueError(f"Cannot connect to '{device_id}': {exc}")

        def on_invalid_auth() -> None:
            self._state[device_id].needs_pairing = True

        remote.keep_reconnecting(on_invalid_auth)
        return remote.device_info or {}

    async def disconnect(self, device_id: str) -> None:
        """Disconnect from a device."""
        remote = self._connections.pop(device_id, None)
        self._state.pop(device_id, None)
        if remote:
            remote.disconnect()

    async def start_pairing(self, device_id: str, host: str) -> str:
        """Start pairing with a device. Returns device name/mac info."""
        cert_path, key_path = get_cert_paths(device_id)
        remote = AndroidTVRemote(CLIENT_NAME, cert_path, key_path, host)

        await remote.async_generate_cert_if_missing()
        name, mac = await remote.async_get_name_and_mac()
        await remote.async_start_pairing()

        self._pairing_remotes[device_id] = remote

        # Save device config
        upsert_device({
            "id": device_id,
            "name": name,
            "host": host,
            "mac": mac,
            "paired": False,
        })

        return f"Device: {name} (MAC: {mac}). A pairing code is now displayed on your TV."

    async def finish_pairing(self, device_id: str, code: str) -> str:
        """Complete pairing with the code shown on TV."""
        remote = self._pairing_remotes.get(device_id)
        if not remote:
            raise ValueError(
                f"No pairing in progress for '{device_id}'. Call start_pairing first."
            )

        try:
            await remote.async_finish_pairing(code)
        except Exception as exc:
            self._pairing_remotes.pop(device_id, None)
            raise ValueError(f"Pairing failed: {exc}")

        self._pairing_remotes.pop(device_id, None)

        # Update device as paired
        device = find_device(device_id)
        if device:
            device["paired"] = True
            upsert_device(device)

        # Connect after pairing
        self._state[device_id] = DeviceState(discovered_apps=load_discovered_apps(device_id))
        self._connections[device_id] = remote
        self._make_callbacks(device_id)

        try:
            await remote.async_connect()
            def on_invalid_auth() -> None:
                self._state[device_id].needs_pairing = True
            remote.keep_reconnecting(on_invalid_auth)
        except Exception:
            pass  # Connection will be retried on next connect call

        return "Pairing successful. Device is now connected."

    def send_key(self, device_id: str, key: str, direction: str = "SHORT") -> None:
        """Send a key command to a connected device."""
        remote = self._connections.get(device_id)
        if not remote:
            raise ValueError(f"Device '{device_id}' is not connected")
        remote.send_key_command(key, direction)

    def send_text(self, device_id: str, text: str) -> None:
        """Send text input to a connected device."""
        remote = self._connections.get(device_id)
        if not remote:
            raise ValueError(f"Device '{device_id}' is not connected")
        remote.send_text(text)

    def launch_app(self, device_id: str, app: str) -> None:
        """Launch an app by package name or deep link on a connected device."""
        remote = self._connections.get(device_id)
        if not remote:
            raise ValueError(f"Device '{device_id}' is not connected")
        remote.send_launch_app_command(app)

    def get_discovered_apps(self, device_id: str) -> set[str]:
        """Get discovered apps for a device (from cache or persisted)."""
        state = self._state.get(device_id)
        if state:
            return state.discovered_apps
        return load_discovered_apps(device_id)

    def get_state(self, device_id: str) -> dict:
        """Get cached state for a connected device."""
        state = self._state.get(device_id)
        if not state:
            raise ValueError(f"Device '{device_id}' is not connected")
        return {
            "is_on": state.is_on,
            "current_app": state.current_app,
            "volume_level": state.volume_level,
            "volume_max": state.volume_max,
            "is_muted": state.is_muted,
            "is_available": state.is_available,
            "needs_pairing": state.needs_pairing,
        }

    async def disconnect_all(self) -> None:
        """Disconnect all devices."""
        for device_id in list(self._connections):
            await self.disconnect(device_id)
        for remote in self._pairing_remotes.values():
            remote.disconnect()
        self._pairing_remotes.clear()
