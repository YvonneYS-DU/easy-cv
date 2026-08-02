# Easy CV

[English](README.md) | [简体中文](README.zh-CN.md)

**Use AI to manage the full lifecycle of your resume** — from raw experience → living material library → tailored drafts for each role → export when you apply.

Easy CV is not “chat once, get a PDF”. It keeps **facts**, **phrasings**, and **versions** separate so the same real experience can be told differently for different jobs — without rewriting your life story from scratch every time.

---

## Who it is for

Anyone who:

- Has projects and jobs scattered in notes, chats, or old PDFs
- Applies to more than one direction (e.g. AI eng vs backend vs PM)
- Wants AI to **suggest** wording, while **you** decide what goes on the final resume
- Needs a repeatable loop: **collect → draft → target a JD → refine blocks → export**

---

## The resume lifecycle (what you actually do)

Think of four layers that grow together:

| Layer | What it is | Who owns edits |
|-------|------------|----------------|
| **Materials** | Structured facts from your real experience (tech stack, impact, context) | Written as facts; AI extracts & refines |
| **Resume paper** | The document you see and ship (blocks: contact, work, projects, skills…) | You edit anytime; AI only changes it when you **Apply** |
| **Application strategy** | “Same facts, different framing” for a target role | Grows when you accept AI rewrites |
| **Versions** | Snapshots you can restore after big AI changes | Auto + manual |

```text
  notes / chat / old resume
            │
            ▼
   ┌─────────────────┐
   │  Material library │  ← lasting fact base
   └────────┬────────┘
            │ generate / feed rewrite
            ▼
   ┌─────────────────┐     select block + instruction
   │  Resume paper    │◄──────────────────────────┐
   └────────┬────────┘                            │
            │ paste JD                            │ apply / ignore
            ▼                                     │
   ┌─────────────────┐     block AI suggestions ──┘
   │ JD match + gaps  │
   └────────┬────────┘
            │
            ▼
   strategy variants + versions → export MD / text / PDF
```

### 1) Capture experience into the material library

**You:** Paste a project write-up, job bullet dump, or notes into **素材 / JD → 提取素材**.  
Or start from the left library: **提交文件 / 项目，完成初始化**, upload `.txt` / `.md`, or import from the top bar.

**AI:** Turns messy text into structured materials (type, one-line summary, tags, tech stack, flexible fields). It prefers **keeping your full stack** rather than silently dropping tools.

**Why it matters:** Materials are your **fact base**. Later generation, block rewrite, and JD matching all pull from here so you don’t forget old projects when chasing a new title.

> Tip: Dump freely first. Clean storytelling happens on the paper and in strategy branches — not by deleting history from the library.

### 2) Build or open a resume on the paper

**You:**

- Open a sample resume, create a blank one, or import an existing draft
- Click any block on the center **paper**
- Edit fields directly (title, dates, bullets, skills…) — changes apply to the draft immediately

**AI:** Stays out of the way until you ask. Manual edit and AI suggestion are separate on purpose.

Layout:

- **Left** — resume library (multiple drafts by time / keyword / project)
- **Center** — the paper (what you will export)
- **Right** — AI assistant (**区块编辑** / **素材 / JD**)

### 3) Let AI improve one block at a time (suggest → you decide)

**You:** Select a block → type an instruction or use a quick chip, e.g.

- Rewrite for my current target role  
- Quantify impact  
- Pull in points I forgot from the material library  
- Polish but keep the tech stack  
- Shorten  

Then run **基于当前内容完善**. Review the **diff** (red = remove, green = add) → **应用** or **忽略**.

**AI:**

- Rewrites only the selected block  
- Uses recent chat on this resume, your **application strategy**, and **underused materials**  
- Never overwrites the paper until you click **应用**

**On Apply, the system also:**

- Saves a **resume version** (so you can roll back)  
- Records a **framing variant** under your strategy (“this experience, said this way, for that direction”)

That is the core habit: **small, reviewable AI edits**, not one opaque full rewrite.

### 4) Generate a full draft from materials (optional kickoff)

When the library has enough material:

1. Pick a **目标领域** (AI/ML, backend, frontend, data, PM, …)  
2. Click **用素材生成完整简历**

**AI** drafts a full resume aligned to that domain’s emphasis.  
**You** treat it as a strong first cut on the paper — then refine block by block.

> Generating full resume **replaces the current paper content**. Use **存版本** / version list if you want a safety net first.

