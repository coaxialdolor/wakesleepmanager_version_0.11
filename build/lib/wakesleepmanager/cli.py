"""Command-line interface for WakeSleepManager."""

import os
import click
import logging
from rich.console import Console
from rich.table import Table
from .device_manager import Device, DeviceManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

console = Console()
device_manager = DeviceManager()

@click.group()
def cli():
    """WakeSleepManager - Manage network devices' wake and sleep states."""
    pass

# Wake commands
@cli.command(name="wake")
@click.argument('name', required=False)
def wake(name: str = None):
    """Wake up one or more devices.

    If NAME is provided, wake up that specific device.
    Otherwise, show a list of devices to choose from.
    """
    if name:
        try:
            device = device_manager.get_device(name)
            if device_manager.check_device_status(name):
                logger.info(f"Device '{name}' is already awake")
                console.print(f"[yellow]Device '{name}' is already awake[/yellow]")
                return
            device_manager.wake_device(name)
            logger.info(f"Sent wake-up signal to device '{name}'")
            console.print(f"[green]Sent wake-up signal to device '{name}'[/green]")
        except KeyError:
            logger.error(f"Device '{name}' not found")
            console.print(f"[red]Device '{name}' not found[/red]")
    else:
        devices = device_manager.list_devices()
        if not devices:
            logger.warning("No devices configured. Use 'add device' to add a device.")
            console.print("[yellow]No devices configured. Use 'add device' to add a device.[/yellow]")
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
                    logger.info(f"Sent wake-up signal to device '{device.name}'")
                    console.print(f"[green]Sent wake-up signal to device '{device.name}'[/green]")
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(devices):
                    device = devices[idx]
                    if device_manager.check_device_status(device.name):
                        logger.info(f"Device '{device.name}' is already awake")
                        console.print(f"[yellow]Device '{device.name}' is already awake[/yellow]")
                    else:
                        device_manager.wake_device(device.name)
                        logger.info(f"Sent wake-up signal to device '{device.name}'")
                        console.print(f"[green]Sent wake-up signal to device '{device.name}'[/green]")
                else:
                    logger.error("Invalid device number")
                    console.print("[red]Invalid device number[/red]")
            except ValueError:
                logger.error("Invalid input. Please enter a number or 'all'")
                console.print("[red]Invalid input. Please enter a number or 'all'[/red]")

@cli.command(name="status")
def check_status():
    """Check the status of all devices."""
    devices = device_manager.list_devices()
    if not devices:
        logger.warning("No devices configured. Use 'add device' to add a device.")
        console.print("[yellow]No devices configured. Use 'add device' to add a device.[/yellow]")
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

@cli.command(name="check")
@click.argument('name')
def check_device(name: str):
    """Check the status of a specific device."""
    try:
        device = device_manager.get_device(name)
        status = "Awake" if device_manager.check_device_status(name) else "Sleeping"
        logger.info(f"Device '{name}' is {status}")
        console.print(f"Device '{name}' is {status}")
    except KeyError:
        logger.error(f"Device '{name}' not found")
        console.print(f"[red]Device '{name}' not found[/red]")

@cli.command(name="list")
def list_devices():
    """List all configured devices."""
    devices = device_manager.list_devices()
    if not devices:
        logger.warning("No devices configured. Use 'add device' to add a device.")
        console.print("[yellow]No devices configured. Use 'add device' to add a device.[/yellow]")
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

