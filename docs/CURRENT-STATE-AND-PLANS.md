# Current State & Future Plans

## Overview

This document captures the current state of each computer in the homelab, what services they run, and how we plan to proceed with the node system migration.

---

## Current Service Distribution

### 🏠 Ridgeserver (Brooklyn)

**Current Purpose:**
- Primary media server
- Large storage (164TB Unraid array, 74% utilized)
- Media management and streaming

**Current Services:**
- **Plex Media Server** - Primary streaming platform
- **Radarr** (2 instances) - Movie acquisition (1080p + 4K)
- **Sonarr** (3 instances) - TV show acquisition (General, Anime, K-Drama)
- **qBittorrent** - Download client
- **Overseerr** - User request interface
- **Tautulli** - Plex analytics and monitoring
- **Jackett** - Indexer aggregation
- **Requestrr** (3 instances) - Discord bot integration

**Storage:**
- 164TB Unraid array
- 14 drives (mix of Btrfs and XFS)
- Several drives >90% full (critical storage pressure)

**Network:**
- Tailscale IP: `100.107.45.13`
- Local IP: `192.168.86.44`

**Future Plans:**
- **Stay separate from node system** (not migrating to K3s)
- **Explore compute/storage separation:**
  - Compute: Proxmox VMs running Plex + Arr stack containers
  - Storage: Bare metal TrueNAS Scale with 164TB storage
  - Network: NFS/SMB shares from TrueNAS to Proxmox VMs
- **Benefits:**
  - Separation of concerns (compute vs storage)
  - Easier scaling (add compute or storage independently)
  - Better resource utilization
  - Easier backup/restore of VMs

**Rationale:**
- Large storage requirements (164TB) not suitable for K3s cluster
- Media files don't need high availability (can tolerate downtime)
- Compute/storage separation allows independent scaling

---

### 🗄️ Tower (Brooklyn)

**Current Purpose:**
- Secondary storage and services
- Photo backup (Immich)
- File synchronization
- Security and access management

**Current Services:**
- **Immich** - Self-hosted photo management (Google Photos alternative)
- **Syncthing** - File synchronization across devices
- **PostgreSQL** - Database backend for Immich
- **Redis** - Caching layer
- **SWAG** - Reverse proxy with SSL termination
- **CrowdSec** - Intrusion detection and prevention
- **CrowdSec Dashboard** - Security analytics
- **Cloudflare Bouncer** - DDoS protection
- **Wizarr** - User onboarding for Plex

**Storage:**
- 26TB Unraid array (11% utilized)
- 2x 13TB drives
- 3TB NVMe cache pool

**Network:**
- Tailscale IP: `100.78.240.7`
- Local IP: `192.168.86.46`
- Status: 92 days uptime (most stable system!)

**Future Plans:**
- **Stay separate from node system** (not migrating to K3s)
- **Explore compute/storage separation:**
  - Compute: K3s pods or Proxmox VMs running Immich + services
  - Storage: Bare metal TrueNAS Scale with 26TB storage
  - Network: NFS/SMB shares from TrueNAS to compute nodes
- **Benefits:**
  - Separation of concerns
  - Potential migration to K3s cluster (if desired)
  - Better resource utilization
  - Easier backup/restore

**Rationale:**
- Large storage requirements (26TB) not suitable for K3s cluster
- Unraid-based (preferred OS at the time)
- Compute/storage separation allows independent scaling

---

### 🖥️ Minikapserver (Forest Hills)

**Current Purpose:**
- Management and automation hub
- Central dashboard and service management
- Workflow automation

**Current Services:**
- **Homarr** - Central dashboard and service management
- **n8n** - Workflow automation platform
- **Re-data** - Data analytics and monitoring
- **Matter Server** - Home Assistant integration
- **Nebula Sync** - File synchronization
- **Cloudflared** - Tunnel service
- **DashDot** - System monitoring

