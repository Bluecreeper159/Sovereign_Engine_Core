<div align="center">
  <img src="ui/assets/organism.png" width="300px" alt="Sovereign Engine">

  # SOVEREIGN ENGINE CORE

  **Autonomous Agent Runtime & Intelligence Desktop**

  [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
  [![Architecture](https://img.shields.io/badge/Architecture-Zero--Trust-red.svg)]()
  [![Status](https://img.shields.io/badge/Build-v0.1.0-success.svg)]()
  [![Engine](https://img.shields.io/badge/Telemetry-CortexDB-8a2be2.svg)]()

  *The conversation window is just an interface. The organism runs underneath.*
</div>

---

## Download

| Platform | File | Notes |
|---|---|---|
| Linux (any distro) | `Sovereign Engine-0.1.0.AppImage` | `chmod +x` and run |
| Debian / Ubuntu | `sovereign-engine_0.1.0_amd64.deb` | `sudo dpkg -i` |
| Source / All platforms | `Sovereign_Engine_Core_v0.1.0.zip` | `bash install.sh` |
| Windows | Coming soon | `install.bat` + `start.bat` ready |

> **Requires Python 3.11+** on your machine. The installer creates an isolated `.venv` automatically on first launch — nothing touches your system Python.

---

## Overview

The **Sovereign Engine Core** is a production-hardened, zero-trust autonomous agent runtime. It establishes a complete multi-LLM operating environment designed to run entirely on your local hardware.

Moving beyond generic chat wrappers, the Sovereign Engine functions as a living software organism — with decentralized daemon architecture, asynchronous memory ingestion, deterministic telemetry via the Execution Ledger, and zero-trust payload containment that prevents autonomous agents from irreversibly mutating your system.

---

## Quick Start

### Option A — AppImage (Linux, zero install)
```bash
chmod +x "Sovereign Engine-0.1.0.AppImage"
./"Sovereign Engine-0.1.0.AppImage"
```

### Option B — .deb (Debian / Ubuntu)
```bash
sudo dpkg -i sovereign-engine_0.1.0_amd64.deb
# Launch from your applications menu or:
sovereign-engine
```

### Option C — Source ZIP (any OS)
```bash
unzip Sovereign_Engine_Core_v0.1.0.zip
cd Sovereign_Engine_Core_v0.1.0/Sovereign_Engine_Core
bash install.sh
```

The installer creates a `.venv`, installs dependencies, generates a `.env` from the example, and boots the engine. On subsequent launches just run `bash start.sh`.

### Option D — Clone
```bash
git clone https://github.com/NovasPlace/Sovereign_Engine_Core.git
cd Sovereign_Engine_Core
bash install.sh
```

---

## Configuration

Open **Configuration Mode** in the UI to set API keys visually, or edit `.env` directly:

```env
# Add any combination — engine auto-routes based on task type
GEMINI_API_KEY="your-key"
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."

# Optional: point to a local Ollama instance
OLLAMA_HOST="http://127.0.0.1:11434"
```

> No keys? No problem. If Ollama is installed and running locally, the engine auto-detects and uses it with zero configuration.

---

## Smart Auto-Routing

When `ACTIVE_MODEL` is set to `auto` (default), the engine classifies each task and picks the best available model:

| Task Type | Detection | Model Priority |
|---|---|---|
| **Simple** | Casual prompts, short queries | Gemini Flash → GPT-4o-mini → Claude Haiku → Ollama |
| **Code** | `function`, `debug`, `python`, `sql`, `regex`, … | deepseek-coder (local) → GPT-4o → Gemini 2.5 Pro |
| **Heavy** | `analyze`, `architecture`, `research`, >60 words | Gemini 2.5 Pro → GPT-4o → Claude Opus → large local |

You can always override by selecting a specific model in the UI dropdown.

---

## Core Capabilities

### 🛡️ Zero-Trust Execution Containment
All agent file access is governed by a Workspace Jail. The `<read>` and `<write>` tools enforce `is_in_jail(path)` bounds with a 10MB OOM cap and symlink resolution blocks. Dangerous binaries (`rm`, `curl`, `pip`, etc.) require explicit operator approval before execution. **Safety == Trust.**

### 🔮 Multi-Provider LLM Routing
Natively supports **Gemini**, **OpenAI**, **Anthropic**, and local **Ollama** instances. The engine handles protocol normalization — agents hot-swap across providers transparently. Placeholder keys in `.env` are correctly ignored and never sent to APIs.

### 🧠 Cortex Memory Fabric
All context, decisions, and execution traces are journaled into a PostgreSQL schema (SQLite fallback on fresh installs). Features hot/warm session recovery, execution event ledger, and a fully decoupled async memory router that protects the UI thread from database latency.

### ⚡ Physical Execution — 9-Tool Protocol
The agent operates with real system agency via strict XML-tagged tools:

| Tool | What it does |
|---|---|
| `<execute>` | Spawns bash subprocesses (quarantine-gated) |
| `<read>` / `<write>` | Reads and rewrites source files (jail-bound, 10MB cap) |
| `<search>` | Live DuckDuckGo scraping to bypass knowledge cutoffs |
| `<fetch>` | Strips and reads raw website HTML |
| `<list_dir>` | Maps file system topologies |
| `<search_dir>` | Wildcard file discovery |
| `<grep>` | Deep text search inside codebases |
| `<system>` | OS telemetry — kernel info, datetime, hardware |

If a capability is missing, the agent writes and immediately executes custom scripts to extend itself.

### 🎨 Live Aesthetic Engine
Five visual themes swappable in real-time via CSS variables:
- **🟢 Bioforge Green** — terminal moss
- **🔵 Gemini Forge** — deep space indigo with azure particle fog
- **🟣 Neon Noir** — hyper-magenta and cyan outrun
- **❄️ Ghost Protocol** — clinical arctic blue on charcoal
- **🟠 Cyber Obsidian** — burnished amber corporate intelligence

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              sov_electron / main.js                     │
│     (Electron Desktop Wrapper — AppImage / .deb / .exe) │
│   First-run: auto-installs .venv and dependencies       │
└──────────────────────────┬──────────────────────────────┘
                           │ spawns start.sh
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    start.sh Guardian                    │
│   Kill → Verify → Launch backend → Watch health loop   │
└──────────────────────────┬──────────────────────────────┘
                           │ uvicorn
                           ▼
┌─────────────────────────────────────────────────────────┐
│                        main.py                          │
│         FastAPI Server + Smart Inference Router         │
│    Task classifier → model selector → provider call     │
└──────────────────────────┬──────────────────────────────┘
                           │
              ┌────────────┴─────────────┐
              ▼                          ▼
┌─────────────────────┐    ┌─────────────────────────────┐
│     memory_api.py   │    │        store.py             │
│  (Memory & Events)  │    │  PostgreSQL / SQLite fabric │
└─────────────────────┘    └─────────────────────────────┘
```

---

## Building Native Installers

```bash
cd sov_electron
npm install

# Linux
npm run dist:linux     # → dist/Sovereign Engine-x.x.x.AppImage + .deb

# Windows (run on Windows or CI)
npm run dist:win       # → dist/Sovereign Engine Setup x.x.x.exe

# Both
npm run dist:all
```

---

> **Axiom**: *The Execution Proof Law — the organism cannot claim success without raw execution output proving it. Confidence without evidence is hallucination.*