@cli.command(name="edit")
@click.argument('name', required=False)
def edit_device(name: str = None):
    """Edit an existing device configuration."""
    from .network_scanner import scan_network, get_device_name

    devices = device_manager.list_devices()
    if not devices:
        logger.warning("No devices configured. Use 'add device' to add a device.")
        console.print("[yellow]No devices configured. Use 'add device' to add a device.[/yellow]")
        return

    if name:
        try:
            device = device_manager.get_device(name)
        except KeyError:
            logger.error(f"Device '{name}' not found")
            console.print(f"[red]Device '{name}' not found[/red]")
            return

        # Edit the specified device
        edit_specific_device(name)
    else:
        # Show list of devices to edit
        table = Table(show_header=True)
        table.add_column("#")
        table.add_column("Name")
        table.add_column("IP Address")
        table.add_column("MAC Address")
        table.add_column("Hostname")

        for i, device in enumerate(devices, 1):
            table.add_row(
                str(i),
                device.name,
                device.ip_address,
                device.mac_address,
                device.hostname or "N/A"
            )

        console.print(table)
        choice = click.prompt("Enter the number of the device to edit", type=str)

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(devices):
                edit_specific_device(devices[idx].name)
            else:
                logger.error("Invalid device number")
                console.print("[red]Invalid device number[/red]")
        except ValueError:
            logger.error("Invalid input. Please enter a number")
            console.print("[red]Invalid input. Please enter a number[/red]")

def edit_specific_device(name: str):
    """Helper function to edit a specific device."""
    from .network_scanner import scan_network, get_device_name

    device = device_manager.get_device(name)

    # Ask user for preferred input method
    input_method = click.prompt(
        "Choose input method",
        type=click.Choice(['scan', 'manual']),
        default='scan'
    )

    if input_method == 'scan':
        logger.info("Scanning network for devices...")
        console.print("[yellow]Scanning network for devices...[/yellow]")
        available_devices = scan_network()

        if available_devices:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim")
            table.add_column("IP Address")
            table.add_column("MAC Address")
            table.add_column("Hostname")

            for i, dev in enumerate(available_devices, 1):
                hostname = get_device_name(dev['ip_address']) or 'Unknown'
                table.add_row(
                    str(i),
                    dev['ip_address'],
                    dev['mac_address'],
                    hostname
                )

            console.print(table)
            dev_choice = click.prompt("Enter the number of the device to use", type=str)

            if dev_choice.isdigit() and 1 <= int(dev_choice) <= len(available_devices):
                selected_device = available_devices[int(dev_choice) - 1]
                ip_address = selected_device['ip_address']
                mac_address = selected_device['mac_address']
                hostname = get_device_name(ip_address) or ''
            else:
                logger.warning("Invalid choice. Switching to manual input.")
                console.print("[red]Invalid choice. Switching to manual input.[/red]")
                input_method = 'manual'
        else:
            logger.warning("No devices found. Switching to manual input.")
            console.print("[yellow]No devices found. Switching to manual input.[/yellow]")
            input_method = 'manual'

    if input_method == 'manual':
        ip_address = click.prompt("Enter IP address")
        mac_address = click.prompt("Enter MAC address")
        hostname = click.prompt("Enter hostname (optional)", default="")

    try:
        updated_device = Device(
            name=name,
            ip_address=ip_address,
            mac_address=mac_address,
            hostname=hostname or None
        )
        device_manager.update_device(name, updated_device)
        logger.info(f"Device '{name}' updated successfully")
        console.print(f"[green]Device '{name}' updated successfully[/green]")

        if click.confirm("Do you want to setup SSH to be able to use the sleep command?"):
            setup_ssh_config(name)

    except ValueError as e:
        logger.error(f"Error: {str(e)}")
        console.print(f"[red]Error: {str(e)}[/red]")

@cli.command(name="add")
@click.argument('type', type=click.Choice(['device', 'ssh']), required=False)
@click.argument('name', required=False)
def add_item(type: str = None, name: str = None):
    """Add a new device or configure SSH.

    Examples:
        add device       Add a new device
        add ssh <name>   Configure SSH for a device
    """
    if not type:
        type = click.prompt(
            "What would you like to add?",
            type=click.Choice(['device', 'ssh']),
            default='device'
        )

    if type == 'device':
        add_device()
    elif type == 'ssh':
        add_ssh(name)

def add_device():
    """Add a new device."""
    from .network_scanner import scan_network, get_device_name
    name = click.prompt("Enter device name")

    # Ask user for preferred input method
    input_method = click.prompt(
        "Choose input method",
        type=click.Choice(['scan', 'manual']),
        default='scan'
    )

    if input_method == 'scan':
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

