# Resilient Multi-Location Node System Deployment Plan

> [!warning] **IMPORTANT: This document has been revised**
> 
> **This original plan assumed Longhorn could replicate across geographic locations. This is NOT feasible due to network constraints:**
> - Longhorn requires <1ms RTT (same datacenter/LAN)
> - Cross-borough latency via Tailscale is 10-50ms+
> - Most locations don't have 1Gbps networking (much less 2.5G)
> - Longhorn uses synchronous replication - cannot work across WAN
> 
> **Please see the revised architecture:**
> - **[REVISED-ARCHITECTURE.md](./REVISED-ARCHITECTURE.md)** - Revised architecture without Longhorn cross-location replication
> - **[CURRENT-STATE-AND-PLANS.md](./CURRENT-STATE-AND-PLANS.md)** - Current state of each computer and future plans
> 
> **Key changes:**
> - No Longhorn cross-location replication (use local storage per location)
> - Use async backups (Restic) instead of real-time replication
> - Only Minikapserver services (n8n, Homarr) migrate to K3s cluster
> - Ridgeserver and Tower stay separate (future compute/storage separation)

## Overview

Deploy a K3s cluster across **5 geographic locations** with automatic failover for critical services (n8n, Homarr), industry-standard backups for Tower's personal data, and disaster recovery for Ridgeserver configurations.

> [!note] **Note:** This plan has been revised. See [REVISED-ARCHITECTURE.md](./REVISED-ARCHITECTURE.md) for the updated architecture.

---

## Architecture Summary

### Geographic Distribution

```
Forest Hills Location          Brooklyn Location          Manhattan Location
┌─────────────────────┐       ┌─────────────────────┐    ┌─────────────────────┐
│  Minikapserver      │       │  Tower              │    │  Node-MN-01         │
│  - K3s Master       │       │  - Immich Photos    │    │  - K3s Worker       │
│  - n8n (Primary)    │◄──────│  - Critical Data    │◄───│  - Longhorn (2TB)   │
│  - Homarr (Primary) │       │  - K3s Worker       │    │  - Backup Repo (2TB)│
│  - Monitoring       │       └─────────────────────┘    └─────────────────────┘
└─────────────────────┘                │                           │
         │                    ┌─────────────────────┐    ┌─────────────────────┐
┌─────────────────────┐       │  Ridgeserver        │    │  Node-MN-02         │
│  Backup-Node-FH     │       │  - Media Services   │    │  - K3s Worker       │
│  - K3s Worker       │       │  - Config Backup    │    │  - Longhorn (2TB)   │
│  - Longhorn Replica │◄──────┤  - Plex/Radarr/etc  │◄───│  - Backup Repo (2TB)│
│  - Restic Server    │       └─────────────────────┘    └─────────────────────┘
└─────────────────────┘                │
         │                    ┌─────────────────────┐    Staten Island
┌─────────────────────┐       │  Kapmox (Proxmox)   │    ┌─────────────────────┐
│  Kappi-one/two      │       │  - K3s Worker VM    │    │  Node-SI-01         │
│  - DNS (HA Pair)    │       │  - Backup VM        │◄───│  - K3s Worker       │
└─────────────────────┘       └─────────────────────┘    │  - Longhorn (2TB)   │
                                       │                  │  - Backup Repo (2TB)│
                              ┌─────────────────────┐    └─────────────────────┘
                              │  Node-BK-01         │
                              │  - K3s Worker       │
                              │  - Longhorn (2TB)   │
                              │  - Backup Repo (2TB)│
                              └─────────────────────┘
```

### Cluster Nodes Summary

| Node | Location | Role | Storage (Longhorn) | Storage (Backup) | Total |
|------|----------|------|-------------------|------------------|-------|
| **Minikapserver** | Forest Hills | K3s Master | Existing | - | - |
| **Backup-Node-FH** | Forest Hills | K3s Worker | Yes | Yes | >10TB |
| **Tower** | Brooklyn | K3s Worker | Yes | - | Existing |
| **Kapmox VM** | Brooklyn | K3s Worker | Optional | Optional | - |
| **Node-BK-01** | Brooklyn | K3s Worker | 2TB | 2TB | 4TB |
| **Ridgeserver** | Brooklyn | Media Server | - | Config Only | - |
| **Node-MN-01** | Manhattan | K3s Worker | 2TB | 2TB | 4TB |
| **Node-MN-02** | Manhattan | K3s Worker | 2TB | 2TB | 4TB |
| **Node-SI-01** | Staten Island | K3s Worker | 2TB | 2TB | 4TB |

