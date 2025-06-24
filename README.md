# CheckPause

A Windows client application that monitors and manages the Do Not Disturb (DND) status of MicroSIP, a VoIP softphone application.

## Features

- Real-time monitoring of MicroSIP's DND status
- Automatic server discovery and connection
- System tray notifications
- Automatic updates from GitHub releases
- Windows system integration

## Requirements

- Python 3.9 or higher
- Windows operating system
- MicroSIP installed
- Required Python packages (see `pyproject.toml`)

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. If you want to enable GitHub release updates:
   - Create a `github_token.txt` file
   - Add your GitHub personal access token to the file

## Building

The project includes several build scripts:

- `build_client.py` - Basic build script
- `build_release.py` - Builds and creates GitHub releases
- `build.spec` - PyInstaller specification file

To build the executable:

```bash
python build_client.py
```

## Development

The project uses:
- Flet for UI components
- PyInstaller for creating standalone executables
- win32api for Windows integration
- requests for API communication

## Configuration

The client can be configured through various constants in `client.py`:

- `DISCOVERY_PORT`: Port for server discovery (default: 12346)
- `SERVER_PORT`: Main communication port (default: 12345)
- `UPDATE_CHECK_INTERVAL`: Time between update checks (default: 3600 seconds)
- `GITHUB_REPO`: Repository for updates

## License

[Add your license information here]