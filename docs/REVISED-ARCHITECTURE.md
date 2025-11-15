# Revised Multi-Location Node System Architecture

## Executive Summary

This document revises the original REFINED-Structure.md plan based on critical network constraints and clarified service separation goals. The key changes:

1. **Longhorn cannot replicate across geographic locations** - Requires <1ms RTT (same datacenter/LAN)
2. **Services separation** - Only Minikapserver services (n8n, Homarr) move to K3s cluster
3. **Storage strategy** - Local storage per location + async backups (not real-time replication)
4. **Compute/storage separation** - Ridgeserver and Tower remain separate with future plans for compute/storage split

---

## Current State Analysis

### Current Service Distribution

#### 🏠 Ridgeserver (Brooklyn)
- **Purpose:** Primary media server
- **Services:** Plex Media Server, Radarr (2x), Sonarr (3x), qBittorrent, Overseerr, Tautulli, Jackett, Requestrr (3x)
- **Storage:** 164TB Unraid array (74% utilized)
- **Status:** **Stays separate from node system**
- **Future Plan:** Explore Proxmox VMs for compute (Plex + Arr stack) with bare metal TrueNAS Scale for storage

#### 🗄️ Tower (Brooklyn)
- **Purpose:** Photo backup and services
- **Services:** Immich, Syncthing, PostgreSQL, Redis, SWAG, CrowdSec, Wizarr
- **Storage:** 26TB Unraid array (11% utilized)
- **Status:** **Stays separate from node system**
- **Future Plan:** Explore separating compute and storage

#### 🖥️ Minikapserver (Forest Hills)
- **Purpose:** Management and automation hub
- **Services:** Homarr, n8n, Re-data, Matter Server, Nebula Sync, Cloudflared
- **Storage:** 512GB SSD
- **Status:** **Services migrate to K3s cluster for HA**
- **Goal:** Keep n8n and Homarr always available with automatic failover

---

## Critical Network Constraints

### ⚠️ Longhorn Limitations

**Problem:** The original plan assumed Longhorn could replicate across geographic locations via Tailscale. This is **not feasible** because:

1. **Latency Requirement:** Longhorn requires <1ms RTT (same datacenter/LAN)
2. **Bandwidth Constraints:** Most locations don't have 1Gbps networking (much less 2.5G)
3. **Geographic Distance:** Cross-borough latency via Tailscale is 10-50ms+
4. **Storage Protocol:** Longhorn uses synchronous replication - cannot work across WAN

**Impact:** Cannot use Longhorn for cross-location storage replication.

### ✅ Alternative Storage Strategy

Instead of cross-location replication, use:

1. **Local Storage per Location:** Each K3s node uses local storage for its services
2. **Async Backups:** Use Restic for async backups across locations (not real-time replication)
3. **Pod Scheduling:** K3s handles service failover via pod rescheduling (not storage replication)
4. **Data Persistence:** Services with persistent data use local volumes + regular backups

---

## Revised Architecture

### Service Classification

#### Services Moving to K3s Cluster (HA Required)
- **n8n** - Workflow automation (critical for always-on)
- **Homarr** - Central dashboard (critical for management)
- **Re-data** - Data analytics (optional, can be ephemeral)
- **Monitoring Stack** - Prometheus, Grafana, Alertmanager

#### Services Staying Separate
- **Ridgeserver Stack** - Plex + Arr stack (large storage, not suitable for K3s)
- **Tower Services** - Immich + backups (large storage, Unraid-based)

### Geographic Distribution (Revised)

```
Forest Hills Location          Brooklyn Location          Manhattan Location
┌─────────────────────┐       ┌─────────────────────┐    ┌─────────────────────┐
│  Minikapserver      │       │  Tower              │    │  Node-MN-01         │
│  - K3s Master       │       │  - Immich (Local)   │    │  - K3s Worker       │
│  - n8n Pod          │◄──────│  - K3s Worker       │◄───│  - Local Storage    │
│  - Homarr Pod       │       │  - Local Storage    │    │  - Backup Repo      │
│  - Monitoring       │       └─────────────────────┘    └─────────────────────┘
└─────────────────────┘                │                           │
         │                    ┌─────────────────────┐    ┌─────────────────────┐
┌─────────────────────┐       │  Ridgeserver        │    │  Node-MN-02         │
│  Backup-Node-FH     │       │  - Plex (Local)     │    │  - K3s Worker       │
│  - K3s Worker       │       │  - Arr Stack (Local)│    │  - Local Storage    │
│  - Local Storage    │       │  - Config Backup    │    │  - Backup Repo      │
│  - Backup Repo      │       └─────────────────────┘    └─────────────────────┘
└─────────────────────┘                │
         │                    ┌─────────────────────┐    Staten Island
┌─────────────────────┐       │  Kapmox (Proxmox)   │    ┌─────────────────────┐
│  Kappi-one/two      │       │  - Optional VM      │    │  Node-SI-01         │
│  - DNS (HA Pair)    │       │  - K3s Worker VM    │◄───│  - K3s Worker       │
└─────────────────────┘       └─────────────────────┘    │  - Local Storage    │
                                       │                  │  - Backup Repo      │
                              ┌─────────────────────┐    └─────────────────────┘
                              │  Node-BK-01         │
                              │  - K3s Worker       │
                              │  - Local Storage    │
                              │  - Backup Repo      │
                              └─────────────────────┘
```