### 5) Target a real job: JD match + gap mining

**You:** Fill **投递方向 / 目标岗位** (recommended), paste the job description, run **分析并挖掘**.

**AI returns:**

- Match score and gap notes  
- Keywords you already cover vs still missing  
- **Forgotten experiences** — materials that fit the JD but are weak or missing on the paper  
- Optional full **JD rewrite draft**

**You:**

- **应用 JD 改写稿** if the overall direction is right, **or**  
- Go block-by-block with the gap hints (usually safer)  
- Optionally **从 JD 匹配填入** ATS hidden keywords for export

Missing JD keywords can also gently update your strategy emphasis so the next block rewrite aims at the same target.

### 6) Grow “same facts, different phrasing” (application strategy)

You should not maintain five unrelated resumes by copy-paste.

Instead, Easy CV keeps an **application strategy** per direction:

- Same underlying projects and outcomes  
- Different **angle** and **phrasing** for AI eng vs backend vs PM, etc.  
- Variants accumulate when you **apply** block suggestions  

Next time you target a similar role, AI already knows how you successfully framed that project.

### 7) Versions, sessions, and memory

| Memory | Purpose |
|--------|---------|
| **Chat session** | Conversation + suggestions for this resume |
| **Block rewrite history** | What AI proposed for each block over time |
| **Resume versions** | Full snapshots (manual save, after generate, JD rewrite, or apply block) |
| **Strategies / variants** | Direction-specific phrasings, not full document clones |

Restore any version from the tools panel when an experiment goes wrong.

**Important:** The paper you edit is stored in the **browser** (resume library). Materials, sessions, versions, and strategies live in the **backend store**. Clearing site data drops local drafts; server memory may still remain (and the reverse if you wipe `.materials`).

### 8) Export when you are ready to apply

Open **导出**:

- **Markdown** / **plain text** for ATS or further editing  
- **打印 / PDF** via the browser print dialog  
- Optional **ATS hidden keywords** (near-invisible on paper / print; injected on export if enabled)

Use hidden keywords only for skills you truly have. Easy CV will not invent experience — but keyword stuffing is still on you.

---

## A practical weekly loop

1. **Dump** new work into materials the week it happens  
2. Keep one **master-ish paper** (or a few by track)  
3. For each application: set **target role** → paste **JD** → mine gaps  
4. Fix **2–5 blocks** with AI diffs; apply only what you believe  
5. **Save version**, export, submit  
6. Next similar JD reuses strategy variants instead of starting from zero  

---

## Run the app

### Demo in one process (no API key)

```bash
cd easy-cv
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
# No OPENAI_API_KEY → automatic mock mode (full UI walkthrough)
python main.py
```

Open http://127.0.0.1:8002  

Default port is `8002` (`PORT` to override). Top bar shows **Mock** or **AI**.

### Real model

Put `OPENAI_API_KEY` in `.env` (optional `LLM_MODEL`, default `gpt-4o-mini`).  
Unset `RESUME_MOCK` / set it to `0`. Restart — badge becomes **AI**.

### Frontend hot reload (optional)

```bash
# Terminal A
cd easy-cv && RESUME_MOCK=1 python main.py

# Terminal B
cd easy-cv/frontend && npm install && npm run dev
```

http://127.0.0.1:5173 (proxied to the API)

### Production-style static build

```bash
cd easy-cv/frontend && npm run build
cd .. && python main.py
```

---

## Design principles (so the lifecycle stays sane)

1. **Facts ≠ copy** — materials hold truth; the paper holds a story for a moment in time.  
2. **Suggest, don’t auto-commit** — block AI always goes through Apply / Ignore.  
3. **Prefer keeping stack** — tools and frameworks are hard-won; AI should not “clean them away”.  
4. **One life, many framings** — strategy variants beat maintaining N divergent resume files.  
5. **You ship the final voice** — always read the paper before export.

---

## Project layout (for contributors)

```
easy-cv/
├── main.py              # App entry (API + static UI)
├── resume_agents/       # Orchestrator, agents, memory, domain profiles
├── frontend/            # React + Vite UI
└── static/              # Built frontend assets
```

Under the hood: material extract/refine, section/full generation, JD match + forgotten-experience mining, block rewrite, sessions, versions, and application strategies. Day-to-day use is entirely through the UI above — you do not need the HTTP API to manage your resume lifecycle.
