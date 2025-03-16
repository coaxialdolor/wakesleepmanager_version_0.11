"""Network scanner for WakeSleepManager."""

import os
import re
import subprocess
from typing import List, Dict

def scan_network() -> List[Dict[str, str]]:
    """Scan the network for devices."""
    devices = []
    try:
        # Use arp-scan or nmap to discover devices
        result = subprocess.run(['arp-scan', '--localnet'], capture_output=True, text=True)
        if result.returncode == 0:
            # Parse arp-scan output
            for line in result.stdout.splitlines():
                match = re.match(r'^([\d.]+)\s+([\w:]+)\s+(.*)$', line)
                if match:
                    ip_address, mac_address, _ = match.groups()
                    devices.append({
                        'ip_address': ip_address,
                        'mac_address': mac_address
                    })
    except FileNotFoundError:
        # Fallback to nmap if arp-scan is not available
        try:
            result = subprocess.run(['nmap', '-sn', '192.168.1.0/24'], capture_output=True, text=True)
            if result.returncode == 0:
                # Parse nmap output
                for line in result.stdout.splitlines():
                    match = re.match(r'^Nmap scan report for ([\w.-]+) \(([\d.]+)\)$', line)
                    if match:
                        hostname, ip_address = match.groups()
                        devices.append({
                            'ip_address': ip_address,
                            'mac_address': 'Unknown',
                            'hostname': hostname
                        })
        except FileNotFoundError:
            pass
    return devices

def get_device_name(ip_address: str) -> str:
    """Get the hostname of a device by its IP address."""
    try:
        result = subprocess.run(['nslookup', ip_address], capture_output=True, text=True)
        if result.returncode == 0:
            # Parse nslookup output
            for line in result.stdout.splitlines():
                match = re.match(r'^Name:\s+([\w.-]+)$', line)
                if match:
                    return match.group(1)
    except FileNotFoundError:
        pass
    return ''
