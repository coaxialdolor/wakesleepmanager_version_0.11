# WakeSleepManager

A cross-platform tool to manage wake and sleep states of network devices.

## Features

- Wake-on-LAN functionality
- Remote sleep commands via SSH
- Device management (add, remove, list)
- Status checking
- Cross-platform support (Windows, macOS, Linux)

## Installation

Install directly from the current directory:

```bash
pip install .
```

## Usage

### Wake Commands
```bash
# Wake a specific device
wake device-name

# Wake all devices
wake

# Check device status
wake check device-name

# List all devices
wake list

# Add a new device
wake add

# Remove a device
wake remove device-name
```

### Sleep Commands
```bash
# Sleep a specific device
sleep device-name

# Sleep all devices
sleep
```

## Requirements

- Python 3.6 or higher
- Network connectivity to target devices
- Wake-on-LAN enabled on target devices
- SSH access for sleep functionality

## Configuration

On first run, the application will create a configuration file in your home directory.

## License

MIT License
