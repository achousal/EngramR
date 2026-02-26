# Engram Reactor

**EngramR is a cumulative research environment where humans and AI jointly capture, connect, and stress-test knowledge, translate evidence into prioritized research plans, and track the data, infrastructure, and analytical context that ground every analysis — maintaining end-to-end provenance from source to result.**

Every paper read, observation logged, and experimental result feeds a persistent
knowledge graph. Hypotheses are generated from that evidence, debated pairwise on
scientific merit, ranked by Elo rating, and evolved through feedback. Each cycle
sharpens the next.

Inspired by DeepMind's [AI co-scientist](https://arxiv.org/abs/2502.18864).<br>
Powered by [Ars Contexta](https://github.com/agenticnotetaking/arscontexta) knowledge architecture.<br>
Runs on [Claude Code](https://docs.anthropic.com/en/docs/claude-code) + [Obsidian](https://obsidian.md/).<br>
Read the [vision document](docs/EngramR.md) for the design philosophy.

---

## The research cycle

1. A paper lands in the inbox. `/reduce` extracts atomic claims with structured
   metadata. `/reflect` links them to existing claims in the graph.

2. Evidence density crosses a threshold. `/generate` proposes testable hypotheses
   grounded in the accumulated claims, each with mechanism, predictions, and
   falsification criteria.

3. `/tournament` debates them pairwise. One hypothesis wins the most matches -- it
   has stronger evidence support and more specific predictions. Elo ratings update.
   Debate transcripts are stored.

4. `/meta-review` synthesizes what made winners win. That feedback injects into the
   next `/generate` and `/evolve` cycle. The reactor learns what good hypotheses
   look like in its domain.

5. The top hypothesis comes with a pre-specified analysis plan. `/experiment` logs
   the run. Results feed back into the graph. The leaderboard updates.

---

## Architecture

EngramR combines a **knowledge layer** that extracts, connects, and maintains
a graph of atomic claims, and a **hypothesis layer** that generates, debates,
ranks, and evolves testable hypotheses from that evidence.

### Knowledge layer

When a lab sets up EngramR, [Ars Contexta](https://github.com/agenticnotetaking/arscontexta)
derives the knowledge system -- folder structure, topic maps, analysis
standards -- from a conversation about the lab's research domains and working
style. Each insight becomes an atomic claim: a single note
with structured metadata and wiki-link edges to related claims. The result is a
knowledge graph built from plain markdown that any team member can browse.

The vault is organized around three primitives:

| Primitive    | What it provides                                                                                              |
| ------------ | ------------------------------------------------------------------------------------------------------------- |
| **Scope**    | Domain boundaries -- research areas, epistemic stance, inclusion and exclusion criteria                        |
| **Contexts** | Three-space architecture: `self/` (identity, methodology, goals), `notes/` (atomic claims), `ops/` (config, queue, sessions) |
| **Texts**    | Atomic claims -- single-insight notes titled as prose propositions, linked by wiki-link edges into a graph     |

Topic maps organize claim clusters into navigable neighborhoods. Templates
enforce consistent figure style and statistical conventions across the team.
Raw input enters through a quality pipeline:

```
inbox/ --> /reduce --> /reflect --> /reweave --> /verify --> notes/
```

### Hypothesis layer

The hypothesis layer reads the accumulated evidence and generates testable
predictions -- each with mechanism, falsification criteria, and a pre-specified
analysis plan. Pairwise debates evaluate novelty, plausibility, testability,
and impact. Elo ratings rank the leaderboard. Meta-reviews extract what made
winners win and inject that feedback into the next generation. Because
hypotheses are themselves notes in the graph, experimental results become
new claims that feed future cycles.

Goals spawn hypotheses. Hypotheses spawn projects. Project results feed back
into the hypothesis pool, reshaping the leaderboard.

|                 | Goal                         | Hypothesis                          | Project                             |
| --------------- | ---------------------------- | ----------------------------------- | ----------------------------------- |
| **Definition**  | Open-ended research question | Testable prediction with mechanism  | Concrete work with defined scope    |
| **Lifecycle**   | Evolves as the lab learns    | Generated, debated, ranked, evolved | Has timeline, budget, deliverables  |
| **Elo applies** | Organizes the leaderboard    | Yes -- compete head-to-head         | No -- projects execute, not compete |

A goal like "Identify biomarker signatures for early AD detection" spawns
hypotheses like "Ceramide-plasmalogen ratio predicts amyloid status," which
spawns a project to run that analysis on a specific cohort.

---

## Adoption

EngramR starts blank -- no migrations needed. It runs alongside whatever the team
already uses. Early on, the system captures and connects. Then it begins
generating hypotheses. Over time, the knowledge graph grows dense enough that
new observations land in a web of existing connections. Teams feed the reactor
what they actually have -- datasets, cell lines, instruments, constraints --
and the system ranks hypotheses not just by scientific merit but by what the
lab can realistically act on.

Adoption is not a cliff. It is a gradient. Send one observation and you have
contributed. Browse the leaderboard and you understand the lab's priorities. Run
an analysis and feed back results. The deeper the team engages, the more the
reactor gives back.

---

## Scaling

### To a team

EngramR works as a single-user tool, but it is designed for labs. Connect Slack
via MCP so team members can send observations, ask questions, and check the
leaderboard without leaving their workflow. A postdoc's literature note links
to a tech's bench observation automatically. The reactor connects what no
single person had time to.

### Across labs

Multiple reactors compound. Each lab runs its own EngramR instance, generates and
ranks hypotheses against its own data. But knowledge graphs can be selectively
bridged -- Lab A's gene regulatory observation connects to Lab B's protein
signature in patient samples. Neither lab would have made that connection alone.

Cross-lab EngramR does not require merging teams or sharing raw data. It requires
sharing claims. Elo tournaments can include cross-lab hypotheses, letting ideas
from different groups compete on equal footing. The system surfaces the scientific
overlap first. The PIs decide whether to cross the bridge.

---

## Getting started

### Prerequisites

| Dependency                                                                         | Required | Purpose                                         |
| ---------------------------------------------------------------------------------- | -------- | ----------------------------------------------- |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code)                      | Yes      | Command host and agent runtime                  |
| [Obsidian](https://obsidian.md/)                                                   | Yes      | Vault browser and editor                        |
| [Local REST API plugin](https://github.com/coddingtonbear/obsidian-local-rest-api) | Yes      | Programmatic vault access                       |
| Python 3.11+                                                                       | Yes      | Library runtime                                 |
| [uv](https://docs.astral.sh/uv/)                                                  | Yes      | Python package management                       |
| `ripgrep` (`rg`)                                                                   | Yes      | YAML queries, graph analysis, schema validation |
| [Slack MCP plugin](https://github.com/slackapi/slack-mcp-plugin)                   | No       | Team interactions via Slack                      |

### Setup

1. Clone the repo and open it as an Obsidian vault:
   ```bash
   git clone https://github.com/achousal/EngramR.git
   ```
   In Obsidian: Open folder as vault. Enable the Local REST API plugin in
   Community Plugins and copy the API key.

2. Install the Python library:
   ```bash
   cd EngramR/_code
   uv sync --all-extras
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Fill in `OBSIDIAN_API_KEY` (from step 1), `NCBI_API_KEY`, and `NCBI_EMAIL`
   (get NCBI keys at https://www.ncbi.nlm.nih.gov/account/settings/).
   Optionally add `SLACK_BOT_TOKEN`, `SLACK_DEFAULT_CHANNEL`, and
   `SLACK_TEAM_ID` to enable Slack sync (see [setup guide](docs/manual/setup-guide.md)).

4. Install the Ars Contexta plugin (knowledge processing layer):
   ```
   /plugin marketplace add agenticnotetaking/arscontexta
   /plugin install arscontexta@agenticnotetaking
   ```

5. Verify everything works:
   ```bash
   uv run pytest tests/ -v
   ```

6. Start Claude Code in the vault directory. Run `/onboard` to set up your
   lab, or `/next` to see what the system recommends.

### First steps

1. **Onboard your lab.** Point `/onboard` at your lab directory:
   ```
   /onboard ~/projects/My_Lab/
   ```
   EngramR scans for projects, asks about what it cannot detect, and generates
   vault artifacts in one pass -- project notes, data inventory, research
   goals, and index updates. Re-run `/onboard --update` when new projects
   arrive.

2. **Feed it literature.** Drop sources into `inbox/` and `/reduce`, or use
   `/literature` to search PubMed/arXiv directly.

3. **Let the loop run.** `/research` orchestrates hypothesis generation,
   debate, and ranking based on your registered data and goals.

4. **Configure the daemon** (optional). Edit `ops/daemon-config.yaml` and
   run in tmux:
   ```bash
   tmux new -s daemon 'bash ops/scripts/daemon.sh'
   ```

### Preparing your projects

`/onboard` works with messy directories, but these steps improve detection:

- **One directory per project** under a shared lab folder.
- **Initialize git repos** -- `.git/` is the strongest boundary signal.
- **Add a CLAUDE.md** to each project. `/onboard` reads it to auto-populate
  description, tech stack, and data files. A minimal example:
  ```markdown
  # Tumor Microenvironment Atlas

  Single-cell RNA-seq analysis of immune infiltration across
  three solid tumor types.

  ## Tech stack
  - Python (scanpy, scvi-tools)
  - R (Seurat, ggplot2)

  ## Data
  - Raw counts: data/counts.h5ad (45,000 cells x 22,000 genes)
  - Clinical metadata: data/patients.csv (n=120)
  ```
- **Use `data/`, `analysis/`, `results/`** directory names for richer
  auto-detection.
- **Note data provenance** in CLAUDE.md or `data/README.md` so EngramR can
  detail source, sample size, and access status.

---

## Reference

<details>
<summary>Commands</summary>

### Co-scientist commands

| Command        | What it does                                                                                    |
| -------------- | ----------------------------------------------------------------------------------------------- |
| `/research`    | Supervisor -- selects which loop step to apply next                                             |
| `/generate`    | Propose testable hypotheses (4 modes: de novo, literature-seeded, gap-filling, cross-goal)      |
| `/review`      | Critical evaluation (6 modes: plausibility, novelty, testability, impact, feasibility, overall) |
| `/tournament`  | Elo-ranked pairwise debate on scientific merit                                                  |
| `/evolve`      | Refine top hypotheses (5 modes: strengthen, merge, pivot, decompose, generalize)                |
| `/landscape`   | Map the hypothesis space -- clusters, gaps, redundancies                                        |
| `/meta-review` | Extract patterns from debates and inject feedback into next cycle                               |

### Research support commands

| Command       | What it does                                                           |
| ------------- | ---------------------------------------------------------------------- |
| `/literature` | Search PubMed and arXiv, create structured literature notes            |
| `/experiment` | Log experiments with parameters, results, statistical analysis plans   |
| `/eda`        | Exploratory data analysis with PII auto-redaction                      |
| `/plot`       | Publication-quality figures with statistical annotations (Python + R)  |
| `/project`    | Register and query research projects                                   |
| `/onboard`    | Bootstrap a lab -- scan filesystem, interview, generate all artifacts  |

### Ars Contexta commands

| Command     | What it does                                           |
| ----------- | ------------------------------------------------------ |
| `/reduce`   | Extract insights from sources                          |
| `/reflect`  | Find connections, update MOCs                          |
| `/reweave`  | Update older notes with new connections                |
| `/verify`   | Combined quality check: description + schema + health  |
| `/validate` | Schema compliance checking                             |
| `/seed`     | Create extraction task with duplicate detection        |
| `/ralph`    | Queue-based orchestration with fresh context per phase |
| `/pipeline` | End-to-end source processing                           |
| `/tasks`    | Queue management                                       |
| `/stats`    | Vault metrics                                          |
| `/graph`    | Graph analysis                                         |
| `/next`     | Next-action recommendation                             |
| `/learn`    | Research and grow                                      |
| `/remember` | Mine session learnings                                 |
| `/rethink`  | Challenge system assumptions                           |
| `/refactor` | Structural improvements                                |

</details>

<details>
<summary>Daemon</summary>

An autonomous background process that runs tournaments, maintenance, and
synthesis while you work. It reads vault state, picks the highest-priority
task from a five-level cascade (health checks, research cycle, maintenance,
background work, idle), and executes it via Claude Code. Generative work can
run fully autonomous or queue to `ops/daemon-inbox.md` for human review.

See [daemon configuration](docs/manual/configuration.md) for the full
priority cascade and guardrail options.

</details>

<details>
<summary>Hooks</summary>

Four hooks automate the session lifecycle:

| Hook                | Event               | What it does                                          |
| ------------------- | -------------------- | ----------------------------------------------------- |
| **Session Orient**  | SessionStart        | Loads identity, surfaces active goals and leaderboard |
| **Write Validate**  | PostToolUse         | Schema enforcement on every note write                |
| **Auto Commit**     | PostToolUse (async) | Every change is version-controlled automatically      |
| **Session Capture** | Stop                | Persists session state for future mining              |

</details>

<details>
<summary>Integrations</summary>

EngramR extends through [MCP servers](https://modelcontextprotocol.io/) --
standardized plugins that give Claude Code access to external services.
Two ship in `.mcp.json`:

- **mcp-obsidian** -- programmatic vault access (reads, writes, search)
- **Slack** -- team notifications and channel interaction

See the [setup guide](docs/manual/setup-guide.md) for step-by-step
configuration of each server, including Slack app creation and
automated notification setup.

</details>

---

## License

MIT
