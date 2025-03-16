# WakeSleepManager

A powerful cross-platform tool to manage wake and sleep states of network devices.

## Features

- **Wake devices** remotely using Wake-on-LAN
- **Sleep devices** remotely via SSH
- **Check status** of devices on your network
- **Manage device list** with easy add/edit/remove operations
- **Cross-platform compatibility** for macOS, Linux, and Windows
- **Automatic OS detection** for proper sleep commands

## Installation

```bash
pip install wakesleepmanager
```

## Quick Start

```bash
# Wake up a device
wake mypc

# Put a device to sleep
sleep mypc

# Check status of all devices
wake status

# Add a new device
wake add device
```

## Command Reference

### Primary Commands
- `wake <subcommand>` - Main command for all functionality
- `awake <subcommand>` - Alternative to `wake`, functions identically
- `wsleep <device>` - Direct command to put a device to sleep

### Wake/Awake Subcommands
- `wake up <device>` - Wake up a specific device
- `wake sleep <device>` - Put a specific device to sleep
- `wake status` - Check status of all devices
- `wake list` - List all configured devices
- `wake add device` - Add a new device
- `wake edit` - Edit an existing device

### Examples
```bash
# Wake up a device
wake up mypc
# or
awake up mypc

# Put a device to sleep
wake sleep mypc
# or
awake sleep mypc
# or
wsleep mypc

# Check status of all devices
wake status
# or
awake status
```

## Requirements

- Python 3.6+
- Network connectivity to target devices
- Wake-on-LAN enabled on target devices for wake functionality
- SSH access to target devices for sleep functionality

## Configuration

On first run, the application will create a configuration file in your home directory.

## License

MIT License