def add_ssh(name: str = None):
    """Set up SSH configuration for a device."""
    if name:
        setup_ssh_config(name)
    else:
        devices = device_manager.list_devices()
        if not devices:
            console.print("[yellow]No devices configured. Use 'add device' to add a device.[/yellow]")
            return

        table = Table(show_header=True)
        table.add_column("#")
        table.add_column("Name")
        table.add_column("SSH Config")

        for i, device in enumerate(devices, 1):
            ssh_status = "Configured" if device.ssh_config else "Not configured"
            table.add_row(str(i), device.name, ssh_status)

        console.print(table)
        choice = click.prompt("Enter the number of the device to configure SSH")

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(devices):
                setup_ssh_config(devices[idx].name)
            else:
                console.print("[red]Invalid device number[/red]")
        except ValueError:
            console.print("[red]Invalid input. Please enter a number[/red]")

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

@cli.command(name="remove")
@click.argument('name')
def remove_device(name: str):
    """Remove a device."""
    try:
        if click.confirm(f"Are you sure you want to remove device '{name}'?"):
            device_manager.remove_device(name)
            console.print(f"[green]Device '{name}' removed successfully[/green]")
    except KeyError:
        console.print(f"[red]Device '{name}' not found[/red]")

# Sleep commands
@cli.command(name="sleep")
@click.argument('name', required=False)
def sleep_device(name: str = None):
    """Put one or more devices to sleep.

    If NAME is provided, put that specific device to sleep.
    Otherwise, show a list of devices to choose from.
    """
    if name:
        try:
            device = device_manager.get_device(name)
            if device_manager.check_device_status(name):
                device_manager.sleep_device(name)
                console.print(f"[green]Sent sleep signal to device '{name}'[/green]")
            else:
                console.print(f"[yellow]Device '{name}' is already sleeping[/yellow]")
        except KeyError:
            console.print(f"[red]Device '{name}' not found[/red]")
        except ValueError as e:
            console.print(f"[red]Error: {str(e)}[/red]")
        except RuntimeError as e:
            console.print(f"[red]Error: {str(e)}[/red]")
    else:
        devices = device_manager.list_devices()
        if not devices:
            console.print("[yellow]No devices configured. Use 'add device' to add a device.[/yellow]")
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
                        console.print(f"[red]Error putting '{device.name}' to sleep: {str(e)}[/red]")
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(devices):
                    device = devices[idx]
                    if device_manager.check_device_status(device.name):
                        try:
                            device_manager.sleep_device(device.name)
                            console.print(f"[green]Sent sleep signal to device '{device.name}'[/green]")
                        except (ValueError, RuntimeError) as e:
                            console.print(f"[red]Error: {str(e)}[/red]")
                    else:
                        console.print(f"[yellow]Device '{device.name}' is already sleeping[/yellow]")
                else:
                    console.print("[red]Invalid device number[/red]")
            except ValueError:
                console.print("[red]Invalid input. Please enter a number or 'all'[/red]")
    """Put one or more devices to sleep.

    If NAME is provided, put that specific device to sleep.
    Otherwise, show a list of devices to choose from.
    """
    if name:
        try:
            device = device_manager.get_device(name)
            if not device_manager.check_device_status(name):
                console.print(f"[yellow]Device '{name}' is already sleeping[/yellow]")
                return
            device_manager.sleep_device(name)
            console.print(f"[green]Sent sleep signal to device '{name}'[/green]")
        except KeyError:
            console.print(f"[red]Device '{name}' not found[/red]")
        except ValueError as e:
            console.print(f"[red]Error: {str(e)}[/red]")
        except RuntimeError as e:
            console.print(f"[red]Error: {str(e)}[/red]")
    else:
        devices = device_manager.list_devices()
        if not devices:
            console.print("[yellow]No devices configured. Use 'add device' to add a device.[/yellow]")
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
                        console.print(f"[red]Error putting '{device.name}' to sleep: {str(e)}[/red]")
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

if __name__ == '__main__':
    cli()
