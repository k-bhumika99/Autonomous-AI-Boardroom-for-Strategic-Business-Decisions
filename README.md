# 🏛️ Autonomous AI Boardroom

**Multi-Agent Intelligence for Strategic Business Decisions**

## Overview

Autonomous AI Boardroom is a real, working multi-agent web application. A user
describes a project their company wants to build, and eight independent AI
agents — Planner, Finance, Marketing, Operations, Risk, Debate/Review, CEO and
Decision Synthesizer — work it through end to end: understand the request,
plan the work, estimate the budget, project revenue/profit/loss, plan growth,
stress-test the scenario, register the risks, and hand a signed-off
recommendation to the human who owns the budget.

Every number behind every chart (profit, ROI, break-even, cash flow, LTV:CAC,
risk exposure, the final weighted score) is computed deterministically in
Python by `services/projections.py`. Gemini is only ever asked for the
*assumptions* and the interpretation — growth rates, best/worst multipliers,
budget splits, what the numbers mean — never for the arithmetic itself. The
same inputs always produce the same charts.

The moment a decision is created, the board starts working in the
background — there's no separate "run" page to visit first. You land
directly on a crisp, one-screen-per-agent wizard (Finance → Marketing →
Operations → Risk → CEO), each with the headline numbers, a few sharp
insights, and a **Next Agent →** button, ending on the CEO's recommendation
and a full human sign-off panel.

## Problem Statement

Real strategic decisions get pulled apart by competing departmental views —
Finance wants ROI, Marketing wants growth, Operations wants feasibility, Risk
wants caution — and reconciling them usually happens informally, in a room,
with no paper trail. This app simulates that room with independent AI agents,
makes the disagreements explicit, and produces one auditable, explainable
recommendation instead of a black-box "yes/no".

## Solution

Each specialist agent runs as its own LangChain + Gemini call, bound to its
own Pydantic schema so malformed output is caught before it's ever stored.
LangGraph orchestrates the workflow: Finance, Marketing and Operations run as
independent branches, feed into Risk, which feeds a Debate/Review agent and a
Strategic Fit assessment, which feed a deterministic weighted-scoring engine,
which feeds the CEO agent, which feeds the final Decision Synthesizer. Every
stage is persisted to SQLite as it completes, so the UI can show real
progress instead of a fake spinner.

## Architecture

```
USER  (describes the project)
 ↓
SCENARIO VALIDATION  — background run starts here, immediately
 ↓
PLANNER AGENT  — understands the request, scope, phases, what/how/when
 ↓             (its plan is fed to every agent below, so the whole
 ↓              board reasons about the same interpretation)
PARALLEL SPECIALIST ANALYSIS  (staggered — see "Why the agents are staggered")
 ├── Finance Agent   (CFO)
 ├── Marketing Agent (CMO)
 └── Operations Agent (COO)
 ↓
Risk Agent (CRO)
 ↓
 ├── Debate / Review Agent
 └── Strategic Fit Assessment
 ↓
Weighted Decision Scoring (deterministic Python)
 ↓
CEO Agent  — recommendation + budget release proposal
 ↓
Decision Agent → Final Executive Report + 90-day plan
 ↓
HUMAN SIGN-OFF  — the CEO / manager / lead records the real decision
```

While the graph above runs in a background thread, the person sees the
**step wizard**: Finance → Marketing → Operations → Risk → CEO, one screen at
a time, each with a small "Step X of 5" pill and a **Next Agent →** button.
If a step's agent hasn't finished yet, that page shows a lightweight
auto-refreshing "analyzing your scenario…" card instead of the next screen —
there's no separate live-monitoring dashboard to babysit. Plan, Debate and
the full Report are still available from the sidebar for anyone who wants
the deeper view.

### Why the agents are staggered

