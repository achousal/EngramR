# Engram Reactor

## The problem is not ideas. It is visibility.

Every lab meeting, we discuss many promising directions. How do we decide which ones to pursue, and based on what evidence? Without a system to track and compare them, most fade.

When I joined the lab, it took me three weeks just to understand what each team member was working on and where the group was heading. That context lived in people's heads -- in scattered conversations, slides, in the PI's intuition. There was no single place to look. A postdoc reads a paper that contradicts an assumption but files it under "interesting" and moves on. A technician notices something unexpected but has no time to chase it down. These insights are real, but without a system to persist them, they fade.

The ideas that do surface face a harder problem: our lab has finite bench hours, finite sequencing budget, finite analyst bandwidth. Ten good ideas compete for three experimental slots. The ones that get pursued are not always the ones best supported by evidence -- they are the ones someone had time to champion.

The gap is not analytical skill or scientific creativity. It is the infrastructure to accumulate evidence and convert it into prioritized action.

## Two capabilities make this possible, and both exist today.

The first is **[Ars Contexta](https://github.com/agenticnotetaking/arscontexta)** -- an open-source knowledge architecture that turns raw research input into a persistent, searchable graph. Every observation, paper, and experimental result becomes a structured claim linked to related claims. The graph is the lab's institutional memory -- browsable, queryable, and built from the lab's own work.

The second is the **co-scientist** -- a hypothesis engine that operates on top of that graph. Inspired by [DeepMind's AI co-scientist](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/), it runs a competitive loop: generate hypotheses from the evidence base, debate them pairwise on scientific merit, rank them by Elo rating, and evolve the strongest through meta-review feedback. Each cycle sharpens the next.

Neither layer reaches its full potential alone. A knowledge graph without hypothesis generation is a well-organized archive. A hypothesis engine without structured evidence is speculation. The combination is what shifts the bottleneck from human attention to evidence quality.

The primary interface is Claude Code. Slack integration via MCP connects the team -- send observations, get notifications, check the leaderboard. The vault is available for deeper exploration when needed.

---

## EngramR in use

### From an observation to results

**9:02am** -- The tech notices something unexpected in her experiment. She sends a Slack message.

> "Seeing unexpected protein accumulation in the treated group at 24h. Wasn't part of the original hypothesis."

She goes back to her bench.

**9:03am** -- The reactor extracts a structured claim, tags it, and searches the knowledge graph. Three connections surface: a grad student's sequencing data from March that showed the same pathway activating, a paper the postdoc read last week about a related mechanism, and an existing hypothesis that predicted this involvement -- but through a different mechanism. The claim is linked to all three. A tension is flagged: the data supports the prediction but not the proposed mechanism.

**9:40am** -- The postdoc gets a Slack notification: a new observation was linked to a literature note he submitted last week. He did not know anyone in the lab was generating data in this area. He taps through, reads the tension flag, and sends a follow-up.

> "Her data fits the alternative pathway better. If that's the mechanism, we should see it in the proteomics dataset we already have."

**9:41am** -- The reactor links the postdoc's claim to the growing cluster. Evidence density crosses the threshold. The system generates an evolved version of the hypothesis -- same core prediction, updated mechanism based on the converging evidence. The evolved hypothesis comes with a pre-specified analysis plan and statistical tests.

**9:45am** -- The evolved hypothesis enters the tournament and debates the original head-to-head on specificity, evidence support, and testability. It wins -- three independent data sources where the original had one. Elo updates. Debate transcript stored.

**11:15am** -- The postdoc executes the analysis. He does not start from scratch -- the hypothesis note contains the test, the parameters, and the figure template. Results: two of three predictions confirmed. One is inconclusive. The system logs the experiment, links results to predictions, flags the gap for the next debate cycle.

**11:30am** -- The graph updates. The hypothesis holds its rank but carries a documented weakness. Next round, that weakness is fair game.

One morning. Two people sent messages while doing their actual work. The reactor connected their observations, evolved a hypothesis, debated it, ranked it, and pre-specified the analysis. By late morning, results were in and feeding back into the system. Nobody stopped what they were doing.

### From anomaly to project proposal

A grad student uploads her dataset to EngramR for exploratory analysis. The system generates a report -- plots in the lab's standard style, summary statistics, all processed locally on the lab's own infrastructure. One finding stands out: a pattern in her data that does not match any existing hypothesis in the graph.

She asks: "What could explain this?"

The reactor searches the knowledge graph. It finds six related claims from literature and prior observations, identifies two possible mechanisms, and generates a hypothesis from the anomaly -- complete with predictions, a validation plan using data already on the server, and falsification criteria. The hypothesis enters the tournament that week.

The anomaly that would have been a footnote in her thesis is now a ranked project proposal with structured evidence behind it.

### Administration

**Writing aims from evidence.** The PI needs specific aims for a new grant. She defines a research goal in EngramR. The system generates six hypotheses from the existing knowledge graph, she runs a tournament to rank them. She considers the top three as her aims -- each with mechanism, predictions, and preliminary data already identified from the lab's own datasets. The debate transcripts document why these beat the alternatives.

**Allocating resources.** The PI has budget for one new project. She filters the leaderboard by hypotheses testable with existing data. Three candidates surface with different cost profiles: one needs only a proteomics dataset from January, another needs RNA-seq already on the server, a third would require a new cohort. The decision takes minutes. The evidence trail is there for anyone to review.

**Opening a new direction.** The PI reads a paper that opens an unexplored direction. She defines a new goal. The system scans the existing graph -- twelve claims are already relevant, two projects have transferable data. The reactor generates three seed hypotheses from what the lab already knows. The new direction starts with context, not from zero.

---

## Networking across labs

One reactor per lab is already valuable. Multiple reactors compound -- connections multiply across boundaries that no single lab can see.

Two labs working in adjacent areas each run their own EngramR instance. Each generates and ranks hypotheses against their own data. But the knowledge graphs can be selectively bridged. Lab A's observation about a gene regulatory pattern connects to Lab B's finding about a protein signature in patient samples. Neither lab would have made that connection alone.

Cross-lab EngramR does not require merging teams or sharing raw data. It requires sharing claims -- structured observations that link across knowledge graphs. Elo tournaments can include cross-lab hypotheses, letting ideas from different groups compete on equal footing.

This inverts the traditional collaboration model. Instead of two PIs deciding to collaborate and then looking for scientific overlap, the system surfaces the overlap first. The knowledge graph identifies the bridges. The PIs decide whether to cross them.

---

The reactor is running. The question is which ideas to put into it.