**Total New Capacity:**
- **8TB** Longhorn distributed storage (4 nodes × 2TB)
- **8TB** backup repository capacity (4 nodes × 2TB)
- **5 geographic locations** (unprecedented redundancy)
- **Survivability:** 2+ simultaneous location failures

---

## Phase 1: Infrastructure Setup (Week 1)

### 1.1 Deploy Four New Geographic Nodes

#### Node-BK-01 (Brooklyn)
- **Purpose:** Additional Brooklyn capacity + geographic redundancy
- **Requirements:** 4TB SSD, Ubuntu 24.04 LTS
- **Configuration:**
  - Install Ubuntu 24.04 LTS
  - Configure static IP on 192.168.50.x
  - Join Tailscale mesh network
  - Partition storage: 2TB LVM (Longhorn) + 2TB LVM (Backups)

#### Node-MN-01 & Node-MN-02 (Manhattan)
- **Purpose:** Manhattan presence for latency + failover
- **Requirements:** 4TB SSD each, Ubuntu 24.04 LTS
- **Configuration:**
  - Install Ubuntu 24.04 LTS
  - Configure static IP on 192.168.50.x
  - Join Tailscale mesh network
  - Partition storage: 2TB LVM (Longhorn) + 2TB LVM (Backups) per node

#### Node-SI-01 (Staten Island)
- **Purpose:** Staten Island geographic diversity
- **Requirements:** 4TB SSD, Ubuntu 24.04 LTS
- **Configuration:**
  - Install Ubuntu 24.04 LTS
  - Configure static IP on 192.168.50.x
  - Join Tailscale mesh network
  - Partition storage: 2TB LVM (Longhorn) + 2TB LVM (Backups)

### 1.2 Deploy Backup Node (Forest Hills)
- **Purpose:** Dedicated backup storage + K3s worker
- **Requirements:** Storage capacity >10TB, Ubuntu 24.04 LTS
- **Location:** Forest Hills (geographic redundancy)
- **Configuration:**
  - Install Ubuntu 24.04 LTS
  - Configure static IP on 192.168.50.x
  - Join Tailscale mesh network
  - Setup LVM for flexible storage

### 1.3 Install K3s Cluster

#### Master Node: Minikapserver (Forest Hills)
```bash
# K3s server with embedded etcd, Longhorn storage, Traefik disabled
curl -sfL https://get.k3s.io | sh -s - server --cluster-init \
  --disable traefik --write-kubeconfig-mode 644
```

#### Worker Nodes:
```bash
# Join command for all worker nodes
curl -sfL https://get.k3s.io | K3S_URL=https://minikapserver:6443 \
  K3S_TOKEN=<token> sh -
```

**Worker node priority order:**
1. **Tower** (Brooklyn) - Primary failover target
2. **Node-MN-01** (Manhattan) - Low latency failover
3. **Node-MN-02** (Manhattan) - Secondary Manhattan node
4. **Backup-Node-FH** (Forest Hills) - Storage + failover
5. **Node-BK-01** (Brooklyn) - Additional Brooklyn capacity
6. **Node-SI-01** (Staten Island) - Geographic diversity
7. **Kapmox VM** (Brooklyn) - Optional additional capacity

**Network:** Leverage existing Tailscale mesh for cross-location communication

### 1.4 Deploy Longhorn Distributed Storage

- Install Longhorn on K3s cluster
- **Configure replication factor:** 3-5 (adjustable based on criticality)
  - Critical services (n8n, Homarr): 5 replicas (all locations)
  - Standard workloads: 3 replicas
- Set automatic snapshots for n8n/Homarr data
- Enable cross-location replication via Tailscale
- **Storage nodes:**
  - Backup-Node-FH: Full capacity
  - Tower: Existing capacity
  - Node-BK-01: 2TB
  - Node-MN-01: 2TB
  - Node-MN-02: 2TB
  - Node-SI-01: 2TB
  - **Total:** ~8TB+ distributed across 5 locations

---

## Phase 2: Monitoring & Alerting (Week 1-2)

### 2.1 Deploy Prometheus + Grafana Stack

**Components:**
- **Prometheus:** Metrics collection from all nodes
- **Grafana:** Visualization dashboards
- **Alertmanager:** Multi-channel notifications (Discord, email, Pushover)
- **Node Exporter:** System metrics on each server (9 nodes total)
- **Blackbox Exporter:** Service uptime monitoring

**Deployment:** Helm chart to K3s cluster with persistent storage on Longhorn

### 2.2 Configure Alerts