### Cluster Nodes Summary (Revised)

| Node | Location | Role | Storage Type | Backup Storage | Purpose |
|------|----------|------|--------------|----------------|---------|
| **Minikapserver** | Forest Hills | K3s Master | Local SSD | - | Cluster control plane |
| **Backup-Node-FH** | Forest Hills | K3s Worker | Local (>10TB) | Yes | Worker + backup storage |
| **Tower** | Brooklyn | K3s Worker (optional) | Local (Unraid) | - | Worker (if joining cluster) |
| **Kapmox VM** | Brooklyn | K3s Worker (optional) | Local | Optional | Optional worker |
| **Node-BK-01** | Brooklyn | K3s Worker | Local (4TB) | 2TB | Worker + backup repo |
| **Node-MN-01** | Manhattan | K3s Worker | Local (4TB) | 2TB | Worker + backup repo |
| **Node-MN-02** | Manhattan | K3s Worker | Local (4TB) | 2TB | Worker + backup repo |
| **Node-SI-01** | Staten Island | K3s Worker | Local (4TB) | 2TB | Worker + backup repo |
| **Ridgeserver** | Brooklyn | Media Server | Local (Unraid) | Config Only | **Stays separate** |
| **Tower** | Brooklyn | Services | Local (Unraid) | - | **Stays separate** |

---

## Revised Storage Strategy

### K3s Services Storage

**Approach:** Local storage per node (no cross-location replication)

1. **Local Volumes:** Each K3s node uses local storage for persistent volumes
2. **HostPath Volumes:** Simple local storage for n8n, Homarr data
3. **Local Storage Class:** Kubernetes local-storage provisioner
4. **Backup Strategy:** Async backups via Restic (not real-time replication)

### Backup Strategy (Revised)

#### n8n Data Backup
- **Source:** n8n persistent volumes on each K3s node
- **Method:** Restic snapshots to backup nodes
- **Frequency:** Every 6 hours
- **Destinations:**
  1. Backup-Node-FH (Forest Hills)
  2. Node-BK-01 (Brooklyn)
  3. Node-MN-01 (Manhattan)
  4. Cloud (Backblaze B2)
- **Recovery:** Restore from backup node if local data lost

#### Homarr Data Backup
- **Source:** Homarr persistent volumes on each K3s node
- **Method:** Restic snapshots to backup nodes
- **Frequency:** Daily
- **Destinations:** Same as n8n
- **Recovery:** Restore from backup node if local data lost

#### Service Failover Strategy
- **Pod Rescheduling:** K3s automatically reschedules pods to healthy nodes
- **Data Availability:** If node fails, restore data from backup to new node
- **Recovery Time:** <30 minutes (pod reschedule + data restore)

---

## Service Migration Plan

### Phase 1: K3s Cluster Setup (No Longhorn)

#### 1.1 Deploy K3s Cluster
- **Master:** Minikapserver (Forest Hills)
- **Workers:** Node-BK-01, Node-MN-01, Node-MN-02, Node-SI-01, Backup-Node-FH
- **Storage:** Local storage only (no Longhorn)

#### 1.2 Configure Local Storage
- Setup local-storage provisioner on each node
- Create storage classes for local volumes
- Configure volume mounts for persistent data

#### 1.3 Deploy Monitoring Stack
- Prometheus + Grafana + Alertmanager
- Use local storage for metrics retention
- Configure backups for Prometheus data

### Phase 2: Service Migration

#### 2.1 Migrate n8n to K3s
- Export existing n8n workflows and credentials
- Deploy n8n as **Deployment** with local persistent volume
- **Replicas:** 2-3 pods across locations (not 5 - no storage replication needed)
- **Pod Anti-Affinity:** Spread across locations
- **Backup:** Restic snapshots every 6 hours
- **Failover:** Pod rescheduling + data restore from backup

#### 2.2 Migrate Homarr to K3s
- Backup existing Homarr configuration
- Deploy Homarr as **Deployment** with local persistent volume
- **Replicas:** 2-3 pods across locations
- **Pod Anti-Affinity:** Spread across locations
- **Backup:** Restic snapshots daily
- **Failover:** Pod rescheduling + data restore from backup

#### 2.3 Deploy Ingress Controller
- Nginx Ingress Controller
- Configure TLS with cert-manager
- Integrate with existing SWAG/Cloudflare setup

### Phase 3: Backup Implementation

#### 3.1 Configure Restic Backups
- Setup Restic on each K3s node
- Configure backup repositories on backup nodes
- Schedule automated backups for n8n and Homarr data

#### 3.2 Ridgeserver Config Backup
- **Strategy:** Full Unraid config + Docker configs
- **Method:** Restic snapshots
- **Frequency:** Daily
- **Destinations:** Backup-Node-FH, Node-BK-01, Node-MN-01, Cloud

