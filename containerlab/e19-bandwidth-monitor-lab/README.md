# E19 — Per-IP Bandwidth Monitor

## Overview

This lab implements the E19 Software Networks final project: Per-IP Bandwidth Monitor using eBPF/XDP.

The XDP program is attached to a container interface and monitors incoming IPv4 packets. For each source IPv4 address, it accumulates the total number of bytes seen from that source.

Current implemented level:

- Basic: Accumulate bytes per source IPv4 address.
- Intermediate: Not implemented.
- Advanced: Not implemented.

IPv6 addresses are configured in the lab topology, but the current implementation monitors IPv4 traffic only.

## Architecture

The lab uses two Linux containers connected with a point-to-point eth1 link:

node1: 10.0.3.1/24, fc00:3::1/64
node2: 10.0.3.2/24, fc00:3::2/64

Typical test setup:

node2 -> node1 traffic
XDP attached on node1:eth1

This monitors incoming traffic on node1 and counts bytes by source IPv4 address.

## Files

Main files:

- Dockerfile
- e19-bandwidth-monitor-lab.clab.yml
- deploy.sh
- destroy.sh
- configs/node1.cfg
- configs/node2.cfg
- bin/entrypoint.sh
- src/Makefile
- src/e19_bandwidth_monitor.bpf.c
- tools/read_map.py

File roles:

- src/e19_bandwidth_monitor.bpf.c: XDP/eBPF source code.
- src/Makefile: builds the BPF object file.
- tools/read_map.py: reads the BPF map and prints readable IPv4 addresses.
- e19-bandwidth-monitor-lab.clab.yml: containerlab topology.
- deploy.sh / destroy.sh: wrapper scripts for deploying and destroying the lab.

## BPF Map

The program uses a BPF hash map named src_ip_bytes.

Map structure:

key   = source IPv4 address
value = total bytes received from that source

Example:

10.0.3.2 -> 490 bytes

## Build

From the lab source directory:

cd containerlab/e19-bandwidth-monitor-lab/src
make

This compiles:

e19_bandwidth_monitor.bpf.c -> e19_bandwidth_monitor.bpf.o

The generated files *.bpf.o and vmlinux.h are build artifacts and should not be committed.

## Deploy the Lab

From the lab directory:

cd containerlab/e19-bandwidth-monitor-lab
./deploy.sh

This creates two containers:

clab-e19-bandwidth-monitor-lab-node1
clab-e19-bandwidth-monitor-lab-node2

## Attach the XDP Program

Attach the XDP program on node1:eth1:

docker exec clab-e19-bandwidth-monitor-lab-node1 bash -c 'ip link set dev eth1 xdp obj /work/bpf/e19_bandwidth_monitor.bpf.o sec xdp'

Verify that XDP is attached:

docker exec clab-e19-bandwidth-monitor-lab-node1 bash -c 'bpftool net show dev eth1'

Expected output includes an xdp section with a program ID.

## Generate IPv4 Traffic

Send traffic from node2 to node1:

docker exec clab-e19-bandwidth-monitor-lab-node2 bash -c 'ping -c 5 10.0.3.1'

The XDP program attached on node1:eth1 sees these incoming packets and updates the byte counter for source IP 10.0.3.2.

## Read the BPF Map

Raw map output with bpftool:

docker exec clab-e19-bandwidth-monitor-lab-node1 bash -c 'bpftool map dump name src_ip_bytes'

The raw key is shown as an integer because IPv4 addresses are stored as __u32.

For readable output, use the helper script:

./tools/read_map.py

Example output:

Map ID   Source IP        Bytes
--------------------------------
67       10.0.3.2         490

The script converts the raw integer key into dotted IPv4 format.

## Optional: Monitor the Other Direction

The same XDP program can also be attached to node2:eth1:

docker exec clab-e19-bandwidth-monitor-lab-node2 bash -c 'ip link set dev eth1 xdp obj /work/bpf/e19_bandwidth_monitor.bpf.o sec xdp'

Then send traffic from node1 to node2:

docker exec clab-e19-bandwidth-monitor-lab-node1 bash -c 'ping -c 5 10.0.3.2'

Read counters from node2:

./tools/read_map.py --container clab-e19-bandwidth-monitor-lab-node2

## Detach XDP

Detach the XDP program from node1:eth1:

docker exec clab-e19-bandwidth-monitor-lab-node1 bash -c 'ip link set dev eth1 xdp off'

If XDP was also attached on node2:

docker exec clab-e19-bandwidth-monitor-lab-node2 bash -c 'ip link set dev eth1 xdp off'

## Destroy the Lab

./destroy.sh

This removes the containers and containerlab runtime files for this lab.

## Notes

- The implementation currently monitors IPv4 source addresses only.
- IPv6 addresses are configured in the topology but are not counted by the current XDP program.
- The program returns XDP_PASS, so packets are monitored but not dropped or modified.
- The map is not pinned under /sys/fs/bpf; it is accessed by name using bpftool.
- The current implementation corresponds to the Basic requirement of E19.