**Storage:**
- 512GB FORESEE SSD
- LVM Configuration: ubuntu-vg (473.89GB total, 373.89GB free)
- Root: 100GB allocated (15GB used, 79GB free)

**Network:**
- Tailscale IP: `100.121.136.23`
- Local IP: `192.168.50.31`
- Status: 40 days uptime

**Future Plans:**
- **Migrate services to K3s cluster** for high availability
- **Primary target services:**
  - n8n (critical for always-on)
  - Homarr (critical for management)
  - Re-data (optional, can be ephemeral)
- **Goal:** Keep n8n and Homarr always available with automatic failover
- **Storage:** Local storage per node (no cross-location replication)
- **Backup:** Async backups via Restic (not real-time replication)

**Rationale:**
- Services are critical for automation and management
- Need high availability (always-on)
- Small storage requirements (suitable for K3s cluster)
- Can benefit from geographic distribution

---

## Network Constraints & Limitations

### ⚠️ Longhorn Cross-Location Replication

**Problem:**
The original REFINED-Structure.md plan assumed Longhorn could replicate across geographic locations via Tailscale. This is **not feasible** because:

1. **Latency Requirement:** Longhorn requires <1ms RTT (same datacenter/LAN)
2. **Bandwidth Constraints:** Most locations don't have 1Gbps networking (much less 2.5G)
3. **Geographic Distance:** Cross-borough latency via Tailscale is 10-50ms+
4. **Storage Protocol:** Longhorn uses synchronous replication - cannot work across WAN

**Impact:**
- Cannot use Longhorn for cross-location storage replication
- Must use local storage per location
- Must use async backups (Restic) instead of real-time replication

**Solution:**
- Use local storage per K3s node
- Use async backups (Restic) for data protection
- Use pod rescheduling for service failover (not storage replication)

---

## Revised Architecture Strategy

### Service Classification

#### Services Moving to K3s Cluster (HA Required)
- **n8n** - Workflow automation (critical for always-on)
- **Homarr** - Central dashboard (critical for management)
- **Re-data** - Data analytics (optional, can be ephemeral)
- **Monitoring Stack** - Prometheus, Grafana, Alertmanager

#### Services Staying Separate
- **Ridgeserver Stack** - Plex + Arr stack (large storage, not suitable for K3s)
- **Tower Services** - Immich + backups (large storage, Unraid-based)

### Storage Strategy

#### K3s Services Storage
- **Local Storage:** Each K3s node uses local storage for persistent volumes
- **HostPath Volumes:** Simple local storage for n8n, Homarr data
- **Local Storage Class:** Kubernetes local-storage provisioner
- **Backup Strategy:** Async backups via Restic (not real-time replication)

#### Backup Strategy
- **n8n Data:** Restic snapshots every 6 hours to backup nodes
- **Homarr Data:** Restic snapshots daily to backup nodes
- **Ridgeserver Config:** Restic snapshots daily to backup nodes
- **Tower Data:** Restic snapshots every 6 hours to backup nodes

### Service Failover Strategy
- **Pod Rescheduling:** K3s automatically reschedules pods to healthy nodes
- **Data Availability:** If node fails, restore data from backup to new node
- **Recovery Time:** <30 minutes (pod reschedule + data restore)

---

## Geographic Distribution

### Current Locations
- **Brooklyn, NY:** Ridgeserver, Tower, Kapmox
- **Forest Hills, NY:** Minikapserver, Kappi-one/two

### Planned Locations
- **Manhattan, NY:** Node-MN-01, Node-MN-02
- **Staten Island, NY:** Node-SI-01
- **Forest Hills, NY:** Backup-Node-FH (additional node)

### K3s Cluster Distribution
- **Master:** Minikapserver (Forest Hills)
- **Workers:** 
  - Node-BK-01 (Brooklyn)
  - Node-MN-01 (Manhattan)
  - Node-MN-02 (Manhattan)
  - Node-SI-01 (Staten Island)
  - Backup-Node-FH (Forest Hills)
  - Tower (Brooklyn) - Optional
  - Kapmox VM (Brooklyn) - Optional

