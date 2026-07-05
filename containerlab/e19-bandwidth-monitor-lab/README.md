# E19 - Per-IP Bandwidth Monitor

This lab implements the E19 Software Networks final project.

The goal of the project is to monitor bandwidth usage per source IP address using an XDP/eBPF program.

## Implemented level

- Basic: Implemented for both IPv4 and IPv6 source addresses.
- Intermediate: Available on branch `e19-intermediate`.
- Advanced: Not implemented.

## Project idea

The XDP program is attached to the `eth1` interface of a Containerlab node.

For every incoming IPv4 or IPv6 packet, the program:

1. Parses the Ethernet header.
2. Checks if the packet is IPv4 or IPv6.
3. Reads the source IP address.
4. Computes the packet length.
5. Updates a BPF map where the key is the source IP address and the value is the byte counter.

The program always returns `XDP_PASS`, so packets are only monitored and are not dropped.

## IPv4 and IPv6 support

The Basic implementation supports both IPv4 and IPv6 traffic.

Two BPF maps are used:

- `ipv4_bytes`
  - Key: source IPv4 address
  - Value: byte counter

- `ipv6_bytes`
  - Key: source IPv6 address
  - Value: byte counter

This keeps IPv4 and IPv6 counters separate and makes the userspace reader easier to understand.

## Files

- `src/e19_bandwidth_monitor.bpf.c`
  - XDP/eBPF program.
  - Parses Ethernet packets.
  - Counts bytes per source IPv4 address.
  - Counts bytes per source IPv6 address.
  - Uses BPF hash maps.

- `tools/read_map.py`
  - Reads the IPv4 and IPv6 BPF maps using `bpftool`.
  - Converts raw IPv4 and IPv6 keys into readable IP addresses.
  - Converts raw byte counters into integer byte values.
  - Prints total bytes per source IP.

- `e19-bandwidth-monitor-lab.clab.yml`
  - Containerlab topology.
  - Creates two Linux nodes connected through `eth1`.

- `configs/node1.cfg`
  - IP configuration for node1.

- `configs/node2.cfg`
  - IP configuration for node2.

- `deploy.sh`
  - Builds and deploys the Containerlab topology.

- `destroy.sh`
  - Destroys the Containerlab topology.

## Topology

The lab contains two Linux containers:

- node1:
  - IPv4: `10.0.3.1/24`
  - IPv6: `fc00:3::1/64`

- node2:
  - IPv4: `10.0.3.2/24`
  - IPv6: `fc00:3::2/64`

They are connected directly through `eth1`.

Traffic generated from node2 to node1 is monitored by attaching the XDP program to `node1:eth1`.

## Build

From the lab directory:

`cd containerlab/e19-bandwidth-monitor-lab`

Build the eBPF object:

`cd src`

`make clean`

`make`

`cd ..`

The build creates:

`src/e19_bandwidth_monitor.bpf.o`

## Deploy the lab

From the lab directory:

`./deploy.sh`

This creates the Containerlab topology and starts the two containers.

## Attach the XDP program

Attach the XDP program to `eth1` of node1:

`docker exec clab-e19-bandwidth-monitor-lab-node1 bash -c 'ip link set dev eth1 xdp obj /work/bpf/e19_bandwidth_monitor.bpf.o sec xdp'`

Check that the XDP program is attached:

`docker exec clab-e19-bandwidth-monitor-lab-node1 bash -c 'bpftool net show dev eth1'`

Expected output should show an XDP program attached to `eth1`.

## Generate IPv4 test traffic

Send IPv4 ICMP traffic from node2 to node1:

`docker exec clab-e19-bandwidth-monitor-lab-node2 bash -c 'ping -c 5 10.0.3.1'`

This generates IPv4 packets with source IP:

`10.0.3.2`

## Generate IPv6 test traffic

Send IPv6 ICMP traffic from node2 to node1:

`docker exec clab-e19-bandwidth-monitor-lab-node2 bash -c 'ping -6 -c 5 fc00:3::1'`

This generates IPv6 packets with source IP:

`fc00:3::2`

## Read the bandwidth counters

Run:

`./tools/read_map.py`

Example output:

`IPv4 counters`

`Map ID   Source IPv4      Bytes`

`--------------------------------`

`-        10.0.3.2         490`

`IPv6 counters`

`Map ID   Source IPv6                Bytes`

`------------------------------------------`

`-        fc00:3::2                  676`

This means that node1 received IPv4 traffic from `10.0.3.2` and IPv6 traffic from `fc00:3::2`.

## Raw BPF map inspection

IPv4 map:

`docker exec clab-e19-bandwidth-monitor-lab-node1 bash -c 'bpftool -j map dump name ipv4_bytes'`

IPv6 map:

`docker exec clab-e19-bandwidth-monitor-lab-node1 bash -c 'bpftool -j map dump name ipv6_bytes'`

The userspace script converts the raw keys and values into readable output.

## Destroy the lab

From the lab directory:

`./destroy.sh`

This removes the Containerlab topology.

## Limitations

- Basic IPv4 and IPv6 byte counting is implemented.
- Intermediate per-CPU LRU counting is available on branch `e19-intermediate`.
- Advanced top-talker reporting and periodic counter reset are not implemented in this branch.

## Branches

- `multi-lab-structure`
  - Basic IPv4-only implementation.

- `e19-basic-ipv6`
  - Basic implementation with IPv4 and IPv6 support.

- `e19-intermediate`
  - Intermediate implementation using `BPF_MAP_TYPE_LRU_PERCPU_HASH`.