Finance, Marketing and Operations fan out from the Planner as true parallel
LangGraph branches — three (sometimes four, with Risk right after) Gemini
calls firing within the same second. Free-tier API keys have a per-minute
rate limit, and a burst that tight trips it even on a single boardroom run.
`graph/boardroom_graph.py` staggers those branches by a couple of seconds
each, and `services/gemini_service.py` backs off with real exponential delay
(not an instant retry) whenever it detects a rate-limit response, so a
transient 429 doesn't take down half the board. If an agent still can't get
through, its step page says plainly that it's a quota issue — not a bug —
and how long to wait before hitting **Retry**.

## Agent Responsibilities

| Agent | Role | Core Question |
|---|---|---|
| Planner | Chief of Staff | What is actually being asked, and what's the plan — what to do, how, when, who? |
| Finance | CFO | Does this make financial sense? |
| Marketing | CMO | Will customers want and buy this? |
| Operations | COO | Can we actually execute this? |
| Risk | CRO | What could go wrong, and how do we mitigate it? |
| Debate/Review | Boardroom facilitator | Where do the specialists agree, disagree, and how do we resolve it? |
| CEO | Chief Executive | Given everything, should we proceed — and why? |
| Decision Synthesizer | Executive writer | Assemble the final, board-ready report and the 90-day plan |
| **Human approver** | CEO / Manager / Team Lead | The AI recommends; **you** approve, approve with conditions, send back, or reject |

## Human Approval

The AI CEO agent proposes; it does not decide. Every completed decision lands
in `awaiting_approval`, and the CEO page carries a sign-off panel where the
real budget owner records one of four outcomes:

| Action | Stored status | Effect |
|---|---|---|
| ✅ Approve | `approved` | Full budget released |
| 📝 Approve with conditions | `approved_with_conditions` | Records a partial budget % and the conditions |
| ↩️ Send back for rework | `sent_back` | Returns it with a note |
| ⛔ Reject | `rejected` | Approved budget forced to 0 |

The approver's name, role, note, released budget percentage and timestamp are
persisted on the `Decision` row and printed into the exported PDF, so there is
a real paper trail.

## Dashboards & Charts

Charts are built with Chart.js 4 through a single themed wrapper,
`static/js/charts.js` (`window.BR`), which matches the pastel design system and
formats every value in Indian rupees (₹ / L / Cr).

| Builder | Used for |
|---|---|
| `BR.line` | Cash-flow curve, customer S-curve, revenue trend |
| `BR.bar` | Budget by category, channel spend, year-on-year P&L |
| `BR.mixed` | Revenue bars + cumulative profit line, what-if sensitivity |
| `BR.doughnut` | Budget split, scope, segment share |
| `BR.gauge` | Every agent's score and confidence |
| `BR.radar` | Five-dimension score comparison across agents |
| `BR.riskMatrix` | Probability × impact bubbles, sized by financial exposure |
| `BR.gantt` | Delivery roadmap by phase and owner |
| `BR.waterfall` | Investment → revenue → cost → profit bridge |
| `BR.funnel` | Marketing funnel, back-solved to hit the customer target |
| `BR.polar` | Risk categories, portfolio mix |

Where they appear:

| Page | What you get |
|---|---|
| **Dashboard** | Portfolio KPIs, decisions by outcome, score comparison, investment vs revenue |
| **Analytics** | Cross-decision analytics — score trends, risk severity mix, category spread, ROI scatter |
| **Plan** | Readiness gauge, budget allocation, phase Gantt, scope in/out |
| **Debate** | Consensus strength, agreements vs disagreements |
| **Report** | Full executive report, risk matrix, 90-day plan, PDF export |
| **What-If** | Re-run the numbers with different investment/revenue/cost and see the sensitivity sweep |

## The Step Wizard (Finance → Marketing → Operations → Risk → CEO)

These five pages deliberately have **no charts** — they're the fast path to
an answer, styled after a single clean card per agent:

- A headline icon, title and one-line tagline for the agent
- A short "Your Scenario" recap so you never lose context
- Four KPI tiles (e.g. Finance: estimated revenue, cost, profit, ROI)
- Three short bullet sections — Recommendations, Key Insights, Risks — capped
  at five items each, always with a sensible fallback if the agent returned
  nothing usable for that section
