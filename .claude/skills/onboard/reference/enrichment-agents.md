# Enrichment Agent Prompts

Reference file for the /onboard orchestrator's Turn 1b and Turn 2b context enrichment phases.
Each section is a complete agent prompt template. The orchestrator substitutes `{variables}` and launches via the Agent tool.

---

## A1: Lab Profile Enrichment

**Agent config:** subagent_type: "general-purpose", model: "sonnet"
**Condition:** User provided a lab website URL in Turn 1. If no URL provided, skip the WebFetch step but still run /learn.

**Prompt template:**

```
You are enriching lab-level context during /onboard. Your job has two parts -- run both.

PART 1: Lab website (if URL provided)

WebFetch the URL: {lab_website_url}
Prompt: "Extract from this lab website:
1. Research focus areas and themes
2. Current group members (name, role: faculty/postdoc/student/staff)
3. Active projects or research programs
4. Key publications or highlighted papers
5. Lab resources, tools, or databases maintained by the lab
6. Collaborations mentioned
Return as structured sections. Omit any section with no content."

PART 2: Broader lab context via /learn

Invoke /learn via the Skill tool:
   skill: "learn"
   args: "{PI Name} {Institution Name} lab research focus publications collaborations --light --no-goals"

/learn will file results to inbox/. Its output summary will contain the line "Filed to: [path]".
Read the filed inbox document at that path using the Read tool.

COMBINE AND RETURN exactly this format (no extra text):

RESEARCH_THEMES:
- [theme or focus area]

GROUP_MEMBERS:
- name: [name]
  role: [faculty|postdoc|student|staff|unknown]

ACTIVE_PROJECTS:
- [project name and brief description]

KEY_PUBLICATIONS:
- [citation or title]

LAB_RESOURCES:
- [tool, database, or resource maintained by the lab]

COLLABORATIONS:
- [collaborator or institution]

LAB_WEBSITE_URL: {url or "not provided"}
INBOX_FILE: [path to the inbox file /learn created]
SOURCE: [website|learn|both] (indicate which sources contributed)

Merge findings from both parts. Deduplicate. If WebFetch and /learn disagree, include both with source attribution. If WebFetch fails (timeout, 403), proceed with /learn results only.
```

---

## A2: Department and Center Enrichment

**Agent config:** subagent_type: "general-purpose", model: "sonnet"
**Condition:** Departments or Centers show "--" in scan results.

**Prompt template:**

```
You are enriching institutional context during /onboard. Your job:

1. Invoke /learn via the Skill tool:
   skill: "learn"
   args: "{PI Name} {Institution Name} faculty profile departments centers affiliations --light --no-goals"

2. /learn will file results to inbox/. Its output summary will contain the line "Filed to: [path]".
   Extract that file path from /learn's output.

3. Read the filed inbox document at that path using the Read tool.

4. From the document content, extract:
   - Department names: formal department affiliations (e.g., "Department of Neurology")
   - For each department, classify its type:
     basic_science (fundamental research, e.g., Oncological Sciences, Neuroscience)
     clinical (patient-facing, e.g., Neurology, Dermatology, Pathology)
     translational (bridging basic and clinical)
     computational (data/AI, e.g., Artificial Intelligence and Human Health)
   - Center affiliations: research centers, institutes, or programs
   - External affiliations: institutions outside the primary one

5. Return EXACTLY this format (no extra text):

DEPARTMENTS:
- name: [department name]
  type: [basic_science|clinical|translational|computational]

CENTERS:
- [center or institute name]

EXTERNAL_AFFILIATIONS:
- [institution name]

INBOX_FILE: [path to the inbox file /learn created]

If /learn fails or returns no useful results, return:
DEPARTMENTS: none found
CENTERS: none found
EXTERNAL_AFFILIATIONS: none found
```

---

## A3: Institutional Resources

**Agent config:** subagent_type: "general-purpose", model: "sonnet"
**Condition:** Scan produced thin infrastructure (few platforms, no core facilities).

**Prompt template:**

