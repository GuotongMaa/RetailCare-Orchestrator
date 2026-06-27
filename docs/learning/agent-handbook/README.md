# AI Agent Handbook RAG Corpus

This folder turns the PDF handbook into a page-aware local reference corpus for
RetailCare learning sessions.

## Source

- PDF: `/Users/maguotong/Desktop/编程学习/海云大模型AIAgent应用面试通关手册.pdf`
- Title: `海云大模型AIAgent应用面试通关手册`
- Pages: 405 physical PDF pages
- Corpus: `pages.jsonl`

Page numbers in this corpus use physical PDF page numbers, starting from the
cover as page 1. When citing the handbook, use this format:

```text
资料第 54 页: RAG 的定义...
```

## How To Use

Before answering AI Agent learning, interview, or RetailCare architecture
questions, search the corpus:

```bash
python3 learning_lab/rag/search_agent_handbook.py "RAG 多租户安全" --top 5
python3 learning_lab/rag/search_agent_handbook.py "工具调用 Function Calling MCP" --top 5
```

Then answer by combining:

1. The handbook evidence with page citations.
2. The RetailCare codebase and docs.
3. Current official docs when the topic is time-sensitive, especially tool
   versions, model names, APIs, salaries, or live hiring requirements.

## Files

- `metadata.json`: source metadata and section ranges.
- `pages.jsonl`: one JSON object per PDF page, with `page`, `section`, `source`,
  and cleaned `text`.
- `section-map.md`: the handbook module map and how each part connects to
  RetailCare study.
- `learning_lab/rag/search_agent_handbook.py`: lightweight local retriever.

## Retrieval Rules

- Prefer citing the most relevant 2-5 pages, not dumping long excerpts.
- If the user asks "按资料说", cite handbook pages explicitly.
- If a page is only loosely related, say it is an inference from the source.
- For implementation work, use the handbook as conceptual guidance; use the
  repository tests and business rules as the source of truth for actual behavior.

