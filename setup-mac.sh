#!/usr/bin/env bash
# setup-mac.sh — One-shot setup for THMES on any Mac (Ollama backend).
# Safe to re-run: skips steps that are already done.
#
# What this does:
#   1. Auto-detects Python 3.10+ and creates ~/.thmes-env venv
#   2. Installs required packages into the venv
#   3. Scans Ollama for available models → interactive picker → sets default
#   4. Writes ~/.local/bin/thmes wrapper (uses venv + chosen model)
#   5. Adds ~/.local/bin to PATH in ~/.zshrc if missing

set -euo pipefail

VENV="$HOME/.thmes-env"
BIN="$HOME/.local/bin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER="$BIN/thmes"
ZSHRC="$HOME/.zshrc"
OLLAMA_HOST="${THMES_OLLAMA_HOST:-http://127.0.0.1:11434}"

echo "=== THMES setup ==="
echo "Project : $SCRIPT_DIR"
echo "Venv    : $VENV"
echo "Wrapper : $WRAPPER"
echo ""

# ── Step 1: venv ──────────────────────────────────────────────────────────────
if [ -x "$VENV/bin/python" ]; then
  echo "✓ venv already exists — skipping create"
else
  PYTHON=""
  for candidate in \
      python3.13 python3.12 python3.11 python3.10 python3 \
      /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 \
      /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3.10 \
      /opt/homebrew/bin/python3 /usr/local/bin/python3 \
      /usr/bin/python3; do
    if command -v "$candidate" &>/dev/null 2>&1; then
      ver=$("$candidate" -c "import sys; print(sys.version_info >= (3,10))" 2>/dev/null || echo False)
      if [ "$ver" = "True" ]; then
        PYTHON=$(command -v "$candidate")
        break
      fi
    fi
  done

  if [ -z "$PYTHON" ]; then
    echo "✗ Python 3.10+ not found. Install via: brew install python3"
    exit 1
  fi

  echo "→ Using Python: $PYTHON ($("$PYTHON" --version))"
  echo "→ Creating venv at $VENV ..."
  "$PYTHON" -m venv "$VENV"
  echo "  done"
fi

echo "→ Ensuring required packages are installed ..."
"$VENV/bin/pip" install --quiet rich prompt_toolkit ddgs
"$VENV/bin/python" -c "import rich, prompt_toolkit, ddgs" \
  && echo "✓ packages ok (rich, prompt_toolkit, ddgs)" \
  || { echo "✗ package install failed"; exit 1; }

# ── Step 2: scan Ollama + model picker ────────────────────────────────────────
echo ""
echo "→ Scanning Ollama at $OLLAMA_HOST ..."

DEFAULT_MODEL="ol:gemma4:e4b"

OLLAMA_JSON=""
if command -v curl &>/dev/null; then
  OLLAMA_JSON=$(curl -sf --max-time 3 "$OLLAMA_HOST/api/tags" 2>/dev/null || true)
fi

if [ -z "$OLLAMA_JSON" ]; then
  echo "  ⚠ Ollama not reachable — using default model: $DEFAULT_MODEL"
  echo "    Start Ollama first: open Ollama.app  or  ollama serve"
