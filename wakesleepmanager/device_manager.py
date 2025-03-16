"""Device manager for WakeSleepManager."""

import os
import json
import socket
import platform
import subprocess
import logging
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Union
from wakeonlan import send_magic_packet
import paramiko
from ping3 import ping

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        logger.info(f"Device '{device.name}' added successfully")

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
        logger.info(f"Device '{name}' updated successfully")

    def remove_device(self, name: str):
        """Remove a device."""
        if name not in self.devices:
            raise KeyError(f"Device '{name}' not found")

        del self.devices[name]
        self._save_devices()
        logger.info(f"Device '{name}' removed successfully")

    def list_devices(self) -> List[Device]:
        """List all devices."""
        return list(self.devices.values())

    def check_device_status(self, name: str) -> bool:
        """Check if a device is truly awake with high accuracy."""
        device = self.get_device(name)
        
        # Fast port check - most reliable indicator of a truly awake device
        common_ports = [22, 3389, 445, 80]  # SSH, RDP, SMB, HTTP
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.3)  # Very short timeout for speed
                result = sock.connect_ex((device.ip_address, port))
                sock.close()
                if result == 0:  # Port is open
                    return True
            except Exception:
                pass
        
        # Single quick ping as fallback
        try:
            response = ping(device.ip_address, timeout=0.5, size=56)
            if response is not None:
                # Additional verification to prevent false positives
                # Try a second ping with different parameters
                second_response = ping(device.ip_address, timeout=0.5, size=32)
                if second_response is not None:
                    return True
        except Exception:
            pass
        
        return False

    def check_all_devices_status(self, devices=None):
        """Check all devices in parallel for maximum speed."""
        import concurrent.futures
        
        if devices is None:
            devices = self.list_devices()
        
        results = {}
        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(devices)) as executor:
            future_to_device = {
                executor.submit(self.check_device_status, device.name): device.name
                for device in devices
            }
            
            for future in concurrent.futures.as_completed(future_to_device):
                device_name = future_to_device[future]
                try:
                    results[device_name] = future.result()
                except Exception:
                    results[device_name] = False
        
        return results

    def wake_device(self, name: str):
        """Wake up a device using Wake-on-LAN."""
        device = self.get_device(name)

        # Send magic packet
        send_magic_packet(device.mac_address)
        logger.info(f"Wake-up signal sent to device '{name}'")

    def setup_ssh_config(self, name: str, username: str, password: str = None, key_path: str = None):
        """Set up SSH configuration for a device."""
        if name not in self.devices:
            raise KeyError(f"Device '{name}' not found")

        if not password and not key_path:
            raise ValueError("Either password or key_path must be provided")

        ssh_config = SSHConfig(username=username, password=password, key_path=key_path)
        self.devices[name].ssh_config = ssh_config
        self._save_devices()
        logger.info(f"SSH configuration for device '{name}' updated successfully")

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
                # Windows sleep commands with fallbacks
                commands = [
                    'shutdown /h',  # Hibernate
                    'rundll32.exe powrprof.dll,SetSuspendState 0,1,0',  # Sleep
                    'powercfg -hibernate off && powercfg -hibernate on && shutdown /h'  # Reset hibernate and try again
                ]
                
                for cmd in commands:
                    logger.info(f"Trying Windows sleep command: {cmd}")
                    _, stdout, stderr = client.exec_command(f'{cmd} 2>&1')
                    output = stdout.read().decode().strip()
                    error = stderr.read().decode().strip()
                    
                    if not error:
                        logger.info(f"Windows sleep command succeeded: {cmd}")
                        break
                    logger.info(f"Command failed, trying next. Error: {error}")
                    
            elif os_type == "macOS":
                # macOS sleep command
                client.exec_command('pmset sleepnow')
                logger.info("Sent macOS sleep command: pmset sleepnow")
                
            elif os_type == "Linux":
                # Linux sleep commands with fallbacks
                commands = [
                    'systemctl suspend',  # Modern systemd systems
                    'pm-suspend',         # Older systems
                    'echo mem > /sys/power/state'  # Direct kernel interface
                ]
                
                for cmd in commands:
                    logger.info(f"Trying Linux sleep command: {cmd}")
                    _, stdout, stderr = client.exec_command(f'sudo {cmd} 2>&1 || {cmd} 2>&1')
                    output = stdout.read().decode().strip()
                    error = stderr.read().decode().strip()
                    
                    if not error:
                        logger.info(f"Linux sleep command succeeded: {cmd}")
                        break
                    logger.info(f"Command failed, trying next. Error: {error}")
            else:
                # Unknown OS, try generic approaches
                logger.warning(f"Unknown OS type for device '{name}', trying generic sleep commands")
                commands = [
                    'systemctl suspend',  # Linux
                    'pm-suspend',         # Linux
                    'pmset sleepnow',     # macOS
                    'shutdown /h',        # Windows
                    'rundll32.exe powrprof.dll,SetSuspendState 0,1,0'  # Windows
                ]
                
                for cmd in commands:
                    client.exec_command(f'{cmd} 2>/dev/null')
                
            logger.info(f"Device '{name}' sleep commands sent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to put device '{name}' to sleep: {str(e)}")
            raise RuntimeError(f"Failed to put device '{name}' to sleep: {str(e)}")
        finally:
            client.close()
