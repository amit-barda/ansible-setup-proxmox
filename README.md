# Proxmox Infrastructure Lab

Ansible-driven provisioning of a 5-VM private lab on Proxmox VE — with NAT routing, authoritative DNS, GitLab CI/CD, K3s Kubernetes, and a sample Flask microservice deployed via pipeline.

## Architecture

```
Internet
    │
┌───┴───────────────────────────────┐
│  router.test.local  10.20.30.1    │  WAN: DHCP on vmbr0
│  (nftables NAT / IP forwarding)   │  LAN: static on vmbr1
└───┬───────────────────────────────┘
    │  vmbr1  (10.20.30.0/24)
    │
    ├── dns.test.local      10.20.30.250   BIND9 authoritative + forwarder
    ├── gitlab.test.local   10.20.30.100   GitLab CE + Container Registry (:5050) + Runner
    ├── dev.test.local      10.20.30.99    Docker, Git, kubectl, developer user
    └── k3s.test.local      10.20.30.200   Single-node K3s cluster
```

A Flask "random word" service is pushed to GitLab, built by CI into the Container Registry, and deployed as a 3-replica Kubernetes Deployment accessible on `http://k3s.test.local:30500/`.

## Prerequisites

| Requirement | Details |
|---|---|
| **Proxmox VE host** | API access via token or user/password |
| **Ubuntu 22.04 cloud image** | Imported as a Proxmox VM template (cloud-init ready) |
| **Proxmox bridges** | `vmbr0` (internet-facing), `vmbr1` (private LAN) |
| **Ansible controller** | Ansible >= 2.14, Python 3.x |
| **Python packages** | `proxmoxer`, `requests` |
| **SSH key** | `~/.ssh/id_rsa` / `~/.ssh/id_rsa.pub` on the Ansible controller |
| **Proxmox snippets storage** | `local:snippets` available on the Proxmox node (defaults to `/var/lib/vz/snippets`) |

## Quick Start

### 1. Install dependencies

```bash
pip3 install proxmoxer requests ansible-lint

ansible-galaxy collection install -r requirements.yml
```

### 2. Configure Proxmox credentials

The file `inventories/lab/group_vars/proxmox.yml` is Ansible Vault-encrypted. To edit it with your real values:

```bash
ansible-vault edit inventories/lab/group_vars/proxmox.yml
```

Required variables inside the vault file:

```yaml
proxmox_api_host: "YOUR_PROXMOX_IP"
proxmox_api_user: "root@pam"
proxmox_api_password: "YOUR_PASSWORD"
proxmox_node: "pve"
template_name: "ubuntu-2204-cloud"
template_vmid: "YOUR_TEMPLATE"
gitlab_root_password: "YourGitLabRootPass"
developer_password: "YourDevPass"
gitlab_runner_registration_token: ""
```

### 3. Deploy everything

Run the full lab from scratch with a single command:

```bash
ansible-playbook playbooks/site.yml --ask-vault-pass
```

This executes all stages in order:

| Stage | Playbook | What it does |
|---|---|---|
| 0 | `00-provision-vms.yml` | Clone and start 5 VMs from cloud-init template |
| 1 | `01-router.yml` | Configure NAT router (dual-NIC, nftables, IP forwarding) |
| 2 | `02-dns.yml` | Install BIND9, create forward/reverse zones for `test.local` |
| 3 | `03-gitlab.yml` | Install GitLab CE, Container Registry, create developer user, register CI runner |
| 4 | `04-workstation.yml` | Install Docker, Git, create developer user + SSH key to GitLab |
| 5 | `05-k3s.yml` | Install K3s, distribute kubeconfig to dev workstation |
| 6 | `06-app-deploy.yml` | Push Flask app to GitLab, build via CI, deploy to K3s |
| -- | Validation | Smoke tests: DNS, NAT, GitLab, K3s, app endpoint |

### 4. Run individual stages

Use tags to run specific parts:

```bash
# Only provision VMs
ansible-playbook playbooks/site.yml --ask-vault-pass --tags provision

# Only configure networking (router + DNS)
ansible-playbook playbooks/site.yml --ask-vault-pass --tags network

# Only deploy the app
ansible-playbook playbooks/site.yml --ask-vault-pass --tags app

# Only run validation smoke tests
ansible-playbook playbooks/site.yml --ask-vault-pass --tags validate
```

Or run individual playbooks directly:

