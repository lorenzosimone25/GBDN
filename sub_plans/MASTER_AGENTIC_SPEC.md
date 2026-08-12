# GBDN A* Submission — Master Agentic Specification

This file is a compact entry point. The authoritative detailed instructions are in the accompanying workspace.

## Mission

Coordinate three agents—Math, Reviewer, and Software Engineer—to transform the current GBDN manuscript and legacy repository into a paper–code-consistent, mathematically verified, multi-split/multi-seed A* submission.

## Required reading

1. `AGENTS.md`
2. `00_ORCHESTRATOR.md`
3. `01_SCIENTIFIC_CONTRACT.md`
4. role-specific instructions
5. `05_H100_NOTEBOOK_SPEC.md`
6. `06_EXPERIMENTS_AND_STATISTICS.md`
7. `08_RESULTS_AND_ARTIFACT_SCHEMA.md`
8. `09_EXECUTION_BOARD.md`

## Core constraints

- Preserve legacy code and artifacts.
- Implement Tight GBDN, Product-sum GBDN, and GBDN+ separately.
- Align exact equations, dense oracle, sparse realization, tests, and paper.
- Do not promote perfect reconstruction alone as the main theorem; distinguish additive and adjoint reconstruction.
- Prove or reject the pointwise partition, weighted Parseval, conditioning, finite-order frame, pole, perturbation, and locality claims.
- Treat oversmoothing and oversquashing as separate. Isometry supports global information preservation, not target-specific propagation.
- Run official heterophily metrics on all fixed splits and at least three seeds.
- Use verified upstream baselines.
- Recompute every primary metric from saved predictions.
- Implement a new resumable `notebooks/gbdn_submission_h100.ipynb` that runs the submission phases successively on one H100.
- Generate paper tables and figures from immutable artifacts.
- Require adversarial reviewer approval before claim promotion.

## First action

Execute Phase 0 from `00_ORCHESTRATOR.md`, update `09_EXECUTION_BOARD.md`, and dispatch the three role prompts.
