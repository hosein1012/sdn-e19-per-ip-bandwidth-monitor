#!/usr/bin/env python3

import argparse
import json
import socket
import struct
import subprocess
import sys


def int_to_ipv4_le(value: int) -> str:
    return socket.inet_ntoa(struct.pack("<I", value))


def normalize_counter(entry):
    if "value" in entry:
        value = entry["value"]

        if isinstance(value, int):
            return value

        if isinstance(value, list):
            total = 0
            for item in value:
                if isinstance(item, int):
                    total += item
                elif isinstance(item, dict) and "value" in item:
                    total += item["value"]
            return total

    if "values" in entry:
        total = 0
        for item in entry["values"]:
            if isinstance(item, dict) and "value" in item:
                total += item["value"]
        return total

    return None


def run_bpftool(container: str, map_name: str) -> str:
    cmd = [
        "docker", "exec", container,
        "bash", "-c",
        f"bpftool map dump name {map_name}"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("[ERROR] Failed to read BPF map.", file=sys.stderr)
        print(result.stderr.strip(), file=sys.stderr)
        sys.exit(result.returncode)

    return result.stdout


def extract_entries(bpftool_json):
    entries = []

    for item in bpftool_json:
        if "key" in item:
            total = normalize_counter(item)
            if total is not None:
                entries.append({
                    "map_id": None,
                    "key": item["key"],
                    "value": total,
                })

        elif "elements" in item:
            map_id = item.get("id", None)
            for element in item["elements"]:
                if "key" in element:
                    total = normalize_counter(element)
                    if total is not None:
                        entries.append({
                            "map_id": map_id,
                            "key": element["key"],
                            "value": total,
                        })

    return entries


def main():
    parser = argparse.ArgumentParser(
        description="Read E19 source-IP byte counters from the BPF map."
    )

    parser.add_argument(
        "--container",
        default="clab-e19-bandwidth-monitor-lab-node1",
        help="Container where bpftool should be executed."
    )

    parser.add_argument(
        "--map",
        default="src_ip_bytes",
        help="BPF map name."
    )

    args = parser.parse_args()

    raw_output = run_bpftool(args.container, args.map)

    try:
        bpftool_json = json.loads(raw_output)
    except json.JSONDecodeError:
        print("[ERROR] Could not parse bpftool output as JSON.")
        print(raw_output)
        sys.exit(1)

    entries = extract_entries(bpftool_json)

    if not entries:
        print("No valid IP byte counters found.")
        return

    print("Map ID   Source IP        Bytes")
    print("--------------------------------")

    for entry in entries:
        map_id = entry["map_id"]
        src_ip_raw = entry["key"]
        total_bytes = entry["value"]

        src_ip = int_to_ipv4_le(src_ip_raw)
        map_id_text = str(map_id) if map_id is not None else "-"

        print(f"{map_id_text:<8} {src_ip:<16} {total_bytes}")


if __name__ == "__main__":
    main()
