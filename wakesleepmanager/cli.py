"""Command-line interface for WakeSleepManager."""

import os
import sys
import click
from rich.console import Console
from rich.table import Table
from .device_manager import Device, DeviceManager

console = Console()
device_manager = DeviceManager()

@click.group()
def cli():
    """WakeSleepManager - Control network devices remotely."""
    pass

# Function that handles waking up devices, used by multiple commands
def _wake_device_handler(name: str = None):
    """Wake up one or more devices."""
    if name:
        try:
            device = device_manager.get_device(name)
            if device_manager.check_device_status(name):
                console.print(f"[yellow]Device '{name}' is already awake[/yellow]")
                return
            device_manager.wake_device(name)
            console.print(f"[green]Sent wake-up signal to device '{name}'[/green]")
        except KeyError:
            console.print(f"[red]Device '{name}' not found[/red]")
    else:
        devices = device_manager.list_devices()
        if not devices:
            console.print("[yellow]No devices configured. Use 'wakemanager add' to add a device.[/yellow]")
            return

        table = Table(show_header=True)
        table.add_column("#")
        table.add_column("Name")
        table.add_column("Status")

        for i, device in enumerate(devices, 1):
            status = "Awake" if device_manager.check_device_status(device.name) else "Sleeping"
            table.add_row(str(i), device.name, status)

        console.print(table)
        choice = click.prompt("Enter the number of the device to wake (or 'all' for all devices)")

        if choice.lower() == 'all':
            for device in devices:
                if not device_manager.check_device_status(device.name):
                    device_manager.wake_device(device.name)
                    console.print(f"[green]Sent wake-up signal to device '{device.name}'[/green]")
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(devices):
                    device = devices[idx]
                    if device_manager.check_device_status(device.name):
                        console.print(f"[yellow]Device '{device.name}' is already awake[/yellow]")
                    else:
                        device_manager.wake_device(device.name)
                        console.print(f"[green]Sent wake-up signal to device '{device.name}'[/green]")
                else:
                    console.print("[red]Invalid device number[/red]")
            except ValueError:
                console.print("[red]Invalid input. Please enter a number or 'all'[/red]")

@cli.command(name="up")
@click.argument('name', required=False)
def wake_up(name: str = None):
    """Wake up one or more devices."""
    _wake_device_handler(name)

@cli.command()
@click.argument('name', required=False)
def check(name: str = None):
    """Check the status of one or more devices."""
    if name:
        try:
            device = device_manager.get_device(name)
            status = "Awake" if device_manager.check_device_status(name) else "Sleeping"
            console.print(f"Device '{name}' is {status}")
        except KeyError:
            console.print(f"[red]Device '{name}' not found[/red]")
    else:
        devices = device_manager.list_devices()
        if not devices:
            console.print("[yellow]No devices configured. Use 'wakemanager add' to add a device.[/yellow]")
            return

        table = Table(show_header=True)
        table.add_column("Name", min_width=15)
        table.add_column("IP Address", min_width=15)
        table.add_column("MAC Address", min_width=17)
        table.add_column("Hostname", min_width=20)
        table.add_column("Status", min_width=10)

        for device in devices:
            status = "Awake" if device_manager.check_device_status(device.name) else "Sleeping"
            table.add_row(device.name, device.ip_address, device.mac_address, device.hostname or "N/A", status)

        console.print(table)

@cli.command()
def list():
    """List all configured devices."""
    devices = device_manager.list_devices()
    if not devices:
        console.print("[yellow]No devices configured. Use 'wakemanager add' to add a device.[/yellow]")
        return

    table = Table(show_header=True)
    table.add_column("Name", min_width=15)
    table.add_column("IP Address", min_width=15)
    table.add_column("MAC Address", min_width=17)
    table.add_column("Hostname", min_width=20)

    for device in devices:
        table.add_row(
            device.name,
            device.ip_address,
            device.mac_address,
            device.hostname or "N/A"
        )

    console.print(table)

@cli.command()
@click.argument('name', required=False)
def add(name: str = None):
    """Add a new device."""
    from .network_scanner import scan_network, get_device_name
    
    if not name:
        name = click.prompt("Enter device name")
    
    # Ask user for preferred input method
    input_method = click.prompt(
        "Choose input method",
        type=click.Choice(['scan', 'manual']),
        default='scan'
    )
    
    if input_method == 'scan':
        # Scan for available devices
        console.print("[yellow]Scanning network for devices...[/yellow]")
        devices = scan_network()
        
        if devices:
            # Create a table of discovered devices
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim")
            table.add_column("IP Address")
            table.add_column("MAC Address")
            table.add_column("Hostname")
            
            for i, device in enumerate(devices, 1):
                hostname = get_device_name(device['ip_address']) or 'Unknown'
                table.add_row(
                    str(i),
                    device['ip_address'],
                    device['mac_address'],
                    hostname
                )
            
            console.print(table)
            choice = click.prompt("Enter the number of the device to add", type=str)
            
            if choice.isdigit() and 1 <= int(choice) <= len(devices):
                selected_device = devices[int(choice) - 1]
                ip_address = selected_device['ip_address']
                mac_address = selected_device['mac_address']
                hostname = get_device_name(ip_address) or ''
            else:
                console.print("[red]Invalid choice. Switching to manual input.[/red]")
                input_method = 'manual'
        else:
            console.print("[yellow]No devices found. Switching to manual input.[/yellow]")
            input_method = 'manual'
    
    if input_method == 'manual':
        ip_address = click.prompt("Enter IP address")
        mac_address = click.prompt("Enter MAC address")
        hostname = click.prompt("Enter hostname (optional)", default="")

    try:
        device = Device(
            name=name,
            ip_address=ip_address,
            mac_address=mac_address,
            hostname=hostname or None
        )
        device_manager.add_device(device)
        console.print(f"[green]Device '{name}' added successfully[/green]")
        
        if click.confirm("Do you want to setup SSH to be able to use the sleep command?"):
            setup_ssh_config(name)
    except ValueError as e:
        console.print(f"[red]Error: {str(e)}[/red]")

