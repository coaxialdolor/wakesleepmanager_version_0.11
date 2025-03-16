
"""Device manager for WakeSleepManager."""

import os
import json
import socket
import logging
import platform
import subprocess
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Union
from wakeonlan import send_magic_packet
import paramiko
from ping3 import ping

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SSHConfig:
    """SSH configuration for a device."""
    username: str
    password: Optional[str] = None
    key_path: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class Device:
    """Network device representation."""
    name: str
    ip_address: str
    mac_address: str
    hostname: Optional[str] = None
    ssh_config: Optional[SSHConfig] = None

    def __post_init__(self):
        """Validate device attributes."""
        # Validate MAC address format
        mac = self.mac_address.replace(':', '').replace('-', '').replace('.', '')
        if len(mac) != 12 or not all(c in '0123456789abcdefABCDEF' for c in mac):
            raise ValueError(f"Invalid MAC address format: {self.mac_address}")
        
        # Validate IP address format
        try:
            socket.inet_aton(self.ip_address)
        except socket.error:
            raise ValueError(f"Invalid IP address format: {self.ip_address}")

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        result = asdict(self)
        if self.ssh_config:
            result['ssh_config'] = self.ssh_config.to_dict()
        return result

class DeviceManager:
    """Manage network devices."""
    
    def __init__(self):
        """Initialize the device manager."""
        self.config_dir = os.path.expanduser("~/.config/wakesleepmanager")
        self.devices_file = os.path.join(self.config_dir, "devices.json")
        self._ensure_config_dir()
        self.devices = self._load_devices()

    def _ensure_config_dir(self):
        """Ensure the configuration directory exists."""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)

    def _load_devices(self) -> Dict[str, Device]:
        """Load devices from the configuration file."""
        if not os.path.exists(self.devices_file):
            return {}
        
        try:
            with open(self.devices_file, 'r') as f:
                devices_data = json.load(f)
            
            devices = {}
            for name, data in devices_data.items():
                ssh_config = None
                if 'ssh_config' in data and data['ssh_config']:
                    ssh_config = SSHConfig(**data['ssh_config'])
                
                devices[name] = Device(
                    name=name,
                    ip_address=data['ip_address'],
                    mac_address=data['mac_address'],
                    hostname=data.get('hostname'),
                    ssh_config=ssh_config
                )
            return devices
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading devices: {e}")
            return {}

    def _save_devices(self):
        """Save devices to the configuration file."""
        devices_data = {name: device.to_dict() for name, device in self.devices.items()}
        with open(self.devices_file, 'w') as f:
            json.dump(devices_data, f, indent=2)

    def add_device(self, device: Device):
        """Add a new device."""
        if device.name in self.devices:
            raise ValueError(f"Device with name '{device.name}' already exists")
        
        self.devices[device.name] = device
        self._save_devices()

    def get_device(self, name: str) -> Device:
        """Get a device by name."""
        if name not in self.devices:
            raise KeyError(f"Device '{name}' not found")
        
        return self.devices[name]

    def update_device(self, name: str, device: Device):
        """Update an existing device."""
        if name not in self.devices:
            raise KeyError(f"Device '{name}' not found")
        
        # Preserve SSH config if not provided in the new device
        if not device.ssh_config and self.devices[name].ssh_config:
            device.ssh_config = self.devices[name].ssh_config
        
        self.devices[name] = device
        self._save_devices()

    def remove_device(self, name: str):
        """Remove a device."""
        if name not in self.devices:
            raise KeyError(f"Device '{name}' not found")
        
        del self.devices[name]
        self._save_devices()

    def list_devices(self) -> List[Device]:
        """List all devices."""
        return list(self.devices.values())

    def check_device_status(self, name: str) -> bool:
        """Check if a device is awake."""
        device = self.get_device(name)
        
        # Try to ping the device
        try:
            response_time = ping(device.ip_address, timeout=2)
            return response_time is not None
        except Exception as e:
            logger.debug(f"Ping failed for {name}: {e}")
            return False

    def wake_device(self, name: str):
        """Wake up a device using Wake-on-LAN."""
        device = self.get_device(name)
        
        # Send magic packet
        send_magic_packet(device.mac_address)
        logger.info(f"Sent wake-up signal to device '{name}'")

    def setup_ssh_config(self, name: str, username: str, password: str = None, key_path: str = None):
        """Set up SSH configuration for a device."""
        if name not in self.devices:
            raise KeyError(f"Device '{name}' not found")
        
        if not password and not key_path:
            raise ValueError("Either password or key_path must be provided")
        
        ssh_config = SSHConfig(username=username, password=password, key_path=key_path)
        self.devices[name].ssh_config = ssh_config
        self._save_devices()

    def sleep_device(self, name: str):
        """Put a device to sleep using SSH with OS detection."""
        device = self.get_device(name)

        if not device.ssh_config:
            raise ValueError(f"SSH configuration not set for device '{name}'")

        # Connect to the device via SSH
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            # Connect using either password or key
            if device.ssh_config.password:
                client.connect(
                    device.ip_address,
                    username=device.ssh_config.username,
                    password=device.ssh_config.password,
                    timeout=5
                )
            elif device.ssh_config.key_path:
                key_path = os.path.expanduser(device.ssh_config.key_path)
                key = paramiko.RSAKey.from_private_key_file(key_path)
                client.connect(
                    device.ip_address,
                    username=device.ssh_config.username,
                    pkey=key,
                    timeout=5
                )

            # Detect OS type
            logger.info(f"Detecting OS type for device '{name}'")
            
            # Try to get OS information using various commands
            os_type = None
            
            # Try uname first (works on Linux and macOS)
            _, stdout, _ = client.exec_command('uname -s 2>/dev/null || echo "Unknown"')
            uname_output = stdout.read().decode().strip()
            
            if uname_output == "Darwin":
                os_type = "macOS"
            elif uname_output in ["Linux", "FreeBSD"]:
                os_type = "Linux"
            else:
                # Try Windows-specific command
                _, stdout, _ = client.exec_command('systeminfo | findstr /B /C:"OS Name" 2>NUL || echo "Unknown"')
                win_output = stdout.read().decode().strip()
                if "Windows" in win_output:
                    os_type = "Windows"
            
            logger.info(f"Detected OS type: {os_type or 'Unknown'}")
            
            # Send appropriate sleep command based on OS type
            if os_type == "Windows":
                # For Windows, use rundll32 to trigger sleep mode with proper command escaping
                cmd = 'powershell -Command "Start-Process rundll32.exe -ArgumentList \'powrprof.dll,SetSuspendState 0,1,0\' -Verb RunAs"'
                logger.info(f"Sending Windows sleep command: {cmd}")
                client.exec_command(cmd)
                # Don't wait for response - return immediately
                
            elif os_type == "macOS":
                # For macOS, use nohup to run in background
                cmd = 'nohup pmset sleepnow > /dev/null 2>&1 &'
                logger.info(f"Sending macOS sleep command: {cmd}")
                client.exec_command(cmd)
                # Don't wait for response
                
            elif os_type == "Linux":
                # For Linux, use nohup to run in background
                cmd = 'nohup sudo systemctl suspend > /dev/null 2>&1 &'
                logger.info(f"Sending Linux sleep command: {cmd}")
                client.exec_command(cmd)
                # Don't wait for response
                
            else:
                # Unknown OS, try generic approach with background execution
                logger.warning(f"Unknown OS type for device '{name}', trying generic sleep command")
                client.exec_command('nohup shutdown /h > /dev/null 2>&1 &')
                
            logger.info(f"Device '{name}' sleep command sent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to put device '{name}' to sleep: {str(e)}")
            raise RuntimeError(f"Failed to put device '{name}' to sleep: {str(e)}")
        finally:
            # Always close the client
            client.close()
