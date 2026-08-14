# Evaluation Workflow

Use this reference when the task asks to test a skill, add evals, benchmark whether a skill helps, compare iterations, or review generated outputs.

## Prepare Test Cases

1. Create 2-3 realistic prompts first; expand later after the first iteration.
2. Save prompts to `evals/evals.json` using the schema in `references/schemas.md`.
3. For each test case, create an `eval_metadata.json` in the run workspace with the prompt and assertions.
4. Prefer objective assertions when outputs can be checked reliably; use qualitative review for subjective skills.

Minimal `evals/evals.json` shape:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": [],
      "expectations": [
        "The output satisfies the primary requirement"
      ]
    }
  ]
}
```

## Run Layout

Put results in `<skill-name>-workspace/` as a sibling to the skill directory.

Use this structure:

```text
<skill-name>-workspace/
└── iteration-1/
    └── eval-<name>/
        ├── with_skill/outputs/
        ├── without_skill/outputs/     # new skill baseline
        └── old_skill/outputs/         # existing skill baseline, if applicable
```

When improving an existing skill, copy the old version to `<workspace>/skill-snapshot/` before editing and use that as the baseline.

## Spawn Runs

For each test case, spawn the with-skill run and baseline run in the same turn where possible.

With-skill prompt template:

```text
Execute this task:
- Skill path: <path-to-skill>
- Task: <eval prompt>
- Input files: <eval files if any, or "none">
- Save outputs to: <workspace>/iteration-<N>/eval-<ID>/with_skill/outputs/
- Outputs to save: <what the user cares about>
```

Baseline prompt uses the same user prompt and saves to `without_skill/outputs/` for new skills or `old_skill/outputs/` for existing skills.

## Draft Assertions While Runs Execute

Do not just wait. Draft or refine assertions and explain them to the user.

Good assertions are:

1. Objective enough to grade consistently.
2. Written in human-readable language.
3. Specific to the value the skill is supposed to add.
4. Not so broad that baseline runs pass just as often.

Update both `eval_metadata.json` and `evals/evals.json` when adding assertions.

## Capture Timing

When a subagent completion includes `total_tokens` and `duration_ms`, immediately save it to `timing.json` in that run directory:

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

This information may not be available later, so capture it as each run completes.

## Grade Runs

Grade each run after outputs are available.

Use `agents/grader.md` for grader instructions. If an assertion is programmatically checkable, prefer a small script over manual judgment.

`grading.json` must use this field shape:

```json
{
  "expectations": [
    {
      "text": "The output includes a runnable command",
      "passed": true,
      "evidence": "Found `npm run decode` in the output."
    }
  ]
}
```

Use `text`, `passed`, and `evidence`; viewer tooling depends on these exact fields.

## Aggregate Benchmark

Run:

```bash
python scripts/aggregate_benchmark.py <workspace>/iteration-N --skill-name <name>
```

This produces `benchmark.json` and `benchmark.md` with pass rate, timing, tokens, and deltas. Put with-skill versions before baselines when generating or presenting summaries.

## Analyze Results

Read `agents/analyzer.md` for the analyst pass.

Look for:

1. Assertions that both with-skill and baseline always pass.
2. High-variance or flaky prompts.
3. Token/time tradeoffs caused by the skill.
4. Cases where the skill over-constrains or over-expands the solution.

## Review Surface

Prefer a review surface that shows qualitative outputs and quantitative benchmark data.

Use `eval-viewer/generate_review.py` if present. If it is not present, use the best fallback:

1. Present outputs inline in the conversation.
2. Generate a static HTML review page.
3. Save benchmark artifacts and ask the user to review files from disk.

In headless environments, avoid long-running local browser servers unless necessary.

## Feedback Loop

When the user is done reviewing, read `feedback.json` if a review artifact produced one.

Focus improvements on cases with specific complaints. Empty feedback usually means the output was acceptable.

After changes:

1. Rerun test cases into `iteration-<N+1>/`.
2. Include a baseline again.
3. For iteration 2+, include previous iteration artifacts in the review surface when possible.
4. Repeat until the user is satisfied or improvements stop being meaningful.
