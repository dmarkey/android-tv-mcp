# android-tv-mcp

MCP server for controlling Android TV devices. Supports device discovery, pairing, remote control (d-pad, volume, power, media), text input, and app launching.

## Installation

```bash
uv tool install android-tv-mcp
```

Or run directly:

```bash
uvx android-tv-mcp
```

## MCP Client Configuration

### Claude Desktop / Claude Code

Add to your MCP settings:

```json
{
  "mcpServers": {
    "android-tv": {
      "command": "uvx",
      "args": ["android-tv-mcp"]
    }
  }
}
```

## Usage

### First-time setup

1. **Discover devices** on your network: `discover_devices`
2. **Start pairing** with a device: `start_pairing(host="192.168.1.100", device_id="living_room")`
3. **Enter the code** shown on your TV: `finish_pairing(device_id="living_room", code="123456")`

### Controlling your TV

```
connect(device_id="living_room")
send_key(device_id="living_room", key="HOME")
send_key(device_id="living_room", key="DPAD_UP")
send_key(device_id="living_room", key="DPAD_CENTER")
send_key(device_id="living_room", key="VOLUME_UP")
send_text(device_id="living_room", text="search query")
launch_app(device_id="living_room", app_link="https://www.youtube.com")
get_device_status(device_id="living_room")
```

### Available Keys

| Category | Keys |
|----------|------|
| Navigation | `DPAD_UP`, `DPAD_DOWN`, `DPAD_LEFT`, `DPAD_RIGHT`, `DPAD_CENTER` |
| System | `HOME`, `BACK`, `MENU`, `POWER` |
| Volume | `VOLUME_UP`, `VOLUME_DOWN`, `MUTE` |
| Media | `MEDIA_PLAY_PAUSE`, `MEDIA_STOP`, `MEDIA_NEXT`, `MEDIA_PREVIOUS`, `MEDIA_REWIND`, `MEDIA_FAST_FORWARD` |
| Apps | `YOUTUBE` |
| Info | `INFO`, `GUIDE`, `SEARCH` |
| Numbers | `0`-`9` |
| Colors | `PROG_RED`, `PROG_GREEN`, `PROG_YELLOW`, `PROG_BLUE` |
| Channels | `CHANNEL_UP`, `CHANNEL_DOWN` |

### Key Repeat

Use the `repeat` parameter to send a key multiple times (1-50), useful for volume adjustments:

```
send_key(device_id="living_room", key="VOLUME_DOWN", repeat=10)
```

### Long Press

Use `direction` parameter: `START_LONG` to begin holding, `END_LONG` to release.

## Tools

| Tool | Description |
|------|-------------|
| `discover_devices` | Scan network for Android TV devices |
| `list_devices` | List saved devices |
| `start_pairing` | Begin pairing (TV shows a code) |
| `finish_pairing` | Complete pairing with the code |
| `connect` | Connect to a paired device |
| `disconnect` | Disconnect from a device |
| `send_key` | Send remote control key |
| `send_text` | Type text on the TV |
| `launch_app` | Launch app via deep link |
| `get_device_status` | Get power, app, volume status |
| `remove_device` | Remove a saved device |

## License

MIT
