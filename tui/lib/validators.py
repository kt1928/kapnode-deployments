"""Validators - Input validation for deployment parameters."""

import re
import ipaddress
from typing import Tuple, Optional


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class Validators:
    """Collection of input validators for deployment parameters."""

    @staticmethod
    def validate_ip(ip: str) -> Tuple[bool, str]:
        """
        Validate IPv4 address format.

        Args:
            ip: IP address string

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        try:
            ipaddress.IPv4Address(ip)
            return True, ""
        except ValueError:
            return False, f"Invalid IPv4 address: {ip}"

    @staticmethod
    def validate_vmid(vmid: int) -> Tuple[bool, str]:
        """
        Validate Proxmox VMID (100-999).

        Args:
            vmid: VM ID number

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not isinstance(vmid, int):
            try:
                vmid = int(vmid)
            except (ValueError, TypeError):
                return False, "VMID must be a number"

        if vmid < 100 or vmid > 999:
            return False, "VMID must be between 100 and 999"

        return True, ""

    @staticmethod
    def validate_hostname(hostname: str) -> Tuple[bool, str]:
        """
        Validate DNS-compatible hostname.

        Args:
            hostname: Hostname string

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not hostname:
            return False, "Hostname cannot be empty"

        if len(hostname) > 63:
            return False, "Hostname must be 63 characters or less"

        # RFC 1123 hostname validation
        pattern = r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$'
        if not re.match(pattern, hostname, re.IGNORECASE):
            return False, "Hostname must contain only letters, numbers, and hyphens, and start/end with alphanumeric"

        return True, ""

    @staticmethod
    def validate_resources(
        cores: int,
        ram: int,
        disk: int
    ) -> Tuple[bool, str]:
        """
        Validate resource allocations.

        Args:
            cores: CPU core count
            ram: RAM in GB
            disk: Disk size in GB

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        # Validate cores
        if not isinstance(cores, int) or cores < 1:
            return False, "CPU cores must be at least 1"
        if cores > 64:
            return False, "CPU cores should not exceed 64"

        # Validate RAM
        if not isinstance(ram, int) or ram < 1:
            return False, "RAM must be at least 1 GB"
        if ram > 512:
            return False, "RAM should not exceed 512 GB"

        # Validate disk
        if not isinstance(disk, int) or disk < 10:
            return False, "Disk size must be at least 10 GB"
        if disk > 10000:
            return False, "Disk size should not exceed 10 TB (10000 GB)"

        return True, ""

    @staticmethod
    def validate_tailscale_key(key: str) -> Tuple[bool, str]:
        """
        Validate Tailscale auth key format.

        Args:
            key: Tailscale auth key

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not key:
            return False, "Tailscale key cannot be empty"

        # Tailscale keys start with tskey-auth- or tskey-api-
        if not (key.startswith("tskey-auth-") or key.startswith("tskey-api-")):
            return False, "Tailscale key must start with 'tskey-auth-' or 'tskey-api-'"

        if len(key) < 40:
            return False, "Tailscale key appears too short"

        return True, ""

    @staticmethod
    def validate_network_config(
        ip: str,
        gateway: str,
        netmask: str
    ) -> Tuple[bool, str]:
        """
        Validate network configuration consistency.

        Args:
            ip: IP address
            gateway: Gateway IP address
            netmask: Network mask (CIDR notation, e.g., "192.168.1.0/24")

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        # Validate IP
        valid, error = Validators.validate_ip(ip)
        if not valid:
            return False, f"IP: {error}"

        # Validate gateway
        valid, error = Validators.validate_ip(gateway)
        if not valid:
            return False, f"Gateway: {error}"

        # Validate netmask and check if IP and gateway are in same network
        try:
            network = ipaddress.IPv4Network(netmask, strict=False)
            ip_addr = ipaddress.IPv4Address(ip)
            gateway_addr = ipaddress.IPv4Address(gateway)

            if ip_addr not in network:
                return False, f"IP {ip} is not in network {netmask}"

            if gateway_addr not in network:
                return False, f"Gateway {gateway} is not in network {netmask}"

            return True, ""

        except ValueError as e:
            return False, f"Network configuration error: {str(e)}"

    @staticmethod
    def validate_dns(dns: str) -> Tuple[bool, str]:
        """
        Validate DNS server list (comma-separated IPs).

        Args:
            dns: DNS servers (e.g., "8.8.8.8,8.8.4.4")

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not dns:
            return False, "DNS servers cannot be empty"

        dns_servers = [s.strip() for s in dns.split(',')]

        for server in dns_servers:
            valid, error = Validators.validate_ip(server)
            if not valid:
                return False, f"DNS server {server}: {error}"

        return True, ""

    @staticmethod
    def validate_ssh_key(key_content: str) -> Tuple[bool, str]:
        """
        Validate SSH public key format.

        Args:
            key_content: SSH public key content

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not key_content:
            return False, "SSH key cannot be empty"

        # SSH public keys typically start with ssh-rsa, ssh-ed25519, etc.
        valid_prefixes = ["ssh-rsa", "ssh-ed25519", "ssh-dss", "ecdsa-sha2"]

        if not any(key_content.strip().startswith(prefix) for prefix in valid_prefixes):
            return False, "SSH key must be a valid public key (ssh-rsa, ssh-ed25519, etc.)"

        # Basic format check: should have at least 3 parts (type, key, optional comment)
        parts = key_content.strip().split()
        if len(parts) < 2:
            return False, "SSH key format appears invalid"

        return True, ""

    @staticmethod
    def validate_location(location: str, valid_locations: list) -> Tuple[bool, str]:
        """
        Validate location against list of known locations.

        Args:
            location: Location name
            valid_locations: List of valid location names

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not location:
            return False, "Location cannot be empty"

        # Case-insensitive comparison
        location_lower = location.lower()
        valid_locations_lower = [loc.lower() for loc in valid_locations]

        if location_lower not in valid_locations_lower:
            return False, f"Invalid location. Must be one of: {', '.join(valid_locations)}"

        return True, ""

    @staticmethod
    def validate_node_type(node_type: str) -> Tuple[bool, str]:
        """
        Validate node type.

        Args:
            node_type: Node type (k3s-worker, k3s-master, backup)

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        valid_types = ["k3s-worker", "k3s-master", "backup"]

        if node_type not in valid_types:
            return False, f"Invalid node type. Must be one of: {', '.join(valid_types)}"

        return True, ""

    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """
        Validate URL format (for K3s master URL).

        Args:
            url: URL string

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        if not url:
            return False, "URL cannot be empty"

        # Basic URL validation
        url_pattern = r'^https?://[a-zA-Z0-9.-]+(:[0-9]+)?(/.*)?$'
        if not re.match(url_pattern, url):
            return False, "Invalid URL format (expected http:// or https://)"

        return True, ""

    @staticmethod
    def validate_all_deployment_params(params: dict) -> Tuple[bool, list]:
        """
        Validate all deployment parameters at once.

        Args:
            params: Dictionary of deployment parameters

        Returns:
            Tuple of (all_valid: bool, list_of_errors: list)
        """
        errors = []

        # Required parameters
        if "name" in params:
            valid, error = Validators.validate_hostname(params["name"])
            if not valid:
                errors.append(f"Hostname: {error}")

        if "vmid" in params:
            valid, error = Validators.validate_vmid(params["vmid"])
            if not valid:
                errors.append(f"VMID: {error}")

        if "ip" in params:
            valid, error = Validators.validate_ip(params["ip"])
            if not valid:
                errors.append(f"IP Address: {error}")

        if "gateway" in params:
            valid, error = Validators.validate_ip(params["gateway"])
            if not valid:
                errors.append(f"Gateway: {error}")

        if "dns" in params:
            valid, error = Validators.validate_dns(params["dns"])
            if not valid:
                errors.append(f"DNS: {error}")

        # Resources
        if all(k in params for k in ["cores", "memory", "disk_size"]):
            valid, error = Validators.validate_resources(
                params["cores"],
                params["memory"],
                params["disk_size"]
            )
            if not valid:
                errors.append(f"Resources: {error}")

        # Tailscale key
        if "tailscale_key" in params:
            valid, error = Validators.validate_tailscale_key(params["tailscale_key"])
            if not valid:
                errors.append(f"Tailscale: {error}")

        # SSH public key
        if "ssh_pubkey" in params:
            valid, error = Validators.validate_ssh_key(params["ssh_pubkey"])
            if not valid:
                errors.append(f"SSH Key: {error}")

        # Node type
        if "node_type" in params:
            valid, error = Validators.validate_node_type(params["node_type"])
            if not valid:
                errors.append(f"Node Type: {error}")

        # K3s master URL (optional but validate if provided)
        if params.get("k3s_master"):
            valid, error = Validators.validate_url(params["k3s_master"])
            if not valid:
                errors.append(f"K3s Master URL: {error}")

        # Network consistency check
        if all(k in params for k in ["ip", "gateway"]) and "network" in params:
            valid, error = Validators.validate_network_config(
                params["ip"],
                params["gateway"],
                params["network"]
            )
            if not valid:
                errors.append(f"Network Config: {error}")

        return len(errors) == 0, errors
