"""Inventory Manager - Read/write Ansible-compatible inventory files."""

import yaml
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime


class InventoryManager:
    """Manage Ansible-compatible inventory files."""

    def __init__(self, inventory_path: Optional[Path] = None):
        """
        Initialize inventory manager.

        Args:
            inventory_path: Path to inventory file (default: ~/.homelab/inventory.yml)
        """
        if inventory_path is None:
            inventory_path = Path.home() / ".homelab" / "inventory.yml"

        self.inventory_path = Path(inventory_path)
        self.inventory_data: Dict[str, Any] = {}

    def load_inventory(self, path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Load inventory from YAML file.

        Args:
            path: Optional path to inventory file (overrides default)

        Returns:
            Dictionary containing inventory data
        """
        if path:
            self.inventory_path = Path(path)

        if not self.inventory_path.exists():
            # Return empty inventory structure
            self.inventory_data = {
                "all": {
                    "children": {
                        "proxmox_hosts": {"hosts": {}},
                        "k3s_masters": {"hosts": {}},
                        "k3s_workers": {"hosts": {}},
                        "backup_nodes": {"hosts": {}},
                    }
                }
            }
            return self.inventory_data

        try:
            with open(self.inventory_path, 'r') as f:
                self.inventory_data = yaml.safe_load(f) or {}

            # Ensure basic structure exists
            if "all" not in self.inventory_data:
                self.inventory_data["all"] = {"children": {}}

            return self.inventory_data

        except Exception as e:
            print(f"Error loading inventory: {e}")
            return {}

    def save_inventory(self, data: Optional[Dict[str, Any]] = None, path: Optional[Path] = None) -> bool:
        """
        Save inventory to YAML file.

        Args:
            data: Inventory data to save (uses cached data if None)
            path: Optional path to save to (overrides default)

        Returns:
            True if successful, False otherwise
        """
        if path:
            self.inventory_path = Path(path)

        if data:
            self.inventory_data = data

        try:
            # Ensure directory exists
            self.inventory_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.inventory_path, 'w') as f:
                yaml.safe_dump(
                    self.inventory_data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2,
                )

            return True

        except Exception as e:
            print(f"Error saving inventory: {e}")
            return False

    def add_node(
        self,
        hostname: str,
        ip: str,
        vmid: int,
        location: str,
        node_type: str = "k3s-worker",
        **kwargs
    ) -> bool:
        """
        Add a new node to inventory.

        Args:
            hostname: Node hostname
            ip: IP address (can be Tailscale IP)
            vmid: Proxmox VMID
            location: Location tag
            node_type: Node type (k3s-worker, k3s-master, backup)
            **kwargs: Additional node properties

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load current inventory if not already loaded
            if not self.inventory_data:
                self.load_inventory()

            # Determine group based on node type
            if node_type == "k3s-master":
                group = "k3s_masters"
            elif node_type == "backup":
                group = "backup_nodes"
            else:
                group = "k3s_workers"

            # Ensure group exists
            if "all" not in self.inventory_data:
                self.inventory_data["all"] = {"children": {}}
            if "children" not in self.inventory_data["all"]:
                self.inventory_data["all"]["children"] = {}
            if group not in self.inventory_data["all"]["children"]:
                self.inventory_data["all"]["children"][group] = {"hosts": {}}
            if "hosts" not in self.inventory_data["all"]["children"][group]:
                self.inventory_data["all"]["children"][group]["hosts"] = {}

            # Build node data
            node_data = {
                "ansible_host": ip,
                "vmid": vmid,
                "location": location,
                "deployed": datetime.utcnow().isoformat() + "Z",
                "node_type": node_type,
            }

            # Add any additional properties
            node_data.update(kwargs)

            # Add node to inventory
            self.inventory_data["all"]["children"][group]["hosts"][hostname] = node_data

            # Save immediately
            return self.save_inventory()

        except Exception as e:
            print(f"Error adding node: {e}")
            return False

    def get_node(self, hostname: str) -> Optional[Dict[str, Any]]:
        """
        Get node information by hostname.

        Args:
            hostname: Node hostname

        Returns:
            Dictionary with node data, or None if not found
        """
        if not self.inventory_data:
            self.load_inventory()

        # Search all groups
        try:
            for group_name, group_data in self.inventory_data.get("all", {}).get("children", {}).items():
                hosts = group_data.get("hosts", {})
                if hostname in hosts:
                    node_data = hosts[hostname].copy()
                    node_data["hostname"] = hostname
                    node_data["group"] = group_name
                    return node_data
        except Exception:
            pass

        return None

    def list_nodes(
        self,
        location: Optional[str] = None,
        node_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all nodes, optionally filtered by location or type.

        Args:
            location: Filter by location (optional)
            node_type: Filter by node type (optional)

        Returns:
            List of node dictionaries
        """
        if not self.inventory_data:
            self.load_inventory()

        nodes = []

        try:
            for group_name, group_data in self.inventory_data.get("all", {}).get("children", {}).items():
                hosts = group_data.get("hosts", {})

                for hostname, node_data in hosts.items():
                    # Apply filters
                    if location and node_data.get("location") != location:
                        continue
                    if node_type and node_data.get("node_type") != node_type:
                        continue

                    # Build node info
                    node_info = node_data.copy()
                    node_info["hostname"] = hostname
                    node_info["group"] = group_name
                    nodes.append(node_info)

        except Exception as e:
            print(f"Error listing nodes: {e}")

        return nodes

    def update_node(self, hostname: str, **kwargs) -> bool:
        """
        Update existing node information.

        Args:
            hostname: Node hostname
            **kwargs: Properties to update

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.inventory_data:
                self.load_inventory()

            # Find and update node
            for group_name, group_data in self.inventory_data.get("all", {}).get("children", {}).items():
                hosts = group_data.get("hosts", {})

                if hostname in hosts:
                    hosts[hostname].update(kwargs)
                    return self.save_inventory()

            return False

        except Exception as e:
            print(f"Error updating node: {e}")
            return False

    def delete_node(self, hostname: str) -> bool:
        """
        Delete a node from inventory.

        Args:
            hostname: Node hostname

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.inventory_data:
                self.load_inventory()

            # Find and delete node
            for group_name, group_data in self.inventory_data.get("all", {}).get("children", {}).items():
                hosts = group_data.get("hosts", {})

                if hostname in hosts:
                    del hosts[hostname]
                    return self.save_inventory()

            return False

        except Exception as e:
            print(f"Error deleting node: {e}")
            return False

    def get_locations(self) -> List[str]:
        """
        Get list of unique locations from inventory.

        Returns:
            List of location names
        """
        locations = set()

        for node in self.list_nodes():
            if "location" in node:
                locations.add(node["location"])

        return sorted(list(locations))

    def get_next_vmid(self, start: int = 200, end: int = 999) -> int:
        """
        Get next available VMID.

        Args:
            start: Starting VMID range
            end: Ending VMID range

        Returns:
            Next available VMID
        """
        used_vmids = set()

        for node in self.list_nodes():
            if "vmid" in node:
                used_vmids.add(node["vmid"])

        # Find next available
        for vmid in range(start, end + 1):
            if vmid not in used_vmids:
                return vmid

        # If all taken, return end + 1
        return end + 1
