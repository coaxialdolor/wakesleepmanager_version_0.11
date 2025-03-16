"""Command-line interface for WakeSleepManager."""

import os
import sys
import click
from rich.console import Console
from rich.table import Table
from .device_manager import Device, DeviceManager
# Configure console with a wider width
console = Console(width=120)
device_manager = DeviceManager()

from rich.progress import Progress, SpinnerColumn, TextColumn

@click.group()
def cli():
    """WakeSleepManager - Manage network devices' wake and sleep states."""
    pass

# Handle wake command
@cli.command(name="wake")
@click.argument('name', required=False)
def wake_device(name: str = None):
    """Wake up one or more devices."""
    if name:
        try:
            # Add spinner for status check
            with Progress(
                SpinnerColumn(),
                TextColumn("[yellow]Checking device status...[/yellow]"),
                transient=True,
            ) as progress:
                progress.add_task("", total=None)
                is_awake = device_manager.check_device_status(name)
            
            if is_awake:
                console.print(f"[yellow]Device '{name}' is already awake[/yellow]")
                return
                
            # Add spinner for wake operation
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[yellow]Sending wake signal to '{name}'...[/yellow]"),
                transient=True,
            ) as progress:
                progress.add_task("", total=None)
                device_manager.wake_device(name)
                
            console.print(f"[green]Sent wake-up signal to device '{name}'[/green]")
        except KeyError:
            console.print(f"[red]Device '{name}' not found[/red]")
    else:
        devices = device_manager.list_devices()
        if not devices:
            console.print("[yellow]No devices configured. Use 'wake add device' to add a device.[/yellow]")
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
@cli.command(name="status")
def check_status():
    """Check the status of all devices."""
    from rich.progress import Progress, SpinnerColumn, TextColumn
    
    devices = device_manager.list_devices()
    if not devices:
        console.print("[yellow]No devices configured. Use 'wake add device' to add a device.[/yellow]")
        return

    # Show spinner while checking status
    with Progress(
        SpinnerColumn(),
        TextColumn("[yellow]Checking device statuses...[/yellow]"),
        transient=True,
    ) as progress:
        progress.add_task("", total=None)
        
        # Get status for all devices concurrently
        device_statuses = device_manager.check_all_devices_status(devices)

    # Display results
    table = Table(show_header=True)
    table.add_column("Name", min_width=15)
    table.add_column("IP Address", min_width=15)
    table.add_column("MAC Address", min_width=17)
    table.add_column("Hostname", min_width=20)
    table.add_column("Status", min_width=10)

    for device in devices:
        status = "Awake" if device_statuses[device.name] else "Sleeping"
        table.add_row(device.name, device.ip_address, device.mac_address, device.hostname or "N/A", status)

    console.print(table)

@cli.command(name="check")
@click.argument('name', required=False)
def check_device(name: str = None):
    """Check the status of a specific device or all devices."""
    if name:
        try:
            device = device_manager.get_device(name)
            status = "Awake" if device_manager.check_device_status(name) else "Sleeping"
            console.print(f"Device '{name}' is {status}")
        except KeyError:
            console.print(f"[red]Device '{name}' not found[/red]")
    else:
        # Show status of all devices
        check_status()

@cli.command(name="list")
def list_devices():
    """List all configured devices."""
    devices = device_manager.list_devices()
    if not devices:
        console.print("[yellow]No devices configured. Use 'wake add device' to add a device.[/yellow]")
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
        console.print("[yellow]No devices configured. Use 'wake add device' to add a device.[/yellow]")
        return

    if name:
        try:
            device = device_manager.get_device(name)
        except KeyError:
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
                console.print("[red]Invalid device number[/red]")
        except ValueError:
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
        updated_device = Device(
            name=name,
            ip_address=ip_address,
            mac_address=mac_address,
            hostname=hostname or None
        )
        device_manager.update_device(name, updated_device)
        console.print(f"[green]Device '{name}' updated successfully[/green]")

        if click.confirm("Do you want to setup SSH to be able to use the sleep command?"):
            setup_ssh_config(name)

    except ValueError as e:
        console.print(f"[red]Error: {str(e)}[/red]")

