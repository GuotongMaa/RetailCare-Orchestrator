# RetailCare Agent Engineering Learning Hub

This folder is the shared memory for learning RetailCare across multiple Codex
conversations. Treat it as the source of truth for the handbook-driven learning
plan, project understanding, open questions, and study outputs.

## How to Resume in a New Conversation

Start a new Codex conversation with:

```text
Please read docs/learning/README.md, docs/learning/progress.md, and
docs/learning/roadmap.md first. Then continue the handbook-driven RetailCare
learning plan from the current chapter.
```

If you want a specific chapter, use:

```text
Please read docs/learning/README.md and progress.md, then teach Chapter 04
工具调用 using the handbook pages and RetailCare codebase. Cite handbook page
numbers and update the learning notes when done.
```

## Working Rhythm

Each learning session should follow this loop:

1. Search the handbook corpus and cite the relevant PDF pages.
2. Explain the chapter concept in plain language.
3. Find and read the matching RetailCare files.
4. Run or inspect the relevant behavior through tests, demos, traces, or evals.
5. Draw the call flow, state flow, or architecture map.
6. Write an interview-ready explanation grounded in the project code.
7. Update `progress.md`, `questions.md`, and a session note.

## Files

- `learning-method.md` records the user's learning preferences and study habits.
- `developer-build-log.md` is historical background; the active plan is now the
  handbook-code roadmap.
- `roadmap.md` maps the handbook chapters to concrete RetailCare files,
  behaviors, tests, and deliverables.
- `progress.md` records the current chapter, completed work, and next actions.
- `project-map.md` explains the current architecture and key code paths.
- `glossary.md` defines agent engineering terms in this project's context.
- `questions.md` keeps unresolved learning questions.
- `decisions.md` records learning and engineering decisions.
- `improvement-ideas.md` records future ideas before they become decisions or
  implementation plans.
- `sessions/` contains per-session notes.
- `agent-handbook/` is the page-aware RAG corpus extracted from
  `海云大模型AIAgent应用面试通关手册.pdf`; use it for handbook-backed
  answers with explicit page citations.

## Current Learning Principle

RetailCare is best studied by connecting handbook theory to project evidence:

- Every concept should cite the handbook page where it appears.
- Every concept should map to real RetailCare code, docs, tests, traces, or evals.
- The goal is full project cognition: architecture, implementation, tradeoffs,
  risks, metrics, and interview expression.
- Use the handbook chapter sequence in `roadmap.md` as the active learning path.

## Isolation Rule

Keep the production demo and learning code separate.

- Production architecture lives in `src/retailcare/`, `eval/`, `tests/`, `web/`,
  and the root operational docs.
- Learning exercises, prototypes, scratch scripts, and experimental notebooks live
  in `learning_lab/`.
- Learning code may import production code for observation, but production code
  must not import from `learning_lab/`.
- Only promote a learning experiment into the main architecture after it passes
  the promotion checklist in `promotion-policy.md`.