> [!important] Critical Alerts
> - Service health checks (n8n, Homarr)
> - Node availability (CPU, RAM, disk) across 5 locations
> - Storage capacity warnings (Ridgeserver disks 1 & 2!)
> - Backup job success/failure (4 backup nodes)
> - K3s cluster health
> - Cross-location network latency (Tailscale)
> - Longhorn replication status

---

## Phase 3: Critical Services Migration (Week 2-3)

### 3.1 Migrate n8n to K3s

- Export existing n8n workflows and credentials
- Deploy n8n as K3s **StatefulSet** with Longhorn volume
- **Replication:** 5 replicas across all locations
- Configure horizontal pod autoscaling
- Setup health checks for automatic failover
- **Pod anti-affinity:** Ensure pods spread across locations
  ```yaml
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          topologyKey: kubernetes.io/hostname
  ```
- Test failover: Kill pod, verify <5min recovery
- Update DNS: `n8n.ridgeserver.com` → K3s Ingress

### 3.2 Migrate Homarr to K3s

- Backup existing Homarr configuration
- Deploy Homarr as K3s **Deployment** with Longhorn volume
- **Replication:** 3-5 replicas across locations
- Configure pod anti-affinity (spread across Forest Hills, Brooklyn, Manhattan)
- Setup liveness/readiness probes
- Test failover across all locations
- **Session persistence:** Redis-backed sessions for seamless failover

### 3.3 Setup Ingress Controller

- Deploy **Nginx Ingress Controller** (replace Traefik)
- Configure TLS with **cert-manager** + Let's Encrypt
- Integrate with existing SWAG/Cloudflare setup
- Load balancing across replicas
- **Geographic routing:** Route to nearest healthy replica

---

## Phase 4: Backup Implementation (Week 3-4)

### 4.1 Ridgeserver Config Backup (Most Efficient)

**Strategy:** Full Unraid config + Docker configs + Plex metadata

#### Implementation with Restic:

**Backup Targets:**
```bash
/boot/config/          # Unraid system config
/mnt/user/appdata/     # All Docker configs (Plex, Radarr, Sonarr, etc.)
# Docker compose files
# Environment variables
```

**Frequency:** Daily incremental, weekly full

**Retention:** 7 daily, 4 weekly, 6 monthly

**Destinations:**
1. **Primary:** Backup-Node-FH (Forest Hills)
2. **Secondary:** Node-BK-01 (Brooklyn)
3. **Tertiary:** Node-MN-01 (Manhattan)
4. **Cloud:** Backblaze B2 encrypted

**Recovery:** Restore to new Unraid server, reconfigure disks, Docker containers auto-deploy

### 4.2 Tower Personal Data Backup (Industry Standard: 3-2-1)

**Strategy:** 3 copies, 2 different media types, 1 offsite

#### Implementation with Restic + Rclone:

**Critical Data:**
- Immich photos + database
- Immich PostgreSQL dumps
- Syncthing data
- Docker configs

**Backup Locations:**
1. **Real-time:** Longhorn replication across 5 locations
2. **Local snapshots (Brooklyn):** Node-BK-01
3. **Remote snapshots (Manhattan):** Node-MN-01, Node-MN-02
4. **Remote snapshots (Staten Island):** Node-SI-01
5. **Remote snapshots (Forest Hills):** Backup-Node-FH
6. **Cloud:** Backblaze B2 / Wasabi - Encrypted nightly backups

**Schedule:**
- **Longhorn:** Real-time replication
- **Restic snapshots:** Every 6 hours to all 4 backup nodes
- **Cloud sync:** Nightly at 2 AM

**Retention:**
- Hourly: 48 snapshots (2 days)
- Daily: 30 snapshots (1 month)
- Weekly: 12 snapshots (3 months)
- Monthly: 24 snapshots (2 years)

**Verification:** Weekly restore tests to temporary location

#### Backup Distribution Matrix

| Source | Backup Node 1 | Backup Node 2 | Backup Node 3 | Backup Node 4 | Cloud |
|--------|---------------|---------------|---------------|---------------|-------|
| **Tower** | Node-BK-01 | Node-MN-01 | Node-SI-01 | Backup-Node-FH | B2 |
| **Ridgeserver** | Backup-Node-FH | Node-BK-01 | Node-MN-01 | Node-SI-01 | B2 |
| **n8n data** | Longhorn 5x | - | - | - | - |
| **Homarr data** | Longhorn 5x | - | - | - | - |

### 4.3 Automated Backup Monitoring

- Prometheus metrics for backup job status (all 4 nodes)
- Grafana dashboard showing backup health across locations
- Alertmanager notifications on failures
- Weekly backup verification reports
- **Cross-location backup verification:** Verify backups are accessible from all locations

---