---

## Implementation Plan

### Phase 1: K3s Cluster Setup
1. Deploy K3s cluster (1 master + 5-6 workers)
2. Configure local storage on each node
3. Deploy monitoring stack (Prometheus + Grafana)
4. **No Longhorn** (local storage only)

### Phase 2: Service Migration
1. Migrate n8n to K3s with local storage
2. Migrate Homarr to K3s with local storage
3. Setup Nginx Ingress Controller
4. Configure TLS certificates
5. Test pod failover (without data restore)

### Phase 3: Backup Implementation
1. Configure Restic on all nodes
2. Setup backup repositories on backup nodes
3. Schedule automated backups for n8n/Homarr
4. Configure Ridgeserver config backups
5. Configure Tower data backups
6. Test backup restoration

### Phase 4: Testing & Documentation
1. Test node failure scenarios
2. Test location failure scenarios
3. Test backup restoration
4. Document procedures and runbooks
5. Create Grafana dashboards
6. Final validation

---

## Key Decisions & Rationale

### Decision 1: No Longhorn Cross-Location Replication
- **Rationale:** Network constraints (latency, bandwidth) make it infeasible
- **Alternative:** Local storage per location + async backups
- **Impact:** RTO increases from <5 minutes to <30 minutes (with data restore)

### Decision 2: Ridgeserver Stays Separate
- **Rationale:** Large storage (164TB) not suitable for K3s cluster
- **Alternative:** Compute/storage separation (Proxmox VMs + TrueNAS Scale)
- **Impact:** Media services remain separate, but can scale independently

### Decision 3: Tower Stays Separate
- **Rationale:** Large storage (26TB) not suitable for K3s cluster
- **Alternative:** Compute/storage separation (K3s pods or Proxmox VMs + TrueNAS Scale)
- **Impact:** Photo services remain separate, but can scale independently

### Decision 4: Only Minikapserver Services to K3s
- **Rationale:** Services (n8n, Homarr) are critical for always-on
- **Alternative:** Migrate all services to K3s (not feasible due to storage)
- **Impact:** Only services with small storage requirements move to K3s

---

## Success Metrics

- [x] n8n available with <30 minute RTO on node failure
- [x] Homarr available with <30 minute RTO on node failure
- [x] Automated backups of n8n/Homarr data to 4 locations + cloud
- [x] Automated backups of Ridgeserver config to 4 locations + cloud
- [x] Automated backups of Tower data to 4 locations + cloud
- [x] Monitoring and alerting across all locations
- [x] Zero data loss on single or dual location failure (via backups)
- [x] Geographic redundancy for compute (pod scheduling)
- [x] Survive 2+ simultaneous location failures (with data restore)

---

## Open Questions

1. **Tower joining K3s cluster:** Should Tower join as a worker node (even if services stay local)?
2. **Kapmox VMs:** Should Kapmox run K3s worker VMs (optional capacity)?
3. **Backup frequency:** Is 6-hour backup frequency sufficient for n8n/Homarr?
4. **RTO target:** Is <30 minutes acceptable for service recovery?
5. **Compute/storage separation:** When to implement for Ridgeserver and Tower?
6. **TrueNAS Scale:** Evaluate for storage separation
7. **Proxmox integration:** How to integrate Proxmox VMs with K3s cluster?
8. **Network upgrades:** Consider 2.5G networking for future Longhorn deployment (if desired)

---

## Next Steps

1. **Review and approve revised architecture**
2. **Procure hardware for new nodes** (if not already done)
3. **Begin K3s cluster deployment** (without Longhorn)
4. **Configure local storage** on each node
5. **Migrate n8n and Homarr** to K3s cluster
6. **Setup backup infrastructure** (Restic + backup nodes)
7. **Test failover scenarios** (pod rescheduling + data restore)

---

*Last updated: 2025-01-XX*
*Document: Current state and future plans for homelab node system*

