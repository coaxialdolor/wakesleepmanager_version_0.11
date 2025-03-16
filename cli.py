import sys

def sleep_cli():
    """Entry point for wsleep command."""
    # If a device name is provided directly
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        device_name = sys.argv[1]
        # Handle direct device name
        try:
            device_manager.get_device(device_name)  # Check if device exists
            if not device_manager.check_device_status(device_name):
                console.print(f"[yellow]Device '{device_name}' is already sleeping[/yellow]")
                return
            device_manager.sleep_device(device_name)
            console.print(f"[green]Sent sleep signal to device '{device_name}'[/green]")
        except KeyError:
            console.print(f"[red]Device '{device_name}' not found[/red]")
        return
    
    # Otherwise, run the sleep command group
    sleep()
