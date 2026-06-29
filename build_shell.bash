#!/usr/bin/env bash
set -e

docker build -f Dockerfile.student_shell -t student-shell-env .

docker rm -f student_shell 2>/dev/null || true

docker run -dit \
  --name student_shell \
  -v "$PWD/data/challenges/demo:/challenge" \
  student-shell-env

echo "student_shell is running."
echo "Test with: docker exec student_shell bash -lc 'ls -la /challenge'"