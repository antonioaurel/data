# Presentation prompt

Paste the block below into Claude (or any design AI) to generate a slide deck
about this project. It carries the real facts so the deck is accurate; adjust
audience/length as needed.

---

You are a senior presentation designer. Create a clean, data-forward **slide deck**
about **EVE — an attendance-estimation system for events organized on Facebook**.

## Audience & tone
- Audience: technical + product stakeholders (engineers, a product lead, a professor/reviewer).
- Tone: confident, concise, honest about limitations. Substance over hype.
- Length: ~12–14 slides. One idea per slide, a strong title line, 3–5 bullets max, and a visual where noted.

## Visual direction
- Light, minimal, editorial. **White background**, a geometric humanist sans (Avenir Next / Avenir feel), generous whitespace, small tasteful type scale.
- Accent blue `#2f6df6`. Size-class color coding used consistently: micro `#2a78d6`, small `#008300`, medium `#e87ba4`, large `#eda100`.
- Prefer real diagrams over clip-art: simple flowcharts, a predicted-vs-actual scatter, a bar chart of conversion by size, an architecture box diagram.
- Numbers are the hero — show the metrics big.

## Required slides (use these section headers, in order)

**1 — Title.** "EVE — Estimating real attendance for Facebook events." Subtitle: a modern reimplementation of a 2016 master's system as a data/modeling project.

**2 — Agenda.** Motivation · Basis · Proposal · Opportunity · Test architecture · Decisions (ADRs) · Current state.

**3 — Motivation.**
- Facebook events collect "Going / Interested" RSVPs, but **real attendance is a fraction** of those, and the gap widens with event size.
- Organizers must plan physical resources (staff, security, food, restrooms) from unreliable signals; over- or under-provisioning is costly.
- Raw RSVP counts systematically overstate turnout — a decision-support gap.
- Visual: a funnel/gap from "Going" → actual attendance.

**4 — What it's based on.**
- The author's **2016 master's article** "EVE — Estimation of Variables to Events" (C.E.S.A.R, Recife). Requirements-era system + a field experiment.
- Real seed data digitized from the article: **20 events** — 16 public events classified by size (tables 7–10) and a **4-rehearsal field experiment** (May 2013, a Recife percussion group).
- Honest note: the article's own arithmetic has documented inconsistencies, preserved and asserted in tests rather than silently "fixed".

**5 — What the system proposes.**
- Turn RSVP counts into a **realistic attendance estimate**, not a raw sum.
- Core idea: **learn conversion rates** (attendance probability per response type × size class) from data — replacing EVE's original weakness, where an **operator had to guess** those proportions.
- A tool that outputs an estimate, a likely range, and a **decomposition** (how many attendees come from Confirmed / Maybe / No-reply), adjustable by **external effects** (a rival match, rain… as ± %).
- Visual: the formula `attendance ≈ Σ (count × learned rate[size][type])`, then × effects.

**6 — The opportunity.**
- Better **resource planning and ROI** for organizers; fewer over/under-provisioning mistakes.
- A **recalibration loop**: log real attendance → export CSV → refit → improved rates embedded back into the tool and dashboard. It gets better with use.
- Generalizable beyond the seed data as more events are logged.
- Visual: the closed loop (tool → CSV → model → coefficients → tool).

**7 — Results so far (proof).**
- Learned-rates model: **overall MAE 34 / MAPE 24%** (in-sample, 20 events); **~76% mean accuracy**.
- On the field experiment it **nearly ties a hand-tuned baseline (MAE ~3.25 vs 3.0)** — with **no operator input**, and the baseline can't even run on the 16 size-events.
- Conversion collapses with size: micro ~89% of confirmed attend, large ~22%.
- Visual: predicted-vs-actual scatter (log scale, colored by size) + conversion-by-size bars.

**8 — Test architecture.**
- **Automated (pytest, 22 tests):** unit tests of the formula; **data-integrity** tests (schema, sums, ranges) that also **assert the article's known inconsistencies**; model tests (rate ordering, bounds); and **regression tests** pinning exact metrics (baseline MAE 3.0; model MAE 34.4 / MAPE 24.4).
- **Component matrices** as the test/risk spine: an **operation flow** (each step = a test scenario) plus module-feature, cross-dependence, reuse, and identification (selector) matrices.
- **Manual UI cases** for the tool and dashboard, mapped to `data-testid` selector roots.
- **Docs-stay-in-sync:** a `check_matrices.py` script + a **pre-commit hook** + a `/sync-matrices` skill keep the matrices aligned with the UI.
- Visual: a small pyramid — unit → data → regression → UI, with the matrices as the connecting spine.

**9 — Architecture (one picture).**
- Two decoupled tiers meeting at one file: **offline (Python)** `data/*.csv → src/model.py → model_coefficients.json`, and **client (static HTML/JS)** `app/` tool + `reports/` dashboard that **embed** those coefficients.
- No server, no database, no build step. The **coefficient JSON is the shared contract**.
- Visual: two boxes joined by the JSON artifact.

**10–11 — Key decisions (ADRs).** Present as compact cards: *Decision → Why*.
- **ADR-1 Scope = analysis/modeling, not a rebuilt web app.** The system layer was requirements-era; the value now is the model.
- **ADR-2 No Facebook Graph API.** The endpoints EVE imported RSVPs from were removed in 2018 (post–Cambridge Analytica); input is digitized/manual counts.
- **ADR-3 No backend / no database.** n≈20 events; CSVs in git are the store, with diff/history/review for free.
- **ADR-4 Python for the offline tier.** Fit for tabular modeling/backtesting, notebook-native, dependency-light, testable; clear path to bigger models.
- **ADR-5 Static HTML + vanilla JS for the client.** Small, self-contained, no framework/build; embeds coefficients and runs standalone.
- **ADR-6 Learn rates from data** instead of operator-informed proportions — the central modeling fix.
- **ADR-7 Coefficient JSON as the contract** between tiers, versioned; changing its keys is a breaking change for both pages.
- **ADR-8 Dashboard = three-pane "F2"** (event list · charts · metrics rail); single light theme, white + Avenir.
- **ADR-9 Tool = single-page vertical form** with mandatory-field gating (Next disabled until valid) instead of a hidden step wizard.

**12 — Current state.**
- Built: digitized dataset; EVE-formula **baseline**; **learned-rates model v1** + exported coefficients; **22 passing tests**; two **notebooks** (EDA + model-vs-baseline); the **tool** (single-page, white/Avenir, local history + CSV export); the **F2 dashboard** (white); a **glossary** page; docs (SPEC, ARCHITECTURE, SYSTEM-DESIGN, FLOW, TEST-CASES) and the **component matrices** + sync tooling.
- Honest limitations: in-sample metrics, tiny n, medium/large classes have only 4 events each.

**13 — Next steps.**
- **Simulated data calibrated on the seed rates** to strengthen medium/large classes.
- Wire `data-testid`s to automate the UI test cases.
- Grow the recalibration loop with real logged events.

**14 — Closing.** One line: *EVE turns unreliable RSVP counts into a calibrated attendance estimate — and gets better every time an organizer logs what actually happened.*

## Output
Produce the deck as a self-contained artifact (HTML slides or a slide-styled document). Keep every claim consistent with the facts above; do not invent numbers.
