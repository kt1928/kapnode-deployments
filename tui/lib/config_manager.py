"""Configuration Manager - Manage TUI configuration and deployment history."""

import json
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime


class ConfigManager:
    """Manage TUI configuration and deployment tracking."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config manager.

        Args:
            config_path: Path to config file (default: ~/.homelab-deploy.conf)
        """
        if config_path is None:
            config_path = Path.home() / ".homelab-deploy.conf"

        self.config_path = Path(config_path)
        self.config_data: Dict[str, Any] = {}

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from JSON file.

        Returns:
            Dictionary containing configuration data
        """
        if not self.config_path.exists():
            # Return default configuration
            self.config_data = self._get_default_config()
            return self.config_data

        try:
            with open(self.config_path, 'r') as f:
                self.config_data = json.load(f)

            # Ensure all default keys exist
            defaults = self._get_default_config()
            for key, value in defaults.items():
                if key not in self.config_data:
                    self.config_data[key] = value

            return self.config_data

        except Exception as e:
            print(f"Error loading config: {e}")
            return self._get_default_config()

    def save_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save configuration to JSON file.

        Args:
            config: Configuration data to save (uses cached data if None)

        Returns:
            True if successful, False otherwise
        """
        if config:
            self.config_data = config

        try:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, 'w') as f:
                json.dump(self.config_data, f, indent=2)

            return True

        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration structure.

        Returns:
            Default configuration dictionary
        """
        # Get Tailscale key from environment or use placeholder
        tailscale_key = os.environ.get('TAILSCALE_AUTH_KEY', '')
        if not tailscale_key:
            tailscale_key = "REPLACE_WITH_YOUR_TAILSCALE_KEY"

        return {
            "last_vmid": 205,
            "ssh_key": "~/.ssh/homelab_rsa",
            "proxmox_host": "kapmox",
            "proxmox_user": "root",
            "tailscale_key": tailscale_key,
            "locations": {
                "brooklyn": {
                    "network": "192.168.86.0/24",
                    "gateway": "192.168.86.1",
                    "dns": "192.168.86.1,8.8.8.8"
                },
                "manhattan": {
                    "network": "192.168.50.0/24",
                    "gateway": "192.168.50.1",
                    "dns": "192.168.50.1,8.8.8.8"
                },
                "staten_island": {
                    "network": "192.168.70.0/24",
                    "gateway": "192.168.70.1",
                    "dns": "192.168.70.1,8.8.8.8"
                },
                "forest_hills": {
                    "network": "192.168.50.0/24",
                    "gateway": "192.168.50.1",
                    "dns": "192.168.50.1,8.8.8.8"
                }
            },
            "k3s_master": "https://minikapserver:6443",
            "k3s_token": "",
            "defaults": {
                "cores": 4,
                "ram_gb": 16,
                "disk_gb": 200,
                "node_type": "k3s-worker",
                "storage": "local-lvm"
            },
            "deployment_history": []
        }

    def get_next_vmid(self) -> int:
        """
        Get next available VMID.

        Returns:
            Next VMID number
        """
        if not self.config_data:
            self.load_config()

        return self.config_data.get("last_vmid", 205) + 1

    def increment_vmid(self) -> int:
        """
        Increment and save VMID counter.

        Returns:
            New VMID number
        """
        if not self.config_data:
            self.load_config()

        new_vmid = self.get_next_vmid()
        self.config_data["last_vmid"] = new_vmid
        self.save_config()

        return new_vmid

    def get_location_defaults(self, location: str) -> Dict[str, str]:
        """
        Get network defaults for a location.

        Args:
            location: Location name (case-insensitive)

        Returns:
            Dictionary with network, gateway, dns keys
        """
        if not self.config_data:
            self.load_config()

        location_key = location.lower().replace(" ", "_")
        locations = self.config_data.get("locations", {})

        return locations.get(location_key, {
            "network": "192.168.1.0/24",
            "gateway": "192.168.1.1",
            "dns": "192.168.1.1,8.8.8.8"
        })

    def set_preference(self, key: str, value: Any) -> bool:
        """
        Set a configuration preference.

        Args:
            key: Configuration key (can use dot notation for nested keys)
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.config_data:
                self.load_config()

            # Handle nested keys (e.g., "defaults.cores")
            keys = key.split('.')
            current = self.config_data

            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]

            current[keys[-1]] = value
            return self.save_config()

        except Exception as e:
            print(f"Error setting preference: {e}")
            return False

    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration preference.

        Args:
            key: Configuration key (can use dot notation for nested keys)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if not self.config_data:
            self.load_config()

        try:
            # Handle nested keys (e.g., "defaults.cores")
            keys = key.split('.')
            current = self.config_data

            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return default

            return current

        except Exception:
            return default

    def add_deployment_history(
        self,
        hostname: str,
        vmid: int,
        location: str,
        ip: str,
        **kwargs
    ) -> bool:
        """
        Add a deployment to history.

        Args:
            hostname: Node hostname
            vmid: Proxmox VMID
            location: Location name
            ip: IP address
            **kwargs: Additional deployment details

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.config_data:
                self.load_config()

            if "deployment_history" not in self.config_data:
                self.config_data["deployment_history"] = []

            deployment = {
                "hostname": hostname,
                "vmid": vmid,
                "location": location,
                "ip": ip,
                "deployed_at": datetime.utcnow().isoformat() + "Z",
            }
            deployment.update(kwargs)

            self.config_data["deployment_history"].append(deployment)

            # Keep only last 100 deployments
            if len(self.config_data["deployment_history"]) > 100:
                self.config_data["deployment_history"] = \
                    self.config_data["deployment_history"][-100:]

            return self.save_config()

        except Exception as e:
            print(f"Error adding deployment history: {e}")
            return False

    def get_deployment_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent deployment history.

        Args:
            limit: Maximum number of deployments to return

        Returns:
            List of deployment dictionaries (most recent first)
        """
        if not self.config_data:
            self.load_config()

        history = self.config_data.get("deployment_history", [])
        return list(reversed(history[-limit:]))

    def get_locations(self) -> List[str]:
        """
        Get list of configured locations.

        Returns:
            List of location names
        """
        if not self.config_data:
            self.load_config()

        locations = self.config_data.get("locations", {}).keys()
        return [loc.replace("_", " ").title() for loc in locations]