@cli.command()
@click.argument('name')
def remove(name: str):
    """Remove a device."""
    try:
        if click.confirm(f"Are you sure you want to remove device '{name}'?"):
            device_manager.remove_device(name)
            console.print(f"[green]Device '{name}' removed successfully[/green]")
    except KeyError:
        console.print(f"[red]Device '{name}' not found[/red]")

@cli.command(name="sleep")
@click.argument('name', required=False)
def sleep_device(name: str = None):
    """Put one or more devices to sleep."""
    if name:
        try:
            device = device_manager.get_device(name)
            if not device_manager.check_device_status(name):
                console.print(f"[yellow]Device '{name}' is already sleeping[/yellow]")
                return
            try:
                device_manager.sleep_device(name)
                console.print(f"[green]Sent sleep signal to device '{name}'[/green]")
            except (ValueError, RuntimeError) as e:
                console.print(f"[red]Error: {str(e)}[/red]")
        except KeyError:
            console.print(f"[red]Device '{name}' not found[/red]")
    else:
        devices = device_manager.list_devices()
        if not devices:
            console.print("[yellow]No devices configured. Use 'wakemanager add' to add a device.[/yellow]")
            return

        table = Table(show_header=True)
        table.add_column("#")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("SSH Config")

        for i, device in enumerate(devices, 1):
            status = "Awake" if device_manager.check_device_status(device.name) else "Sleeping"
            ssh_status = "Configured" if device.ssh_config else "Not configured"
            table.add_row(str(i), device.name, status, ssh_status)

        console.print(table)
        choice = click.prompt("Enter the number of the device to sleep (or 'all' for all devices)")

        if choice.lower() == 'all':
            for device in devices:
                if device_manager.check_device_status(device.name):
                    try:
                        device_manager.sleep_device(device.name)
                        console.print(f"[green]Sent sleep signal to device '{device.name}'[/green]")
                    except (ValueError, RuntimeError) as e:
                        console.print(f"[red]Error with device '{device.name}': {str(e)}[/red]")
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(devices):
                    device = devices[idx]
                    if not device_manager.check_device_status(device.name):
                        console.print(f"[yellow]Device '{device.name}' is already sleeping[/yellow]")
                    else:
                        try:
                            device_manager.sleep_device(device.name)
                            console.print(f"[green]Sent sleep signal to device '{device.name}'[/green]")
                        except (ValueError, RuntimeError) as e:
                            console.print(f"[red]Error: {str(e)}[/red]")
                else:
                    console.print("[red]Invalid device number[/red]")
            except ValueError:
                console.print("[red]Invalid input. Please enter a number or 'all'[/red]")

def setup_ssh_config(name: str):
    """Helper function to set up SSH configuration for a device."""
    try:
        device = device_manager.get_device(name)
        username = click.prompt("Enter SSH username")
        auth_type = click.prompt(
            "Choose authentication type",
            type=click.Choice(['password', 'key']),
            default='password'
        )

        if auth_type == 'password':
            password = click.prompt("Enter SSH password", hide_input=True)
            device_manager.setup_ssh_config(name, username, password=password)
        else:
            key_path = click.prompt("Enter path to SSH private key file")
            key_path = os.path.expanduser(key_path)
            if not os.path.exists(key_path):
                console.print(f"[red]SSH key file not found: {key_path}[/red]")
                return
            device_manager.setup_ssh_config(name, username, key_path=key_path)

        console.print(f"[green]SSH configuration for device '{name}' updated successfully[/green]")
    except KeyError:
        console.print(f"[red]Device '{name}' not found[/red]")
    except ValueError as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def wake_cli():
    """Entry point for the wake command.
    
    - Running 'wake' alone shows an interactive list of devices
    - Running 'wake devicename' wakes up the specified device
    """
    # If a device name is provided directly
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        device_name = sys.argv[1]
        # Handle direct device name
        try:
            device = device_manager.get_device(device_name)
            if device_manager.check_device_status(device_name):
                console.print(f"[yellow]Device '{device_name}' is already awake[/yellow]")
                return
            device_manager.wake_device(device_name)
            console.print(f"[green]Sent wake-up signal to device '{device_name}'[/green]")
        except KeyError:
            console.print(f"[red]Device '{device_name}' not found[/red]")
        return
    
    # Otherwise, show interactive device selection
    _wake_device_handler()

def sleep_cli():
    """Entry point for wsleep command."""
    # If a device name is provided directly
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        device_name = sys.argv[1]
        # Handle direct device name
        try:
            device = device_manager.get_device(device_name)
            if not device_manager.check_device_status(device_name):
                console.print(f"[yellow]Device '{device_name}' is already sleeping[/yellow]")
                return
            try:
                device_manager.sleep_device(device_name)
                console.print(f"[green]Sent sleep signal to device '{device_name}'[/green]")
            except (ValueError, RuntimeError) as e:
                console.print(f"[red]Error: {str(e)}[/red]")
        except KeyError:
            console.print(f"[red]Device '{device_name}' not found[/red]")
        return
    
    # Otherwise, show interactive device selection
    sleep_device()

if __name__ == '__main__':
    cli()
