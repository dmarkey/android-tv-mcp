"""Zeroconf device discovery for Android TV."""

import asyncio
import logging

from zeroconf import ServiceStateChange, Zeroconf
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf

_LOGGER = logging.getLogger(__name__)


async def discover_devices(timeout: float = 5.0) -> list[dict]:
    """Discover Android TV devices on the network via Zeroconf.

    Returns a list of dicts with keys: name, host, port.
    """
    devices: list[dict] = []

    def on_service_state_change(
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        if state_change is ServiceStateChange.Added:
            asyncio.ensure_future(get_service_info(zeroconf, service_type, name))

    async def get_service_info(
        zeroconf: Zeroconf, service_type: str, name: str
    ) -> None:
        try:
            info = AsyncServiceInfo(service_type, name)
            await info.async_request(zeroconf, 3000)
            if info and info.parsed_scoped_addresses():
                host = info.parsed_scoped_addresses()[0]
                port = info.port or 6467
                device_name = name.split(".")[0]
                devices.append(
                    {"name": device_name, "host": host, "port": port}
                )
        except Exception as e:
            _LOGGER.debug(f"Error getting service info for {name}: {e}")

    zc = AsyncZeroconf()
    browser = AsyncServiceBrowser(
        zc.zeroconf,
        ["_androidtvremote2._tcp.local."],
        handlers=[on_service_state_change],
    )

    await asyncio.sleep(timeout)

    await browser.async_cancel()
    await zc.async_close()

    return devices
