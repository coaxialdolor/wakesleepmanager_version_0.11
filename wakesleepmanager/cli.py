@click.group()
def cli():
    """WakeSleepManager - Control network devices remotely.
    
    This tool allows you to wake up sleeping devices using Wake-on-LAN,
    put devices to sleep via SSH, and check their current status.
    """
    pass

@cli.command(name="wake")
@click.argument('name', required=False)
def wake_device(name: str = None):
    """Wake up one or more devices using Wake-on-LAN.
    
    If NAME is provided, wake up that specific device.
    Otherwise, show an interactive list of devices to choose from.
    
    Examples:
      wake mypc     Wake up the device named "mypc"
      wake          Show interactive device selection
    """
    # Implementation remains the same
