# E19 - Per-IP Bandwidth Monitor

This lab implements the E19 Software Networks final project.

The goal of the project is to monitor bandwidth usage per source IP address using an XDP/eBPF program.

## Implemented level

- Basic: Accumulate bytes per source IPv4 address.
- Intermediate: Implemented using `BPF_MAP_TYPE_LRU_PERCPU_HASH`.
- Advanced: Not implemented.

## Project idea

The XDP program is attached to the `eth1` interface of a Containerlab node.

For every incoming IPv4 packet, the program:

1. Parses the Ethernet header.
2. Checks if the packet is IPv4.
3. Parses the IPv4 header.
4. Reads the source IPv4 address.
5. Computes the packet length.
6. Updates a BPF map where the key is the source IPv4 address and the value is the byte counter.

The program always returns `XDP_PASS`, so packets are only monitored and are not dropped.

## Intermediate implementation

The Intermediate version uses a per-CPU LRU hash map:

`BPF_MAP_TYPE_LRU_PERCPU_HASH`

This means that each CPU keeps a separate byte counter for each source IPv4 address.

This avoids updating one shared counter from multiple CPUs and removes the need for atomic byte updates in the XDP program.

Example internal per-CPU counter layout:

`10.0.3.2 -> CPU0: 196 bytes, CPU1: 294 bytes, CPU2: 0 bytes, CPU3: 0 bytes`

The userspace script `tools/read_map.py` reads the per-CPU values, sums them, and prints the total bytes per source IP.

Example:

`196 + 294 + 0 + 0 = 490 bytes`

## Files

- `src/e19_bandwidth_monitor.bpf.c`
  - XDP/eBPF program.
  - Parses IPv4 packets.
  - Counts bytes per source IPv4 address.
  - Uses `BPF_MAP_TYPE_LRU_PERCPU_HASH`.

- `tools/read_map.py`
  - Reads the BPF map using `bpftool`.
  - Converts raw IPv4 keys into readable IPv4 addresses.
  - Sums per-CPU values.
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

- node1: `10.0.3.1/24`
- node2: `10.0.3.2/24`

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

## Generate test traffic

Send ICMP traffic from node2 to node1:

`docker exec clab-e19-bandwidth-monitor-lab-node2 bash -c 'ping -c 5 10.0.3.1'`

This generates IPv4 packets with source IP `10.0.3.2`.

## Read the bandwidth counters

Run:

`./tools/read_map.py`

Example output:

`Map ID   Source IP        Bytes`

`--------------------------------`

`-        10.0.3.2         490`

This means that node1 received 490 bytes from source IP `10.0.3.2`.

## Raw BPF map output

The raw per-CPU map output can be inspected with:

`docker exec clab-e19-bandwidth-monitor-lab-node1 bash -c 'bpftool map dump name src_ip_bytes'`

Example raw output:

`key: 10.0.3.2`

`CPU0: 196 bytes`

`CPU1: 294 bytes`

`CPU2: 0 bytes`

`CPU3: 0 bytes`

The userspace script sums these values and prints the total.

## Destroy the lab

From the lab directory:

`./destroy.sh`

This removes the Containerlab topology.

## Limitations

- The current implementation monitors IPv4 traffic only.
- IPv6 addresses are configured in the lab but are not counted by the XDP program.
- Advanced top-talker reporting and periodic counter reset are not implemented.

## Branches

- `multi-lab-structure`
  - Basic implementation.

- `e19-intermediate`
  - Intermediate implementation using `BPF_MAP_TYPE_LRU_PERCPU_HASH`.

