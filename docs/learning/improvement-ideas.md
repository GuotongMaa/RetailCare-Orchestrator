# Improvement Ideas

This document records future improvement ideas only. Entries here are not yet
committed architecture decisions, implementation plans, or product requirements.

## 2026-06-22 - Self-Iterating RetailCare Agent From Historical Operations

Idea:

Can RetailCare evolve into a self-iterating agent system after launch? The system
could store historical operations in a database, then when it encounters a similar
order, similar customer intent, or similar return/refund reason, it can retrieve
and compare prior handling records before deciding the next action.

Initial thought:

- Store historical conversations, tool calls, guardrail decisions, HITL outcomes,
  final resolutions, policy citations, and customer/order context.
- For a new request, retrieve similar historical cases by order features, item
  category, reason, eligibility result, refund amount, escalation reason, and final
  outcome.
- Use retrieved cases as decision support, not as direct authority. Current policy,
  ownership checks, guardrails, and HITL still override historical precedent.
- Compare the proposed action with historical outcomes to improve consistency:
  whether to ask a clarification question, check eligibility, create a return,
  issue compensation, or escalate to a human.
- Feed post-resolution results back into the case memory so the system can improve
  over time through evaluated operational history.

Questions to explore later:

- What counts as a "similar" order or reason: embedding similarity, structured
  filters, or both?
- Which historical fields are safe and useful to retrieve without leaking private
  data?
- How do we prevent the agent from copying a past wrong decision?
- Should retrieved historical cases influence only recommendations, or also eval
  metrics and regression tests?
- How should human-reviewed outcomes become higher-trust examples than fully
  automated outcomes?

Risk note:

Historical behavior cannot replace policy. This idea should be designed as a
case-based memory and evaluation loop, with explicit safeguards against stale
policy, biased precedent, privacy leakage, and unauthorized write actions.
