# Sweden vs. Germany Energy Market Analysis

A modular, portfolio-grade DA project comparing Swedish (SCB) and German (SMARD/Destatis)
energy price & generation data, anchored on the day-ahead vs. intraday price divergence story.

**Full background/rationale:** see `PROJECT_PLAN.md` (condensed from the original project brief —
that's your source of truth for *why* each piece exists).

**Live task tracking:** see `TASKS.md` — check things off there as we go so we always know where
we left off, even across sessions.

---

## How this workspace is organized

Each `phaseN_*` folder is a self-contained step. You should be able to work through them in
order, and each one produces something runnable/showable on its own — nothing depends on a
later phase existing yet.

```
energy-project/
├── README.md              ← you are here
├── PROJECT_PLAN.md         ← condensed plan, options, and reasoning
├── TASKS.md                ← checklist, update as we go
├── requirements.txt
├── .env.example             ← copy to .env for the ENTSO-E key (Phase 6 only)
├── data/                    ← local data lands here (gitignored)
├── notebooks/               ← exploratory/narrative notebooks (Phase 4-5)
├── phase1_explore/          ← touch both APIs once, get one chart each
├── phase2_single_country/   ← first real analysis, single country
├── phase3_etl/               ← formalize into fetch → transform → load + SQLite
│   └── etl/
├── phase4_comparative/      ← SE vs DE questions, using the SQLite db
├── phase5_polish/            ← flagship Plotly view / Tableau piece
└── phase6_stretch/           ← ENTSO-E plug-in, scheduled pipeline (optional)
```

## Quick start

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Then open `phase1_explore/` and start with `fetch_scb.py` — that's the actual first step,
described in `TASKS.md`.

## Ground rules for keeping this sane

1. **Don't open Phase 3 until Phase 1 and 2 run.** The whole point of doing this in order is that
   each phase proves the previous mechanics work before you build structure on top of them.
2. **Stub files are stubs on purpose.** Each one has a docstring explaining what it needs to do
   and why, plus a `# TODO` where the real logic goes — that's the scope, not a full implementation
   to figure out from scratch.
3. **If something in the brief feels like scope creep, it's optional by design** — Phase 6 and the
   Tableau piece in Phase 5 are explicitly stretch goals. Core deliverable is Phases 1–4.
4. When you come back to this project after time away, read `TASKS.md` first — it'll tell you
   exactly what's done and what's next, so you're not re-deriving the plan from memory.
