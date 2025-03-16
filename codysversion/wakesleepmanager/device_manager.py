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
            # For Windows, use nohup or start to run the command in background
            cmd = 'start /b shutdown /h'
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
