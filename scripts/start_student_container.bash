#!/usr/bin/env bash
set -euo pipefail

SESSION_ID="$(date +"%m-%d-%Y_%H-%M-%S")"

IMAGE_NAME="ctf-shell-env"
CONTAINER_NAME="student_shell"

SOURCE_DIR="$PWD/data/challenges/public"
WORKSPACE_DIR="$PWD/.runtime/sessions/$SESSION_ID/student_workspace"

docker build -f Dockerfile.shell -t "$IMAGE_NAME" .

mkdir -p "$WORKSPACE_DIR"
cp -r "$SOURCE_DIR/." "$WORKSPACE_DIR/"

docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

docker run -dit \
  --name "$CONTAINER_NAME" \
  -v "$WORKSPACE_DIR:/challenge" \
  "$IMAGE_NAME"

echo "student_shell is running."
echo "Session: $SESSION_ID"
echo "Workspace: $WORKSPACE_DIR"
echo "Test with: docker exec student_shell bash -lc 'ls -la /challenge'"