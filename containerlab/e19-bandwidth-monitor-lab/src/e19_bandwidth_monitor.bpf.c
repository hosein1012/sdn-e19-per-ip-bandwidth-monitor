#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define ETH_P_IP   0x0800
#define ETH_P_IPV6 0x86DD

struct ipv6_key {
    __u8 addr[16];
};

struct ipv6hdr_min {
    __u32 ver_tc_flow;
    __u16 payload_len;
    __u8 nexthdr;
    __u8 hop_limit;
    __u8 saddr[16];
    __u8 daddr[16];
};

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, __u64);
} ipv4_bytes SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, struct ipv6_key);
    __type(value, __u64);
} ipv6_bytes SEC(".maps");

SEC("xdp")
int xdp_bandwidth_monitor(struct xdp_md *ctx)
{
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;

    struct ethhdr *eth = data;

    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;

    __u16 eth_proto = bpf_ntohs(eth->h_proto);
    __u64 packet_len = data_end - data;

    if (eth_proto == ETH_P_IP) {
        struct iphdr *ip = (void *)(eth + 1);

        if ((void *)(ip + 1) > data_end)
            return XDP_PASS;

        __u32 src_ip = ip->saddr;
        __u64 initial_value = packet_len;

        __u64 *stored_bytes;
        stored_bytes = bpf_map_lookup_elem(&ipv4_bytes, &src_ip);

        if (stored_bytes) {
            __sync_fetch_and_add(stored_bytes, packet_len);
        } else {
            bpf_map_update_elem(&ipv4_bytes, &src_ip, &initial_value, BPF_ANY);
        }

        return XDP_PASS;
    }

    if (eth_proto == ETH_P_IPV6) {
        struct ipv6hdr_min *ip6 = (void *)(eth + 1);

        if ((void *)(ip6 + 1) > data_end)
            return XDP_PASS;

        struct ipv6_key src_ip6 = {};
        __builtin_memcpy(src_ip6.addr, ip6->saddr, 16);

        __u64 initial_value = packet_len;

        __u64 *stored_bytes;
        stored_bytes = bpf_map_lookup_elem(&ipv6_bytes, &src_ip6);

        if (stored_bytes) {
            __sync_fetch_and_add(stored_bytes, packet_len);
        } else {
            bpf_map_update_elem(&ipv6_bytes, &src_ip6, &initial_value, BPF_ANY);
        }

        return XDP_PASS;
    }

    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
