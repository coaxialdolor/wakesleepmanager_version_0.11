"""Network scanning functionality for device discovery."""

import subprocess
import re
import logging
from typing import List, Dict, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def scan_network() -> List[Dict[str, str]]:
    """Scan the local network for active devices.

    Returns:
        List of dictionaries containing device information with IP and MAC addresses.
    """
    try:
        # Run arp -a to get the ARP table
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("Failed to retrieve ARP table")
            return []

        devices = []
        # Parse the output to extract IP and MAC addresses
        for line in result.stdout.splitlines():
            # Match IP and MAC addresses in the ARP output
            match = re.search(r'\(([0-9.]+)\) at ([0-9a-fA-F:]+)', line)
            if match:
                ip_addr = match.group(1)
                mac_addr = match.group(2)
                if mac_addr != '(incomplete)':
                    devices.append({
                        'ip_address': ip_addr,
                        'mac_address': mac_addr.replace(':', '-')
                    })

        logger.info(f"Found {len(devices)} devices on the network")
        return devices
    except (subprocess.SubprocessError, OSError) as e:
        logger.error(f"Error scanning network: {e}")
        return []

def get_device_name(ip_address: str) -> Optional[str]:
    """Try to get the hostname of a device using its IP address.

    Args:
        ip_address: The IP address to lookup.

    Returns:
        The hostname if found, None otherwise.
    """
    try:
        result = subprocess.run(['host', ip_address], capture_output=True, text=True)
        if result.returncode == 0:
            match = re.search(r'domain name pointer ([\w.-]+)', result.stdout)
            if match:
                return match.group(1)
    except (subprocess.SubprocessError, OSError) as e:
        logger.error(f"Error getting hostname for {ip_address}: {e}")
    return None