@cli.group(name="add")
def add_group():
    """Add a new device or configure SSH."""
    pass

@add_group.command(name="device")
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

@add_group.command(name="ssh")
@click.argument('name', required=False)
def add_ssh(name: str = None):
    """Set up SSH configuration for a device."""
    if name:
        setup_ssh_config(name)
    else:
        devices = device_manager.list_devices()
        if not devices:
            console.print("[yellow]No devices configured. Use 'wake add device' to add a device.[/yellow]")
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
            console.print("[yellow]No devices configured. Use 'wake add device' to add a device.[/yellow]")
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
# Entry point for wake command - can handle direct device name
def wake_cli():
    """Entry point for wake command."""
    # Check if first argument is a device name (not starting with -)
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        device_name = sys.argv[1]
        # Check if it's a subcommand
        if device_name in ['add', 'check', 'list', 'remove', 'sleep', 'wake', 'status', 'edit']:
            # It's a subcommand, let Click handle it normally
            cli()
            return
        
        # Try to handle it as a device name
        try:
            # Remove the device name from argv so it doesn't confuse click
            original_argv = sys.argv.copy()
            sys.argv = [sys.argv[0]]
            
            # Get the device manager and try to wake the device
            from wakesleepmanager.device_manager import DeviceManager
            device_manager = DeviceManager()
            
            # Check if device exists
            device_manager.get_device(device_name)  # Will raise KeyError if not found
            
            # Show spinner while checking status
            from rich.progress import Progress, SpinnerColumn, TextColumn
            from rich.console import Console
            console = Console()
            
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[yellow]Checking if '{device_name}' is already awake...[/yellow]"),
                transient=True,
            ) as progress:
                progress.add_task("", total=None)
                is_awake = device_manager.check_device_status(device_name)
            
            if is_awake:
                console.print(f"[yellow]Device '{device_name}' is already awake[/yellow]")
            else:
                with Progress(
                    SpinnerColumn(),
                    TextColumn(f"[yellow]Waking up '{device_name}'...[/yellow]"),
                    transient=True,
                ) as progress:
                    progress.add_task("", total=None)
                    device_manager.wake_device(device_name)
                console.print(f"[green]Sent wake-up signal to device '{device_name}'[/green]")
            return
        except KeyError:
            # Not a valid device, restore args and continue with normal CLI
            console = Console()
            console.print(f"[red]Device '{device_name}' not found[/red]")
            return
    
    # Run the normal CLI
    cli()
# Entry point for sleep command - can handle direct device name
def sleep_cli():
    """Entry point for sleep command."""
    # Check if first argument is a device name (not starting with -)
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        device_name = sys.argv[1]
        # Check if it's a subcommand
        if device_name in ['device', 'add', 'add-ssh']:
            # It's a subcommand, let Click handle it normally
            cli()
            return
        
        # Try to handle it as a device name
        try:
            # Remove the device name from argv so it doesn't confuse click
            original_argv = sys.argv.copy()
            sys.argv = [sys.argv[0]]
            
            device = device_manager.get_device(device_name)
            if not device_manager.check_device_status(device_name):
                console.print(f"[yellow]Device '{device_name}' is already sleeping[/yellow]")
            else:
                try:
                    device_manager.sleep_device(device_name)
                    console.print(f"[green]Sent sleep signal to device '{device_name}'[/green]")
                except (ValueError, RuntimeError) as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
            return
        except KeyError:
            # Not a valid device, restore args and continue with normal CLI
            sys.argv = original_argv
    
    # Run the sleep command with no args
    if len(sys.argv) == 1:
        sleep_device(None)
        return
    
    # Otherwise run the normal CLI
    cli()

if __name__ == '__main__':
    cli()