- A one-line conclusion callout
- **Next Agent →** (or, on the CEO step, the full human approval panel)

All rendered from one shared template, `templates/agent_step.html`, with the
content built per agent by `services/step_view.py` from the same validated,
deterministic data the charts elsewhere use — nothing here is a separate
source of truth. Charts, when you want the fuller picture, are still one
click away on **Dashboard**, **Analytics**, **Plan**, **Debate**, **Report**
and **What-If**.

## Technology Stack

- **Backend:** Python 3.11+, Flask, Flask-SQLAlchemy, SQLite, python-dotenv
- **AI:** LangChain, LangGraph, Google Gemini, Pydantic
- **Frontend:** HTML5, CSS3 (pastel/glassmorphism design system), vanilla JS, Chart.js 4 (Dashboard/Analytics/Plan/Debate/Report/What-If — the step wizard itself is chart-free by design)
- **PDF export:** ReportLab

## Folder Structure

```
autonomous_ai_boardroom/
├── app.py                  # Flask app factory
├── config.py                # Central config (Gemini, scoring weights, DB)
├── database.py               # Shared SQLAlchemy instance
├── models.py                 # User, Scenario, AgentResult, Debate, Decision
├── auth.py                   # Signup / signin / logout blueprint
├── migrations.py             # Additive column migration for older dev databases
├── agents/                   # One module per agent, each with its own prompt
│   ├── planner_agent.py      # Runs first; its plan feeds every other agent
│   └── schemas.py            # Pydantic contract for every agent's output
├── graph/                    # LangGraph state + orchestration
├── services/
│   ├── projections.py        # Deterministic engine behind every chart
│   ├── step_view.py          # KPI tiles + bullet content for the step wizard
│   ├── flow.py                # Step-state machine behind /api/.../status
│   ├── gemini_service.py     # All Gemini access — retries + rate-limit backoff
│   ├── calculations.py       # Profit / ROI / break-even
│   ├── scoring.py            # Weighted decision scoring
│   ├── formatting.py         # ₹ Indian number formatting Jinja filters
│   └── report_service.py     # PDF export
├── routes/                   # HTML page routes + JSON API routes
├── templates/
│   └── agent_step.html       # Shared step-wizard template (5 agent pages)
├── static/css/style.css      # Pastel/glassmorphism design system
├── static/js/charts.js       # Themed Chart.js wrapper (window.BR) — loaded
│                              # in <head>, before any page's inline chart script
└── tests/                    # Unit + integration tests
```

## Installation

```bash
cd autonomous_ai_boardroom
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your Gemini key:

```
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
SECRET_KEY=some-random-secret
```

**Get a Gemini API key:** https://aistudio.google.com/app/apikey — the app
never hardcodes this key and never sends it to the browser. If it's missing,
every agent fails gracefully with a clear "Gemini not configured" message
instead of crashing or faking a result.

## Database Setup

No manual step needed — `db.create_all()` runs automatically on first launch
and creates `instance/boardroom.db`.

If you already have a `boardroom.db` from an older version, `migrations.py`
adds the new columns (plan fields, approval fields, industry/business model)
in place on startup. Nothing is dropped and no data is lost.

## Running the Application

```bash
python app.py
```

Visit `http://localhost:5000`, sign up, and click **➕ New Decision**.

## Example Scenario

> Our company has developed an AI-powered healthcare product. We require
> ₹50 lakh investment and expect ₹1.2 crore annual revenue. Our target
> customers are private hospitals and diagnostic centers. The planned launch
> timeline is 6 months.

## LangGraph Workflow