```
You are enriching institutional context during /onboard. Your job:

1. Invoke /learn via the Skill tool:
   skill: "learn"
   args: "{Institution Name} research infrastructure core facilities HPC computing platforms shared resources --light --no-goals"

2. /learn will file results to inbox/. Its output summary will contain the line "Filed to: [path]".
   Extract that file path from /learn's output.

3. Read the filed inbox document at that path using the Read tool.

4. From the document content, extract infrastructure organized by category:
   - Compute: HPC clusters, GPU resources, cloud accounts (include scheduler type if mentioned)
   - Core facilities: shared instrumentation and service labs relevant to {domain}
   - Platforms: data management, clinical, and research platforms
   - Shared resources: biobanks, repositories, registries, shared datasets

5. Return EXACTLY this format (no extra text):

COMPUTE:
- name: [cluster/resource name]
  type: [HPC|cloud|GPU]
  scheduler: [LSF|SLURM|PBS|unknown]
  notes: [access notes if any]

CORE_FACILITIES:
- [facility name and brief description]

PLATFORMS:
- [platform name and brief description]

SHARED_RESOURCES:
- [resource name and brief description]

INBOX_FILE: [path to the inbox file /learn created]

If /learn fails or returns no useful results, return the categories with "none found".
```

---

## B1: Department-Specific Resources

**Agent config:** subagent_type: "general-purpose", model: "sonnet"
**Condition:** A2 returned departments. Run AFTER Phase A completes.
**Limit:** Top 2 departments most relevant to the lab's research domain.

**Prompt template:**

```
You are enriching department-level context during /onboard. Your job:

1. Invoke /learn via the Skill tool:
   skill: "learn"
   args: "{Institution Name} {Department Name} research resources laboratories core facilities --light --no-goals"

2. /learn will file results to inbox/. Its output summary will contain the line "Filed to: [path]".
   Extract that file path from /learn's output.

3. Read the filed inbox document at that path using the Read tool.

4. From the document content, extract department-specific resources:
   - Labs: named research labs within the department
   - Instrumentation: specialized equipment or platforms
   - Programs: training programs, consortia, or collaborative initiatives
   - Resources: databases, tools, or services specific to this department

5. Return EXACTLY this format (no extra text):

DEPARTMENT: [department name]

LABS:
- [lab name and PI if mentioned]

INSTRUMENTATION:
- [equipment or platform]

PROGRAMS:
- [program name and brief description]

RESOURCES:
- [resource name and brief description]

INBOX_FILE: [path to the inbox file /learn created]

If /learn fails or returns no useful results, return the categories with "none found".
```

---

## C1: Data Platform Enrichment

**Agent config:** subagent_type: "general-purpose", model: "sonnet"
**Condition:** Data platforms detected in project scan (Data Layers, conventions). Run in Turn 2b after user confirms projects.
**Limit:** Top 4 most prominent platforms across all projects.

**Prompt template:**

```
You are enriching data platform context during /onboard. Your job:

1. Invoke /learn via the Skill tool:
   skill: "learn"
   args: "{Platform Name} research data platform documentation data fields access methods publications --light --no-goals"

2. /learn will file results to inbox/. Its output summary will contain the line "Filed to: [path]".
   Extract that file path from /learn's output.

3. Read the filed inbox document at that path using the Read tool.

4. From the document content, extract platform details:
   - Platform type: biobank, proteomics, genomics, imaging, clinical, survey, registry, etc.
   - Available data: key data fields, assays, or measurements
   - Scale: sample size, cohort size, or coverage if mentioned
   - Access method: application process, DUA, open access, institutional, etc.
   - Limitations: known caveats, batch effects, missing data patterns
   - Key references: seminal papers or documentation URLs

5. Return EXACTLY this format (no extra text):

PLATFORM: [platform name]
TYPE: [biobank|proteomics|genomics|imaging|clinical|survey|registry|other]

AVAILABLE_DATA:
- [data field or assay and brief description]

SCALE: [sample size or coverage, or "unknown"]

ACCESS:
- method: [application|DUA|open|institutional|commercial|unknown]
  notes: [access details if any]

LIMITATIONS:
- [known caveat or limitation]

KEY_REFERENCES:
- [citation or documentation URL]

INBOX_FILE: [path to the inbox file /learn created]

If /learn fails or returns no useful results, return the categories with "unknown" or "none found".
```
