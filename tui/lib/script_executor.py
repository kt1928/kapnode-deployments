"""Script Executor - Execute deployment scripts with live output streaming."""

from pathlib import Path
from typing import Dict, Iterator, Tuple, Optional
import re
from .ssh_manager import SSHManager


class ScriptExecutor:
    """Execute deployment scripts on remote hosts."""

    def __init__(self, ssh_manager: Optional[SSHManager] = None):
        """
        Initialize script executor.

        Args:
            ssh_manager: SSH manager instance (creates new one if None)
        """
        self.ssh_manager = ssh_manager or SSHManager()

    def prepare_deployment(self, params: Dict[str, any]) -> str:
        """
        Build deployment command string from parameters.

        Args:
            params: Dictionary of deployment parameters

        Returns:
            Complete command string for deployment
        """
        cmd_parts = ["bash /tmp/deploy-ubuntu-vm.sh"]

        # Required parameters
        if "name" in params:
            cmd_parts.append(f"--name {params['name']}")
        if "vmid" in params:
            cmd_parts.append(f"--vmid {params['vmid']}")
        if "ip" in params:
            cmd_parts.append(f"--ip {params['ip']}")

        # Network parameters
        if "gateway" in params:
            cmd_parts.append(f"--gateway {params['gateway']}")
        if "dns" in params:
            cmd_parts.append(f"--dns '{params['dns']}'")

        # Resource parameters
        if "memory" in params:
            cmd_parts.append(f"--memory {params['memory']}")
        if "cores" in params:
            cmd_parts.append(f"--cores {params['cores']}")
        if "disk_size" in params:
            cmd_parts.append(f"--disk-size {params['disk_size']}")
        if "storage" in params:
            cmd_parts.append(f"--storage {params['storage']}")

        # Storage parameters
        if params.get("longhorn_size", 0) > 0:
            cmd_parts.append(f"--longhorn-size {params['longhorn_size']}")
        if params.get("backup_size", 0) > 0:
            cmd_parts.append(f"--backup-size {params['backup_size']}")

        # Tailscale and SSH
        if "tailscale_key" in params:
            cmd_parts.append(f"--tailscale-key '{params['tailscale_key']}'")
        if "ssh_pubkey" in params:
            # SSH public key needs proper escaping
            pubkey = params['ssh_pubkey'].strip()
            cmd_parts.append(f"--ssh-pubkey '{pubkey}'")

        # Location and node type
        if "location" in params:
            cmd_parts.append(f"--location '{params['location']}'")
        if "node_type" in params:
            cmd_parts.append(f"--node-type {params['node_type']}")

        # K3s parameters
        if "k3s_master" in params and params["k3s_master"]:
            cmd_parts.append(f"--k3s-master '{params['k3s_master']}'")
        if "k3s_token" in params and params["k3s_token"]:
            cmd_parts.append(f"--k3s-token '{params['k3s_token']}'")

        # Auto-confirm
        cmd_parts.append("--yes")

        return " ".join(cmd_parts)

    def copy_script_to_host(
        self,
        script: Path,
        host: str,
        user: str,
        key: Optional[Path] = None
    ) -> bool:
        """
        Copy deployment script to Proxmox host.

        Args:
            script: Local path to deployment script
            host: Hostname or IP of Proxmox host
            user: Username for SSH connection
            key: Path to SSH private key

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.ssh_manager.scp_file(
                local_path=script,
                remote_path="/tmp/deploy-ubuntu-vm.sh",
                host=host,
                user=user,
                key=key
            )
        except Exception as e:
            print(f"Error copying script: {e}")
            return False

    def execute_deployment(
        self,
        command: str,
        host: str,
        user: str,
        key: Optional[Path] = None
    ) -> Iterator[str]:
        """
        Execute deployment command with streaming output.

        Args:
            command: Command to execute
            host: Hostname or IP
            user: Username
            key: SSH private key path

        Yields:
            Lines of output from command execution
        """
        try:
            import paramiko

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs = {
                "hostname": host,
                "username": user,
                "timeout": 30,
            }

            if key:
                connect_kwargs["key_filename"] = str(key)
                connect_kwargs["look_for_keys"] = False
                connect_kwargs["allow_agent"] = False

            client.connect(**connect_kwargs)

            # Execute command with pty for real-time output
            stdin, stdout, stderr = client.exec_command(command, get_pty=True)

            # Stream output line by line
            for line in stdout:
                yield line.rstrip('\n\r')

            # Also get any stderr output
            stderr_lines = stderr.read().decode()
            if stderr_lines:
                for line in stderr_lines.split('\n'):
                    if line.strip():
                        yield f"STDERR: {line}"

            client.close()

        except Exception as e:
            yield f"ERROR: {str(e)}"

    def parse_output(self, line: str) -> Dict[str, any]:
        """
        Parse deployment output line for progress and errors.

        Args:
            line: Single line of output

        Returns:
            Dictionary with parsed information (type, message, progress, etc.)
        """
        result = {
            "type": "info",
            "message": line,
            "progress": None,
            "stage": None
        }

        # Detect errors
        if "ERROR" in line or "FAILED" in line or "error:" in line.lower():
            result["type"] = "error"

        # Detect warnings
        elif "WARNING" in line or "WARN" in line:
            result["type"] = "warning"

        # Detect success
        elif "SUCCESS" in line or "✓" in line or "complete" in line.lower():
            result["type"] = "success"

        # Detect stages
        stage_patterns = [
            (r"Creating VM", "Creating VM"),
            (r"Downloading.*image", "Downloading Image"),
            (r"Configuring.*cloud-init", "Configuring Cloud-Init"),
            (r"Starting VM", "Starting VM"),
            (r"Waiting for.*boot", "Waiting for Boot"),
            (r"Installing.*K3s", "Installing K3s"),
            (r"Joining.*cluster", "Joining Cluster"),
            (r"Configuring.*Tailscale", "Configuring Tailscale"),
        ]

        for pattern, stage_name in stage_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                result["stage"] = stage_name
                break

        # Extract progress percentages
        progress_match = re.search(r'(\d+)%', line)
        if progress_match:
            result["progress"] = int(progress_match.group(1))

        return result

    def wait_for_completion(
        self,
        output_iterator: Iterator[str]
    ) -> Tuple[bool, str]:
        """
        Wait for deployment to complete and determine success/failure.

        Args:
            output_iterator: Iterator yielding output lines

        Returns:
            Tuple of (success: bool, final_message: str)
        """
        last_line = ""
        error_lines = []

        try:
            for line in output_iterator:
                last_line = line
                parsed = self.parse_output(line)

                if parsed["type"] == "error":
                    error_lines.append(line)

            # Determine success based on final output
            if error_lines:
                return False, "\n".join(error_lines)

            if "success" in last_line.lower() or "complete" in last_line.lower():
                return True, last_line

            # If we got here without errors, consider it success
            return True, "Deployment completed"

        except Exception as e:
            return False, f"Execution error: {str(e)}"

    def execute_remote_command(
        self,
        command: str,
        host: str,
        user: str,
        key: Optional[Path] = None
    ) -> Tuple[str, str, int]:
        """
        Execute a simple remote command and return results.

        Args:
            command: Command to execute
            host: Hostname or IP
            user: Username
            key: SSH private key path

        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        return self.ssh_manager.execute_command(
            host=host,
            user=user,
            command=command,
            key=key
        )

    def get_vm_status(
        self,
        vmid: int,
        host: str,
        user: str,
        key: Optional[Path] = None
    ) -> Optional[str]:
        """
        Get Proxmox VM status.

        Args:
            vmid: VM ID
            host: Proxmox hostname
            user: Username
            key: SSH key path

        Returns:
            VM status string (running, stopped, etc.) or None
        """
        stdout, stderr, exit_code = self.execute_remote_command(
            command=f"qm status {vmid}",
            host=host,
            user=user,
            key=key
        )

        if exit_code == 0 and stdout:
            # Parse output like "status: running"
            match = re.search(r'status:\s*(\w+)', stdout)
            if match:
                return match.group(1)

        return None
