# Easy CV

[English](README.md) | [简体中文](README.zh-CN.md)

AI resume editor: resume paper on the left, AI block rewrite on the right. Reuses a multi-agent backend (material extraction / resume generation / JD matching).

## Layout

```
easy-cv/
├── main.py                 # FastAPI entry (API + static frontend)
├── resume_agents/          # Backend package (agents / api / memory / domain)
├── frontend/               # React + Vite frontend
└── static/                 # Frontend build output
```

## Quick start

### 1) Backend

```bash
cd easy-cv
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
# Without OPENAI_API_KEY the service runs in mock mode for demos
python main.py
```

Open http://127.0.0.1:8002  
(Default port `8002`, override with `PORT`; avoids clashing with other local services on 8000.)

### 2) Frontend dev (HMR)

```bash
# Terminal A
cd easy-cv && RESUME_MOCK=1 python main.py

# Terminal B
cd easy-cv/frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 (proxied to backend 8002)

### 3) Production build

```bash
cd easy-cv/frontend && npm run build
cd .. && python main.py
```

## Core interactions

- Click a resume block → select it in the right-hand AI panel
- Quick / custom instructions → diff suggestions → apply / ignore
- Import `.txt/.md`, export Markdown / plain text / print PDF
- Material library extraction, domain-based full resume generation, JD match rewrite
- Desktop two-column layout; drawer-style right panel on narrow screens; print styles

## API (selected)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/meta` | Service mode mock/llm |
| POST | `/api/v1/resume/block-rewrite` | Block AI rewrite |
| POST | `/api/v1/materials` | Add material |
| POST | `/api/v1/resume/full` | Generate full resume |
| POST | `/api/v1/resume/match` | JD match and rewrite |
| GET | `/api/v1/domains` | Domain list |

## Design notes

Visual layout aligns with the *Resume AI Editor* design: brand color `#4b3fe3`, 48px top bar, left paper + 380px right AI panel, block hover/selected states, and diff cards.
