# German Energy Market Analysis (Sweden + cross-border as stretch)

A modular, portfolio-grade DA project centered on Germany's day-ahead vs. intraday electricity
price divergence (via SMARD), with a Sweden module and cross-border flow story packaged
together as an optional stretch extension.

**Full background/rationale:** see `PROJECT_PLAN.md`.
**Live task tracking:** see `TASKS.md` — check things off there as we go.

---

## Why Germany-only for the core build

SMARD is the only source in play that has BOTH day-ahead and intraday wholesale prices for the
same market, keyless and free. That's what makes the spread analysis (the centerpiece) possible
at all. Sweden's SCB only has end-consumer prices, not exchange/spot prices — the actual Nordic
exchange (Nord Pool) has free day-ahead data but intraday is paywalled. So a symmetric SE vs. DE
spread analysis was never really available for free — building the whole core project around
Germany, where the full picture *is* free, is the honest move rather than forcing a half-real
comparison.

Sweden still has a real role — just later, and clearly optional:
- **SCB** (household prices, energy mix) + **Nord Pool day-ahead** (free, keyless) let you build
  a genuine cross-country comparison once the DE core is solid — aligning two very different
  data sources and doing an actual cross-comparison IS the interesting part for Sweden's
  inclusion, not a second spread analysis.
- **ENTSO-E** unlocks the cross-border flow story (does DE import Nordic hydro/wind during low
  German wind, and does that show up as price convergence). This needs data from more than one
  country to mean anything, so it's packaged with the Sweden module rather than standalone.

## How this workspace is organized

```
energy-project/
├── README.md
├── PROJECT_PLAN.md
├── TASKS.md
├── requirements.txt
├── .env.example                        ← ENTSO-E key, only needed for phase6
├── data/
├── notebooks/
├── phase1_smard_explore/               ← touch the SMARD API once, get one chart
├── phase2_de_analysis/                 ← first real DE analysis (volatility vs renewable share)
├── phase3_etl/                          ← formalize into fetch → transform → load + SQLite (DE)
│   └── etl/
├── phase4_centerpiece/                  ← day-ahead/intraday spread + follow-ons, all DE
├── phase5_polish/                       ← flagship Plotly view / Tableau piece
└── phase6_sweden_and_crossborder/       ← STRETCH: SCB + Nord Pool + ENTSO-E, cross-country work
```

**Core deliverable = Phases 1–5, Germany only.** That alone is a complete, honest, finishable
portfolio piece. Phase 6 is a genuine bonus, not a promise.

## Quick start

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Then open `phase1_smard_explore/` and start with `fetch_smard.py`.

## Ground rules for keeping this sane

1. **Don't open Phase 3 until Phase 1 and 2 run.** Each phase proves the previous mechanics work
   before you build structure on top of them.
2. **Stub files are stubs on purpose.** Docstrings explain the goal, `# TODO`s mark where the
   real logic goes — that's the scope, not a full implementation to figure out from scratch.
3. **Phase 6 is genuinely optional.** Don't start it until Phase 5 is done. If time runs out, a
   finished Germany-only project beats an unfinished two-country one.
4. When you come back after time away, read `TASKS.md` first.