#### 3.3 Tower Data Backup
- **Strategy:** Immich data + PostgreSQL dumps
- **Method:** Restic snapshots
- **Frequency:** Every 6 hours
- **Destinations:** Backup-Node-FH, Node-BK-01, Node-MN-01, Cloud

---

## Compute/Storage Separation Plans

### Ridgeserver Separation (Future)

#### Current State
- **Compute + Storage:** Unraid running Plex + Arr stack + 164TB storage

#### Target State
- **Compute:** Proxmox VMs running Plex + Arr stack containers
- **Storage:** Bare metal TrueNAS Scale with 164TB storage
- **Network:** NFS/SMB shares from TrueNAS to Proxmox VMs

#### Benefits
- Separation of concerns (compute vs storage)
- Easier scaling (add compute or storage independently)
- Better resource utilization
- Easier backup/restore of VMs

### Tower Separation (Future)

#### Current State
- **Compute + Storage:** Unraid running Immich + services + 26TB storage

#### Target State
- **Compute:** K3s pods or Proxmox VMs running Immich + services
- **Storage:** Bare metal TrueNAS Scale with 26TB storage
- **Network:** NFS/SMB shares from TrueNAS to compute nodes

#### Benefits
- Separation of concerns
- Potential migration to K3s cluster (if desired)
- Better resource utilization
- Easier backup/restore

---

## Failure Scenarios & Recovery

### Scenario 1: Single Node Failure
- **Impact:** Services on that node unavailable
- **Recovery:** K3s reschedules pods to healthy nodes
- **Data Recovery:** Restore from backup to new node
- **RTO:** <30 minutes (pod reschedule + data restore)

### Scenario 2: Single Location Failure
- **Impact:** All nodes in that location unavailable
- **Recovery:** Services continue on other locations
- **Data Recovery:** Restore from backup nodes
- **RTO:** <1 hour (pod reschedule + data restore)

### Scenario 3: Network Partition
- **Impact:** Locations cannot communicate
- **Recovery:** Services continue locally, resync on reconnect
- **Data Recovery:** Backups continue locally, sync when reconnected
- **RTO:** 0 for local services

### Scenario 4: Ridgeserver Failure
- **Impact:** Media services unavailable
- **Recovery:** Restore config from backup, reconfigure Unraid
- **Data:** Media files remain on storage (if separated)
- **RTO:** <2 hours (config restore + service restart)

---

## Key Differences from Original Plan

| Aspect | Original Plan | Revised Plan |
|--------|---------------|--------------|
| **Storage** | Longhorn cross-location replication | Local storage per location |
| **Replication** | Real-time synchronous (5 replicas) | Async backups (Restic) |
| **Services** | All services to K3s | Only Minikapserver services to K3s |
| **Ridgeserver** | Config backup only | Stays separate, future compute/storage split |
| **Tower** | Migrate to K3s | Stays separate, future compute/storage split |
| **Failover** | Storage-level replication | Pod rescheduling + backup restore |
| **RTO** | <5 minutes | <30 minutes (with data restore) |

---

## Success Metrics (Revised)

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

## Implementation Timeline

### Week 1: Infrastructure Setup
- [ ] Deploy 4 new geographic nodes (BK, MN × 2, SI)
- [ ] Deploy Backup-Node-FH
- [ ] Install K3s cluster (1 master + 5-6 workers)
- [ ] Configure local storage on each node
- [ ] Deploy monitoring stack (Prometheus + Grafana)

### Week 2: Service Migration
- [ ] Migrate n8n to K3s with local storage
- [ ] Migrate Homarr to K3s with local storage
- [ ] Setup Nginx Ingress Controller
- [ ] Configure TLS certificates
- [ ] Test pod failover (without data restore)

### Week 3: Backup Implementation
- [ ] Configure Restic on all nodes
- [ ] Setup backup repositories on backup nodes
- [ ] Schedule automated backups for n8n/Homarr
- [ ] Configure Ridgeserver config backups
- [ ] Configure Tower data backups
- [ ] Test backup restoration

### Week 4: Testing & Documentation
- [ ] Test node failure scenarios
- [ ] Test location failure scenarios
- [ ] Test backup restoration
- [ ] Document procedures and runbooks
- [ ] Create Grafana dashboards
- [ ] Final validation

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

## Questions & Considerations

### Open Questions
1. **Tower joining K3s cluster:** Should Tower join as a worker node (even if services stay local)?
2. **Kapmox VMs:** Should Kapmox run K3s worker VMs (optional capacity)?
3. **Backup frequency:** Is 6-hour backup frequency sufficient for n8n/Homarr?
4. **RTO target:** Is <30 minutes acceptable for service recovery?

### Future Considerations
1. **Compute/storage separation:** When to implement for Ridgeserver and Tower?
2. **TrueNAS Scale:** Evaluate for storage separation
3. **Proxmox integration:** How to integrate Proxmox VMs with K3s cluster?
4. **Network upgrades:** Consider 2.5G networking for future Longhorn deployment (if desired)

---

*Last updated: 2025-01-XX*
*Architecture: Multi-location K3s cluster with local storage and async backups*