## Phase 5: High Availability Configuration (Week 4)

### 5.1 Service Failover Rules

#### n8n:
- **Replicas:** 5 (one per location: Forest Hills, Brooklyn × 2, Manhattan × 2, Staten Island)
- **Health check:** HTTP /healthz every 10s
- **Failover trigger:** 3 consecutive failures
- **Automatic pod rescheduling** on node failure
- **Recovery time:** <5 minutes
- **Data persistence:** Longhorn volume with 5 replicas

#### Homarr:
- **Replicas:** 3-5 across locations
- **StatefulSet** with Longhorn persistent volume
- **Session data** preserved across failovers
- **Recovery time:** <5 minutes
- **Pod distribution:** Spread across Forest Hills, Brooklyn, Manhattan

### 5.2 Data Replication

- **Longhorn automatic replication:** 3-5 replicas based on criticality
- **Replication across locations** via Tailscale
- **Automatic consistency checks**
- **Snapshot-based rollback capability**
- **Cross-location sync:** Monitor replication lag between locations

### 5.3 Failure Scenarios & Recovery

> [!warning] Disaster Recovery Scenarios
>
> **Scenario 1: Single Location Failure**
> - Impact: 0% (4 other locations available)
> - Recovery: Automatic pod rescheduling
> - RTO: <5 minutes
>
> **Scenario 2: Two Simultaneous Location Failures**
> - Impact: Minimal (3 locations still operational)
> - Recovery: Automatic failover to remaining nodes
> - RTO: <10 minutes
>
> **Scenario 3: Brooklyn Complete Outage** (Ridgeserver + Tower + Node-BK-01)
> - Impact: Media services offline, critical services continue
> - Recovery: Services run from Forest Hills/Manhattan/Staten Island
> - RTO: <5 minutes for critical services
>
> **Scenario 4: Network Partition** (Tailscale failure)
> - Impact: Cross-location replication paused
> - Recovery: Local services continue, replication resumes on reconnect
> - RTO: 0 for local services

---

## Phase 6: Documentation & Testing (Week 5)

### 6.1 Create Runbooks

- [ ] Disaster recovery procedures
- [ ] Node failure response (per location)
- [ ] Service restoration steps
- [ ] Backup restoration guides
- [ ] Monitoring dashboard guides
- [ ] Cross-location failover testing
- [ ] Network partition handling

### 6.2 Chaos Testing

**Test Matrix:**

| Test | Expected Outcome | RTO Target |
|------|------------------|------------|
| Shutdown Minikapserver | n8n/Homarr failover to Tower or Node-MN-01 | <5 min |
| Shutdown entire Brooklyn | Services continue from FH/Manhattan/SI | <5 min |
| Kill n8n pod | Automatic restart on another node | <2 min |
| Simulate network partition | Services continue locally, resync on reconnect | 0 min |
| Restore Tower backup | Full Immich recovery from any backup node | <30 min |
| Restore Ridgeserver config | Complete Unraid config restoration | <2 hours |

**Execution Steps:**
1. Simulate node failures (shutdown individual machines)
2. Verify service failover <5 minutes
3. Test backup restoration from all 4 backup nodes
4. Validate alerting pipeline (Discord/email/Pushover)
5. Document any issues and remediation
6. **Test cross-location failover:** Verify services move between locations

### 6.3 Documentation Repository Structure

```
docs/
├── architecture/
│   ├── network-topology.md
│   ├── k3s-cluster-design.md
│   ├── storage-architecture.md
│   ├── geographic-distribution.md (NEW)
│   └── failover-strategy.md (NEW)
├── runbooks/
│   ├── disaster-recovery.md
│   ├── node-failure-response.md
│   ├── backup-restoration.md
│   ├── service-migration.md
│   ├── location-failure-procedures.md (NEW)
│   └── network-partition-handling.md (NEW)
├── monitoring/
│   ├── grafana-dashboards/
│   │   ├── cluster-overview.json
│   │   ├── geographic-distribution.json (NEW)
│   │   └── backup-status.json
│   ├── prometheus-alerts.yaml
│   └── alerting-guide.md
└── deployment/
    ├── k3s-setup.sh
    ├── longhorn-config.yaml
    ├── node-provisioning/
    │   ├── brooklyn-node.sh (NEW)
    │   ├── manhattan-nodes.sh (NEW)
    │   └── staten-island-node.sh (NEW)
    ├── service-manifests/
    └── backup-scripts/
        ├── restic-config-all-nodes.sh (NEW)
        └── backup-verification.sh (NEW)
```

---

