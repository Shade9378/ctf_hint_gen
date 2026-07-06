#!/usr/bin/env bash
set -euo pipefail

docker build -f Dockerfile.shell -t ctf-shell-env .

docker rm -f llm_shell 2>/dev/null || true

docker run -dit \
  --name llm_shell \
  -v "$PWD/llm_workspace" \
  ctf-shell-env

echo "llm_shell is running."
echo "Test with: docker exec llm_shell bash -lc 'ls -la /challenge'"