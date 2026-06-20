---
name: business-chain
description: >
  This skill should be used when the user asks to "iterate on a feature", "refine implementation",
  "run a development loop", "build incrementally", or needs an iterative Think → Do → Review →
  Analyze cycle for complex features requiring multiple refinement iterations.
version: 1.1.0
type: workflow
triggers:
  keywords_en: [business-chain, iterate, iterative, refine, development loop, build incrementally, think do review, incremental]
  keywords_th: [วนลูป, ทำซ้ำ, พัฒนาซ้ำ, ปรับปรุงซ้ำ, วนรอบ, ทำซ้ำๆ]
---

# /business-chain — Active Iterative Development Loop

Execute an iterative Think → Do → Review → Analyze cycle until requirements are fully met.

## Usage

```
/business-chain <feature description> [max_iterations=4]
```

## Architecture

```
    ┌───────────────────────────────────────────────┐
    │                                               │
    ▼                                               │
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  THINK   │───▶│   DO     │───▶│  REVIEW  │───▶│ ANALYZE  │
│ (Plan)   │    │ (Execute)│    │ (Check)  │    │ (Learn)  │
└─────────┘    └──────────┘    └──────────┘    └──────────┘
     │                                              │
     └──────────────────────────────────────────────┘
                    Loop until DONE
```

## Iteration Workflow

```
INPUT: feature_description, max_iterations (default: 4)

FOR iteration IN 1..max_iterations:

  ## THINK Phase
  pre_analysis = Bash("llm-query --classify '{remaining_work}' --model brain")

  plan = Task(architect, "
    Iteration {N}/{max}: Plan implementation for: {feature}
    Previous results: {previous_analyze_summary}
    Remaining gaps: {gaps}
    Local LLM pre-analysis: {pre_analysis}
    Output: concrete task list with agent assignments
  ")

  ## DO Phase
  Parse plan.CHAIN_OUTPUT → identify agents needed
  FOR agent IN plan.chain.next:
    Task(agent, prompt=plan_prompt, isolation="worktree")
    # Use run_in_background=true for parallel-independent agents
  Merge worktree results

  ## REVIEW Phase
  test_result = Task(tester, "
    Test changes from iteration {N}:
    Files changed: {all_artifacts}
    Previous test results: {last_test_results}
  ")

  review_result = Task(reviewer, "
    Review changes from iteration {N}:
    Implementation: {do_phase_outputs}
    Tests: {test_result.summary}
  ")

  ## ANALYZE Phase
  analysis = Task(analyst, "
    Analyze iteration {N} results:
    - Tests: {test_result.summary}
    - Review: {review_result.summary}
    - Original requirements: {feature_description}
    Determine: DONE (all requirements met) or CONTINUE (with gap list)
    Include business_chain fields in CHAIN_OUTPUT
  ")

  llm_assessment = Bash("llm-query 'Assess completeness: {analysis.summary}' --model general --format json")

  IF analysis.business_chain.decision == "DONE":
    Task(git-ops, "Commit: feat({scope}): {description}")
    BREAK

  # Prepare next iteration
  gaps = analysis.business_chain.gaps
  previous_analyze_summary = analysis.summary

REPORT: "Completed in {N} iterations"
```

## Business Chain CHAIN_OUTPUT

Analyze phase returns special `business_chain` fields:

```json
{
  "status": "success",
  "summary": "Iteration 2: API + tests pass, UI needs refinement",
  "business_chain": {
    "iteration": 2,
    "decision": "CONTINUE",
    "completeness": 75,
    "gaps": ["UI responsive design", "Error states missing"],
    "metrics": {
      "tests_pass": 12,
      "tests_fail": 2,
      "review_issues": 1
    }
  }
}
```

## Sandbox Integration

For system file changes across iterations:

```
Iteration 1 THINK:
  architect recommends system file changes →
  claude-sandbox create {feature-name}

Iteration 1-N DO:
  workers edit overlay files (sandbox active)

Iteration N REVIEW:
  if complete → claude-sandbox promote {id}
  if not → continue editing overlay in next iteration
```

## Termination Conditions

1. **DONE**: Analyst returns `decision: "DONE"` (all requirements met)
2. **MAX ITERATIONS**: Reached max_iterations (default 4) → commit best result
3. **USER STOP**: User manually interrupts → commit current state
4. **CRITICAL FAILURE**: Unrecoverable error → report and stop

## Cost Estimation

| Iteration | Estimated Cost (Sonnet workers) |
|-----------|-------------------------------|
| 1 | ~$0.20-0.40 (initial implementation) |
| 2 | ~$0.10-0.20 (refinement) |
| 3 | ~$0.05-0.10 (polish) |
| 4 | ~$0.05-0.10 (edge cases) |
| Total | ~$0.40-0.80 per feature |