else
  # Parse model list with python (write JSON to temp file to avoid stdin conflict)
  _TMP_JSON=$(mktemp)
  printf '%s' "$OLLAMA_JSON" > "$_TMP_JSON"
  MODEL_LIST=$("$VENV/bin/python" - "$_TMP_JSON" <<'PYEOF'
import sys, json

with open(sys.argv[1]) as f:
    data = json.load(f)
models = data.get("models", [])
if not models:
    sys.exit(0)
lines = []
for m in sorted(models, key=lambda x: x.get("name", "")):
    name = m.get("name") or m.get("model", "")
    size_gb = (m.get("size") or 0) / 1e9
    params  = (m.get("details") or {}).get("parameter_size", "")
    family  = (m.get("details") or {}).get("family", "")
    lines.append(f"ol:{name}\t{size_gb:.1f}GB\t{params}\t{family}")
print("\n".join(lines))
PYEOF
  )
  rm -f "$_TMP_JSON"

  if [ -z "$MODEL_LIST" ]; then
    echo "  ⚠ No models found in Ollama — using default: $DEFAULT_MODEL"
    echo "    Pull a model first: ollama pull gemma4:e4b"
  else
    echo ""
    echo "  Available models:"
    echo ""

    # Build indexed array
    i=1
    declare -a MODEL_KEYS=()
    while IFS=$'\t' read -r alias size params family; do
      printf "  %3d)  %-42s %8s  %-8s  %s\n" "$i" "$alias" "$size" "$params" "$family"
      MODEL_KEYS+=("$alias")
      i=$((i + 1))
    done <<< "$MODEL_LIST"

    # Find recommended default (prefer gemma4:e4b or first)
    RECOMMENDED=""
    for k in "${MODEL_KEYS[@]}"; do
      if [[ "$k" == *"gemma4:e4b"* ]]; then
        RECOMMENDED="$k"; break
      fi
    done
    [ -z "$RECOMMENDED" ] && RECOMMENDED="${MODEL_KEYS[0]}"

    echo ""
    if [ -t 0 ] || [ -e /dev/tty ]; then
      printf "  Select default model [Enter = %s]: " "$RECOMMENDED"
      read -r CHOICE </dev/tty 2>/dev/null || CHOICE=""
    else
      echo "  (non-interactive — using recommended: $RECOMMENDED)"
      CHOICE=""
    fi

    if [ -z "$CHOICE" ]; then
      DEFAULT_MODEL="$RECOMMENDED"
    elif [[ "$CHOICE" =~ ^[0-9]+$ ]]; then
      idx=$((CHOICE - 1))
      if [ "$idx" -ge 0 ] && [ "$idx" -lt "${#MODEL_KEYS[@]}" ]; then
        DEFAULT_MODEL="${MODEL_KEYS[$idx]}"
      else
        echo "  ✗ invalid number — using $RECOMMENDED"
        DEFAULT_MODEL="$RECOMMENDED"
      fi
    else
      # Accept bare tag (e.g. "qwen3:8b" → "ol:qwen3:8b")
      if [[ "$CHOICE" != ol:* ]]; then CHOICE="ol:$CHOICE"; fi
      DEFAULT_MODEL="$CHOICE"
    fi

    echo "  ✓ default model set to: $DEFAULT_MODEL"
  fi
fi

# ── Step 3: wrapper script ────────────────────────────────────────────────────
# IMPORTANT: remove any existing symlink first to avoid overwriting source files
mkdir -p "$BIN"
[ -L "$WRAPPER" ] && rm "$WRAPPER"
[ -f "$WRAPPER" ] && mv "$WRAPPER" "$WRAPPER.bak-$(date +%Y%m%d-%H%M%S)"

cat > "$WRAPPER" << WRAPPER_EOF
#!/usr/bin/env bash
# thmes wrapper — generated by setup-mac.sh
# Default model: ${DEFAULT_MODEL}  (override: THMES_MODEL=ol:<tag> thmes)
# THMES_MODEL sets the default model.
export THMES_MODEL="\${THMES_MODEL:-${DEFAULT_MODEL}}"
exec "${VENV}/bin/python" "${SCRIPT_DIR}/bin/thmes" "\$@"
WRAPPER_EOF
chmod +x "$WRAPPER"
echo "✓ wrapper written → $WRAPPER"

# ── Step 4: PATH in ~/.zshrc ──────────────────────────────────────────────────
PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
if grep -qF '.local/bin' "$ZSHRC" 2>/dev/null; then
  echo "✓ ~/.local/bin already in $ZSHRC — skipping"
else
  printf '\n# thmes: local bin\n%s\n' "$PATH_LINE" >> "$ZSHRC"
  echo "✓ added PATH entry to $ZSHRC"
fi

# ── Step 5: skills directory check ───────────────────────────────────────────
SKILLS_DIR="$HOME/.claude/skills"
PROJ_SKILLS="$SCRIPT_DIR/skills"
if [ -d "$SKILLS_DIR" ] && [ "$(ls "$SKILLS_DIR" 2>/dev/null | wc -l)" -gt 0 ]; then
  skill_count=$(ls "$SKILLS_DIR" | wc -l | tr -d ' ')
  echo "✓ skills found at $SKILLS_DIR ($skill_count skills)"
elif [ -d "$PROJ_SKILLS" ] && [ "$(ls "$PROJ_SKILLS" 2>/dev/null | wc -l)" -gt 0 ]; then
  skill_count=$(ls "$PROJ_SKILLS" | wc -l | tr -d ' ')
  echo "✓ skills found at $PROJ_SKILLS ($skill_count skills, project-local)"
else
  echo ""
  echo "⚠ No skills found — thmes will show '0 skills'"
  echo "  Set env: THMES_SKILLS_DIR=/path/to/skills thmes"
fi

# ── Smoke test ────────────────────────────────────────────────────────────────
echo ""
echo "→ Smoke test ..."
"$WRAPPER" /dev/null 2>&1 | head -3 || true
echo ""

echo "=== Setup complete ==="
echo ""
echo "Open a new terminal tab, then run:"
echo "  thmes"
echo ""
echo "Default model: $DEFAULT_MODEL"
echo "Override:      THMES_MODEL=ol:qwen3:8b thmes"
