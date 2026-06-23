#!/usr/bin/env bash
# uninstall.sh — Remove symlinks/wrappers installed by install.sh (macOS + Linux).
# Runtime data in ~/.thmes/ is NOT touched (delete manually if desired).
# Windows users: run  .\uninstall.ps1  instead.

set -euo pipefail
LOCAL_BIN="$HOME/.local/bin"

for script in dev-thmes dev-thmes-pro dev-thmes-daemon dev-thmes-web dev-gemma \
              dev-hermes-use dev-mlx-serve-gemma dev-mlx-serve-qwen dev-mlx-serve-qwen3 \
              gemma-pro gemma-daemon; do  # last two = legacy names, cleaned up too
  link="$LOCAL_BIN/$script"
  if [ -L "$link" ] || [ -f "$link" ]; then   # symlink OR generated wrapper
    rm "$link"
    echo "  ✗ removed: $link"
  fi
done

echo ""
echo "✓ Symlinks removed."
echo ""
echo "Runtime data preserved:"
echo "  ~/.thmes/                  (sessions, memory, agents, mcp.json)"
echo "  ~/.thmes-history           (input history)"
echo ""
echo "To wipe runtime data:  rm -rf ~/.thmes ~/.thmes-history"
