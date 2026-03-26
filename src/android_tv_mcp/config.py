"""Configuration and persistence for android-tv-mcp."""

import json
import os
import platform
from pathlib import Path


def get_config_dir() -> Path:
    """Get the appropriate configuration directory for the current OS."""
    system = platform.system()

    if system == "Windows":
        config_dir = Path(os.environ.get("APPDATA", "")) / "android-tv-mcp"
    elif system == "Darwin":
        config_dir = (
            Path.home() / "Library" / "Application Support" / "android-tv-mcp"
        )
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            config_dir = Path(xdg_config) / "android-tv-mcp"
        else:
            config_dir = Path.home() / ".config" / "android-tv-mcp"

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_certs_dir() -> Path:
    """Get the directory for storing certificates."""
    certs_dir = get_config_dir() / "certs"
    certs_dir.mkdir(parents=True, exist_ok=True)
    return certs_dir


def get_devices_file() -> Path:
    """Get the path to the devices configuration file."""
    return get_config_dir() / "devices.json"


def load_devices() -> list[dict]:
    """Load device configurations from the config file."""
    devices_file = get_devices_file()
    if devices_file.exists():
        try:
            with open(devices_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_devices(devices: list[dict]) -> None:
    """Save device configurations to the config file."""
    devices_file = get_devices_file()
    with open(devices_file, "w", encoding="utf-8") as f:
        json.dump(devices, f, indent=2, ensure_ascii=False)


def get_cert_paths(device_id: str) -> tuple[str, str]:
    """Get cert and key file paths for a device."""
    certs_dir = get_certs_dir()
    cert_path = certs_dir / f"{device_id}_cert.pem"
    key_path = certs_dir / f"{device_id}_key.pem"
    return str(cert_path), str(key_path)


def find_device(device_id: str) -> dict | None:
    """Find a device by ID."""
    for device in load_devices():
        if device["id"] == device_id:
            return device
    return None


def upsert_device(device: dict) -> None:
    """Add or update a device in the config."""
    devices = load_devices()
    for i, d in enumerate(devices):
        if d["id"] == device["id"]:
            devices[i] = device
            save_devices(devices)
            return
    devices.append(device)
    save_devices(devices)


def delete_device(device_id: str) -> bool:
    """Delete a device from the config. Returns True if found."""
    devices = load_devices()
    new_devices = [d for d in devices if d["id"] != device_id]
    if len(new_devices) < len(devices):
        save_devices(new_devices)
        return True
    return False


def _get_apps_file(device_id: str) -> Path:
    """Get the path to the discovered apps file for a device."""
    return get_config_dir() / f"{device_id}_apps.json"


def load_discovered_apps(device_id: str) -> set[str]:
    """Load discovered apps for a device."""
    apps_file = _get_apps_file(device_id)
    if apps_file.exists():
        try:
            with open(apps_file, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError):
            return set()
    return set()


def save_discovered_apps(device_id: str, apps: set[str]) -> None:
    """Save discovered apps for a device."""
    apps_file = _get_apps_file(device_id)
    with open(apps_file, "w", encoding="utf-8") as f:
        json.dump(sorted(apps), f, indent=2, ensure_ascii=False)
