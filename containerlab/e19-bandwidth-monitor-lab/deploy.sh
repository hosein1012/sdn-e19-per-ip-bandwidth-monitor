#!/bin/bash
LAB_NAME="e19-bandwidth-monitor-lab"
IMAGE="clab-softnet-e19-bandwidth:latest"
TOPOLOGY="e19-bandwidth-monitor-lab.clab.yml"
NODES="node1 node2"
LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${LAB_DIR}/../lib/deploy.sh"