```bash
ansible-playbook playbooks/03-gitlab.yml --ask-vault-pass
```

## Teardown

Destroy all VMs:

```bash
ansible-playbook playbooks/00-provision-vms.yml --ask-vault-pass -e vm_state=absent
```

## Project Structure

```
proxmox-infra-lab/
├── ansible.cfg                          # Ansible configuration
├── requirements.yml                     # Galaxy collections
├── inventories/lab/
│   ├── hosts.yml                        # All hosts and groups
│   ├── group_vars/
│   │   ├── all.yml                      # Domain, subnet, lab_hosts map
│   │   ├── private_subnet.yml           # Shared NIC config for lab VMs
│   │   └── proxmox.yml                  # Vault-encrypted secrets
│   └── host_vars/
│       ├── router.yml                   # VM 110 — dual NIC, NAT config
│       ├── dns.yml                      # VM 111 — BIND zones/forwarders
│       ├── gitlab.yml                   # VM 112 — GitLab URLs, 4 CPU / 8 GB
│       ├── dev.yml                      # VM 113 — developer user details
│       └── k3s.yml                      # VM 114 — K3s TLS SAN, DNS
├── playbooks/
│   ├── site.yml                         # Master playbook (all stages + validation)
│   ├── 00-provision-vms.yml             # Clone VMs via Proxmox API
│   ├── 01-router.yml                    # NAT router setup
│   ├── 02-dns.yml                       # BIND9 DNS server
│   ├── 03-gitlab.yml                    # GitLab CE + runner
│   ├── 04-workstation.yml               # Dev workstation + Docker
│   ├── 05-k3s.yml                       # K3s single-node
│   └── 06-app-deploy.yml               # Flask app CI/CD + K8s deploy
└── roles/
    ├── vm_provision/                    # Proxmox VM lifecycle (create/destroy)
    ├── common/                          # Hostname, /etc/hosts, DNS resolver, packages
    ├── router/                          # Netplan dual-NIC, nftables NAT, sysctl
    ├── bind9/                           # BIND9 zones, validation, service
    ├── gitlab/                          # GitLab omnibus, user creation, runner
    ├── workstation/                     # Docker CE, developer user, SSH key upload
    ├── k3s/                             # K3s install, registry config, kubeconfig
    └── flask_app/                       # Sample app, GitLab CI, K8s deployment
```

## Verification

After a full run, confirm the lab is working:

```bash
# DNS resolution
dig @10.20.30.250 gitlab.test.local +short        # → 10.20.30.100

# Internet via NAT (from any private VM)
ping -c 2 8.8.8.8

# GitLab UI
curl -s http://gitlab.test.local/users/sign_in     # → HTML login page

# Container Registry
curl http://gitlab.test.local:5050/v2/              # → {}

# K3s cluster
kubectl get nodes                                    # → 1 node, Ready

# Flask word service
curl http://k3s.test.local:30500/                   # → {"word": "...", "hostname": "..."}
```

## Network Details

| Parameter | Value |
|---|---|
| Domain | `test.local` |
| Subnet | `10.20.30.0/24` |
| Gateway | `10.20.30.1` (router) |
| DNS | `10.20.30.250` |
| Private bridge | `vmbr1` |
| Internet bridge | `vmbr0` |

## Notes

- All traffic from the private subnet exits via the router's NAT masquerade.
- GitLab and the Container Registry run over HTTP (lab-only; not production-safe).
- K3s is configured with `insecure_skip_verify` for the GitLab registry mirror.
- The vault password is required for any playbook run (`--ask-vault-pass` or a vault password file).
- VM IDs 110–114 are used; adjust in `host_vars` if they conflict with existing VMs.
- First-boot cloud-init networking is rendered as a custom `network-config` snippet matched by NIC MAC address, so it does not depend on guest interface names like `eth0` vs `ens18`.
- Single-NIC VMs default to static first-boot addressing from inventory. If you want DHCP during initial provisioning, set `vm_provision_single_nic_bootproto: dhcp` for that host or group and make sure `ansible_host` still resolves to the address Ansible should use.
- SSH access to `10.20.30.0/24` defaults to direct connections. If your controller cannot route to that subnet, set `lab_ssh_proxy_jump` in `inventories/lab/group_vars/private_subnet.yml` or a higher-precedence inventory file to something like `root@YOUR_PROXMOX_LAN_IP`.
