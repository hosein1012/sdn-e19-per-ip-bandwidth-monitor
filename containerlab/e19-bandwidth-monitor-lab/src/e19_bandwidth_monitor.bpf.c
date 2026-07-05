#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define ETH_P_IP 0x0800

struct {
    __uint(type, BPF_MAP_TYPE_LRU_PERCPU_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, __u64);
} src_ip_bytes SEC(".maps");

SEC("xdp")
int xdp_bandwidth_monitor(struct xdp_md *ctx)
{
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;

    struct ethhdr *eth = data;

    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;

    if (bpf_ntohs(eth->h_proto) != ETH_P_IP)
        return XDP_PASS;

    struct iphdr *ip = (void *)(eth + 1);

    if ((void *)(ip + 1) > data_end)
        return XDP_PASS;

    __u32 src_ip = ip->saddr;
    __u64 packet_len = data_end - data;

    __u64 *stored_bytes;
    __u64 initial_value = packet_len;

    stored_bytes = bpf_map_lookup_elem(&src_ip_bytes, &src_ip);

    if (stored_bytes) {
        *stored_bytes += packet_len;
    } else {
        bpf_map_update_elem(&src_ip_bytes, &src_ip, &initial_value, BPF_ANY);
    }

    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