The graph (`graph/boardroom_graph.py`) runs `validate` → `planner`, then fans
out from `planner` to `finance`, `marketing` and `operations` in parallel
(each receiving the Planner's plan as context), joins at `risk`, fans out again to
`debate` and `strategic_fit`, joins at `scoring`, then runs `ceo` and
`decision` sequentially. Every node persists its result immediately and
updates `Scenario.current_stage`, so `static/js/boardroom.js` can poll
`/api/decision/<id>/status` and show real, not simulated, progress.

## Weighted Scoring

```
Final Score = Finance × 0.25 + Marketing × 0.20 + Operations × 0.20
            + Risk × 0.20 + Strategic Fit × 0.15
```

| Score | Decision |
|---|---|
| 80–100 | STRONGLY RECOMMEND |
| 65–79 | RECOMMEND WITH CONDITIONS |
| 50–64 | REVIEW / DELAY |
| 0–49 | DO NOT PROCEED |

Weights live in `config.py` (`SCORE_WEIGHTS`) and are never decided by the LLM.

## Troubleshooting

- **"Gemini API key is not set"** — add `GEMINI_API_KEY` to `.env` and restart.
- **An agent shows "could not complete"** — check the terminal logs; the
  scenario is marked `completed_with_errors` and every other agent's results
  are still shown.
- **A step page says "analyzing your scenario…" for a while** — the
  background thread is still running; the page auto-refreshes every 3
  seconds. It survives page reloads since progress is persisted in SQLite.
- **An agent step says "hit a rate limit — not a bug"** — your Gemini key's
  free-tier quota (usually per-minute) got tripped by the burst of parallel
  calls. Wait about a minute and click **Retry This Agent**; `gemini_service.py`
  now backs off with real delay on retries instead of hammering the same limit.
- **`AttributeError: 'NoneType' object has no attribute 'id'`** — this meant
  your browser held a session for a user that no longer existed (usually after
  deleting or rebuilding `instance/boardroom.db`). Fixed: `login_required` now
  verifies the user still exists, clears the dead session, and sends you to
  sign in instead of crashing.
- **Charts don't draw** — fixed: Chart.js and `charts.js` used to load at the
  bottom of the page, after each page's own chart-building script, so
  `window.BR` didn't exist yet when it was needed. They now load in `<head>`,
  before anything else.

## Future Enhancements

- Multi-currency support beyond ₹ (INR)
- Streaming agent output instead of polling
- Configurable scoring weights from the Settings page
- Multi-turn follow-up questions to agents from each agent page
- Multi-approver sign-off chains (lead → manager → CEO)

## Testing

```bash
pytest tests/
```

111 tests, no API key required — the suite never calls Gemini.

Covers:

- **`test_routes.py`** — signup/login, unauthorized cross-user access
- **`test_calculations.py`** — profit, ROI, break-even, weighted scoring
- **`test_agent_schemas.py`** — Pydantic validation of every agent's output
  (out-of-range scores/confidence rejected, invalid risk severities and
  complexity levels normalised, empty responses still safe to render)
- **`test_projections.py`** — the deterministic chart engine: budget splits
  summing to the investment, ramp-discounted year one, ordered best/base/worst
  bands, funnels back-solved to the customer target, LTV:CAC consistency, risk
  exposure, roadmap ordering, and determinism (same input → same charts)
- **`test_flow_and_approval.py`** — the step-state machine behind the live
  status API, and the full human sign-off workflow including budget clamping
  and cross-user protection
- **`test_stale_session.py`** — every protected page redirects instead of
  crashing when the session outlives its user row
- **`test_wizard_and_reliability.py`** — creating a decision lands directly
  on the Finance step; `/run` can never wipe a completed or in-progress run
  (a real bug this session, since it's the fallback target from several other
  pages); `step_view.py`'s KPI/bullet builders stay sane against partial or
  empty agent output; `gemini_service.py` backs off on rate limits instead of
  retrying instantly into the same wall
- **`test_chart_script_order.py`** — replays each chart-bearing page's
  `<script>` tags in real browser execution order and fails if any inline
  chart call runs before `charts.js` has loaded. This is the test that would
  have caught the "no chart ever draws" bug — plain syntax checking
  (`node --check`) cannot see it, since the bug is about *order across
  multiple tags*, not syntax within one.
