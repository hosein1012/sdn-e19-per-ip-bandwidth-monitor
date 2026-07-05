#!/usr/bin/env python3

import argparse
import json
import socket
import struct
import subprocess
import sys


def byte_item_to_int(item):
    if isinstance(item, int):
        return item

    if isinstance(item, str):
        item = item.strip()

        if item.startswith("0x"):
            return int(item, 16)

        return int(item, 16)

    raise ValueError(f"Unsupported byte item: {item}")


def byte_list_to_bytes(items):
    return bytes(byte_item_to_int(item) for item in items)


def value_to_int(value):
    if isinstance(value, int):
        return value

    if isinstance(value, list):
        raw = byte_list_to_bytes(value)

        if len(raw) == 8:
            return struct.unpack("<Q", raw)[0]

        if len(raw) == 4:
            return struct.unpack("<I", raw)[0]

        return int.from_bytes(raw, byteorder="little")

    if isinstance(value, dict):
        if "value" in value:
            return value_to_int(value["value"])

    return value


def ipv4_key_to_text(key) -> str:
    if isinstance(key, int):
        return socket.inet_ntoa(struct.pack("<I", key))

    if isinstance(key, list):
        return socket.inet_ntoa(byte_list_to_bytes(key))

    if isinstance(key, dict):
        if "addr" in key:
            return socket.inet_ntoa(byte_list_to_bytes(key["addr"]))

        values = list(key.values())
        if len(values) == 4:
            return socket.inet_ntoa(byte_list_to_bytes(values))

    return str(key)


def ipv6_key_to_text(key) -> str:
    if isinstance(key, dict) and "addr" in key:
        raw_bytes = byte_list_to_bytes(key["addr"])
    elif isinstance(key, list):
        raw_bytes = byte_list_to_bytes(key)
    else:
        return str(key)

    return socket.inet_ntop(socket.AF_INET6, raw_bytes)


def run_bpftool(container: str, map_name: str):
    cmd = [
        "docker", "exec", container,
        "bash", "-c",
        f"bpftool -j map dump name {map_name}"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[ERROR] Failed to read BPF map: {map_name}", file=sys.stderr)
        print(result.stderr.strip(), file=sys.stderr)
        sys.exit(result.returncode)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"[ERROR] Could not parse bpftool output for map: {map_name}")
        print(result.stdout)
        sys.exit(1)


def extract_entries(bpftool_json):
    entries = []

    for item in bpftool_json:
        if "key" in item and "value" in item:
            entries.append({
                "map_id": None,
                "key": item["key"],
                "value": value_to_int(item["value"]),
            })

        elif "elements" in item:
            map_id = item.get("id", None)
            for element in item["elements"]:
                if "key" in element and "value" in element:
                    entries.append({
                        "map_id": map_id,
                        "key": element["key"],
                        "value": value_to_int(element["value"]),
                    })

    return entries


def print_ipv4_entries(container: str):
    entries = extract_entries(run_bpftool(container, "ipv4_bytes"))

    print("IPv4 counters")
    print("Map ID   Source IPv4      Bytes")
    print("--------------------------------")

    if not entries:
        print("No IPv4 counters found.")
        print()
        return

    for entry in entries:
        map_id = entry["map_id"]
        src_ip = ipv4_key_to_text(entry["key"])
        total_bytes = entry["value"]
        map_id_text = str(map_id) if map_id is not None else "-"

        print(f"{map_id_text:<8} {src_ip:<16} {total_bytes}")

    print()


def print_ipv6_entries(container: str):
    entries = extract_entries(run_bpftool(container, "ipv6_bytes"))

    print("IPv6 counters")
    print("Map ID   Source IPv6                Bytes")
    print("------------------------------------------")

    if not entries:
        print("No IPv6 counters found.")
        print()
        return

    for entry in entries:
        map_id = entry["map_id"]
        src_ip = ipv6_key_to_text(entry["key"])
        total_bytes = entry["value"]
        map_id_text = str(map_id) if map_id is not None else "-"

        print(f"{map_id_text:<8} {src_ip:<26} {total_bytes}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Read E19 IPv4 and IPv6 source-IP byte counters from BPF maps."
    )

    parser.add_argument(
        "--container",
        default="clab-e19-bandwidth-monitor-lab-node1",
        help="Container where bpftool should be executed."
    )

    args = parser.parse_args()

    print_ipv4_entries(args.container)
    print_ipv6_entries(args.container)


if __name__ == "__main__":
    main()
