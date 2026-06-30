#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="ctf-shell-env"

docker build -f Dockerfile.student_shell -t "$IMAGE_NAME" .

docker rm -f llm_shell 2>/dev/null || true

docker run -dit \
  --name llm_shell \
  -v "$PWD/llm_workspace" \
  "$IMAGE_NAME"

echo "llm_shell is running."
echo "Test with: docker exec llm_shell bash -lc 'ls -la /challenge'"