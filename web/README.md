# THMES Web Terminal

A browser front-end for the **`thmes` CLI** — not a model API client. It spawns the
real `thmes` REPL in a pseudo-terminal (PTY) and bridges it to [xterm.js](https://xtermjs.org/)
over a WebSocket, so you get the full CLI (smart routing, tools, sessions, slash
commands, relay, …) in a browser tab. Everything runs locally; the session never
leaves the machine.

```
Browser (xterm.js) ──WebSocket──▶ web/server.py ──pty.spawn──▶ thmes (real REPL)
        ▲                                                          │
        └──────────────── bytes streamed both ways ◀──────────────┘
```

## Run

```bash
pip install websockets        # one-time (only dependency)
thmes-web                     # or: python3 web/server.py
# open http://localhost:8765
```

At the model picker, press **Enter** to take the default (or type a number), then use
`thmes` exactly as in the terminal — `/help`, `/agent`, `/relay`, etc.

## Config (env)

| Var | Default | Meaning |
|---|---|---|
| `THMES_WEB_HTTP_PORT` | `8765` | port for the static page |
| `THMES_WEB_WS_PORT` | `8766` | PTY/WebSocket bridge port (must match `index.html`) |
| `THMES_CMD` | auto | command that launches the CLI — set this if the `thmes` shebang Python isn't on this host, e.g. `THMES_CMD="$HOME/.thmes-env/bin/python /path/to/repo/bin/thmes"` |
| `THMES_MODEL` | — | forwarded to `thmes` (e.g. `ol:gemma4:e4b`) |
| `THMES_WEB_PYTHON` | `python3` | interpreter `thmes-web` uses (needs `websockets`) |

`thmes-web` resolves the CLI portably: `$THMES_CMD` → `thmes` on `PATH` → `../bin/thmes`.

## Origin

`index.html` was written by **thmes itself** in relay mode (cloud=brain, this
machine=hands) during development; `server.py` was then productionised for the repo
(portable paths + a single-reader PTY bridge — no duplicate reader tasks). The flow
was verified end-to-end in a headless browser (xterm renders, the real banner streams
in, typed `/help` executes in the live REPL).
