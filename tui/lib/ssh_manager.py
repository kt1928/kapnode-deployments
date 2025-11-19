"""SSH Manager - Handle SSH connections, key detection, and remote command execution."""

import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException


class SSHManager:
    """Manage SSH connections and operations."""

    def __init__(self):
        self.ssh_client: Optional[paramiko.SSHClient] = None

    def detect_ssh_key(self) -> Optional[Path]:
        """
        Auto-detect SSH keys in priority order.

        Returns:
            Path to SSH key if found, None otherwise
        """
        ssh_dir = Path.home() / ".ssh"
        key_priorities = [
            "homelab_rsa",
            "homelab_ed25519",
            "id_ed25519",
            "id_rsa",
        ]

        for key_name in key_priorities:
            key_path = ssh_dir / key_name
            if key_path.exists() and key_path.is_file():
                # Check if it's a valid private key
                try:
                    with open(key_path, 'r') as f:
                        content = f.read()
                        if "PRIVATE KEY" in content:
                            return key_path
                except Exception:
                    continue

        return None

    def generate_ssh_key(self, path: Path, key_type: str = "ed25519") -> bool:
        """
        Generate a new SSH key pair.

        Args:
            path: Path to save the private key
            key_type: Type of key (ed25519 or rsa)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure .ssh directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            # Generate key using ssh-keygen
            cmd = [
                "ssh-keygen",
                "-t", key_type,
                "-f", str(path),
                "-C", "homelab-deployments",
                "-N", "",  # No passphrase
            ]

            if key_type == "rsa":
                cmd.extend(["-b", "4096"])

            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0

        except Exception as e:
            print(f"Error generating SSH key: {e}")
            return False

    def test_connection(self, host: str, user: str, key: Path, port: int = 22) -> bool:
        """
        Test SSH connection to target host.

        Args:
            host: Hostname or IP address
            user: Username for SSH connection
            key: Path to SSH private key
            port: SSH port (default 22)

        Returns:
            True if connection successful, False otherwise
        """
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(
                hostname=host,
                port=port,
                username=user,
                key_filename=str(key),
                timeout=10,
                look_for_keys=False,
                allow_agent=False,
            )

            # Test with a simple command
            stdin, stdout, stderr = client.exec_command("echo 'test'")
            result = stdout.read().decode().strip()

            client.close()
            return result == "test"

        except (SSHException, AuthenticationException, Exception) as e:
            print(f"Connection test failed: {e}")
            return False

    def setup_ssh_key(self, host: str, user: str, key: Path, password: str) -> bool:
        """
        Setup SSH key on remote host using ssh-copy-id.

        Args:
            host: Hostname or IP address
            user: Username for SSH connection
            key: Path to SSH private key
            password: User password for initial connection

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use ssh-copy-id to copy the public key
            pub_key_path = Path(str(key) + ".pub")

            if not pub_key_path.exists():
                print(f"Public key not found: {pub_key_path}")
                return False

            # Use sshpass for password authentication
            cmd = [
                "ssh-copy-id",
                "-i", str(pub_key_path),
                f"{user}@{host}",
            ]

            # For security, we'll use paramiko instead of sshpass
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(
                hostname=host,
                username=user,
                password=password,
                timeout=10,
            )

            # Read public key
            with open(pub_key_path, 'r') as f:
                pub_key = f.read().strip()

            # Add to authorized_keys
            commands = [
                "mkdir -p ~/.ssh",
                "chmod 700 ~/.ssh",
                f"echo '{pub_key}' >> ~/.ssh/authorized_keys",
                "chmod 600 ~/.ssh/authorized_keys",
            ]

            for cmd in commands:
                stdin, stdout, stderr = client.exec_command(cmd)
                stdout.read()  # Wait for completion

            client.close()
            return True

        except Exception as e:
            print(f"Error setting up SSH key: {e}")
            return False

    def execute_command(
        self,
        host: str,
        user: str,
        command: str,
        key: Optional[Path] = None,
        port: int = 22,
    ) -> Tuple[str, str, int]:
        """
        Execute a remote command via SSH.

        Args:
            host: Hostname or IP address
            user: Username for SSH connection
            command: Command to execute
            key: Path to SSH private key (optional)
            port: SSH port (default 22)

        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs = {
                "hostname": host,
                "port": port,
                "username": user,
                "timeout": 30,
            }

            if key:
                connect_kwargs["key_filename"] = str(key)
                connect_kwargs["look_for_keys"] = False
                connect_kwargs["allow_agent"] = False

            client.connect(**connect_kwargs)

            stdin, stdout, stderr = client.exec_command(command)

            stdout_data = stdout.read().decode()
            stderr_data = stderr.read().decode()
            exit_code = stdout.channel.recv_exit_status()

            client.close()

            return stdout_data, stderr_data, exit_code

        except Exception as e:
            return "", str(e), 1

    def scp_file(
        self,
        local_path: Path,
        remote_path: str,
        host: str,
        user: str,
        key: Optional[Path] = None,
        port: int = 22,
    ) -> bool:
        """
        Copy file to remote host via SCP.

        Args:
            local_path: Local file path
            remote_path: Remote destination path
            host: Hostname or IP address
            user: Username for SSH connection
            key: Path to SSH private key (optional)
            port: SSH port (default 22)

        Returns:
            True if successful, False otherwise
        """
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            connect_kwargs = {
                "hostname": host,
                "port": port,
                "username": user,
                "timeout": 30,
            }

            if key:
                connect_kwargs["key_filename"] = str(key)
                connect_kwargs["look_for_keys"] = False
                connect_kwargs["allow_agent"] = False

            client.connect(**connect_kwargs)

            # Use SFTP for file transfer
            sftp = client.open_sftp()
            sftp.put(str(local_path), remote_path)
            sftp.close()

            client.close()
            return True

        except Exception as e:
            print(f"Error copying file: {e}")
            return False

    def get_public_key(self, private_key_path: Path) -> Optional[str]:
        """
        Get public key content from private key path.

        Args:
            private_key_path: Path to private key

        Returns:
            Public key content as string, or None if not found
        """
        pub_key_path = Path(str(private_key_path) + ".pub")

        if pub_key_path.exists():
            try:
                with open(pub_key_path, 'r') as f:
                    return f.read().strip()
            except Exception:
                pass

        return None
