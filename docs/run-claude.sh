#!/usr/bin/env bash
set -euo pipefail
cat docs/prompts/execution-loop-system.md docs/prompts/current-task.md | claude