## Key Technologies & Tools

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Orchestration** | K3s | Lightweight Kubernetes |
| **Storage** | Longhorn | Distributed block storage (8TB+) |
| **Backup** | Restic | Encrypted, deduplicated snapshots |
| **Cloud Sync** | Rclone | S3-compatible cloud backup |
| **Monitoring** | Prometheus + Grafana | Metrics & visualization |
| **Alerting** | Alertmanager | Multi-channel notifications |
| **Networking** | Tailscale | Cross-location mesh VPN |
| **Ingress** | Nginx Ingress | Load balancing & TLS |
| **Cloud Storage** | Backblaze B2 | Cost-effective S3-compatible |

---

## Cost Estimate

### Cloud Storage (Backblaze B2):
- **Estimated data:** ~3TB (Tower) + 100GB (configs)
- **Cost:** ~$15/month storage + $1/GB egress (rarely used)
- **Total:** ~$15-20/month

### Hardware:
- **Existing:** Minikapserver, Tower, Ridgeserver, Kapmox, Kappi-one/two
- **New:**
  - Backup-Node-FH (>10TB storage)
  - 4× 4TB SSD nodes (Node-BK-01, Node-MN-01, Node-MN-02, Node-SI-01)
- **Total new capacity:** 26TB+ (10TB + 16TB)

---

## Success Metrics

- [x] n8n/Homarr failover <5 minutes
- [x] Tower data backed up to **5 locations** (local + 4 remote nodes + cloud)
- [x] Ridgeserver config backed up to **4 locations** (Forest Hills, Brooklyn, Manhattan, Staten Island + cloud)
- [x] Automated monitoring with alerting across all 5 locations
- [x] **Zero data loss** on single or dual location failure
- [x] **Geographic redundancy** across 5 NYC metro locations
- [x] **8TB Longhorn storage** distributed across cluster
- [x] **8TB backup repository** capacity across 4 dedicated nodes
- [x] Survive **2+ simultaneous location failures**

---

## Timeline: 5 Weeks

### Week 1: Infrastructure + Monitoring
- [ ] Deploy 4 new geographic nodes (BK, MN × 2, SI)
- [ ] Deploy Backup-Node-FH
- [ ] Install K3s cluster (1 master + 7 workers)
- [ ] Configure Longhorn with 5-location replication
- [ ] Deploy Prometheus + Grafana + Alertmanager

### Week 2-3: Service Migration to K3s
- [ ] Migrate n8n to K3s with 5-replica deployment
- [ ] Migrate Homarr to K3s with multi-location deployment
- [ ] Setup Nginx Ingress Controller
- [ ] Configure TLS certificates
- [ ] Test cross-location failover

### Week 3-4: Backup Implementation
- [ ] Configure Restic on all 4 backup nodes
- [ ] Setup Ridgeserver → 4-location backup
- [ ] Setup Tower → 5-location backup (Longhorn + 4 Restic nodes)
- [ ] Configure Backblaze B2 cloud sync
- [ ] Implement backup verification scripts

### Week 4: HA Configuration
- [ ] Configure service failover rules
- [ ] Setup pod anti-affinity for geographic spread
- [ ] Implement health checks and readiness probes
- [ ] Test disaster recovery scenarios
- [ ] Validate cross-location replication

### Week 5: Testing + Documentation
- [ ] Chaos testing (node failures, location outages)
- [ ] Backup restoration testing from all nodes
- [ ] Document runbooks and procedures
- [ ] Create Grafana dashboards for all locations
- [ ] Final validation and sign-off

---

## Advanced Features

### Geographic-Aware Routing
- **Low-latency routing:** Route users to nearest K3s node
- **Smart failover:** Prefer same-location failover before cross-location
- **Tailscale mesh:** Automatic routing optimization

### Storage Efficiency
- **Longhorn deduplication:** Reduce storage overhead
- **Restic deduplication:** Efficient incremental backups
- **Compression:** Enable on all storage layers

### Security
- **Encrypted backups:** All Restic backups encrypted at rest
- **Tailscale ACLs:** Restrict cross-location traffic
- **Network policies:** K3s NetworkPolicies for pod isolation
- **Secrets management:** Sealed Secrets or external vault

---

> [!tip] Next Steps
> 1. Provision the 4 new machines with Ubuntu 24.04 LTS
> 2. Partition storage on each: 2TB Longhorn + 2TB Backups
> 3. Join Tailscale mesh network
> 4. Begin K3s cluster deployment
> 5. Configure monitoring stack first (observability before migration)

---

*Last updated: 2025-11-13*
*Architecture: 5-location distributed K3s cluster with 8TB Longhorn storage and 8TB backup capacity*
