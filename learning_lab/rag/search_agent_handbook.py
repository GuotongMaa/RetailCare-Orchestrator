#!/usr/bin/env python3
"""Search the page-aware AI Agent handbook corpus.

This is a lightweight local retriever for study sessions. It uses only the
standard library so it works even when the project environment is not installed.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = REPO_ROOT / "docs" / "learning" / "agent-handbook" / "pages.jsonl"
WORD_RE = re.compile(r"[a-z0-9_+#./-]+|[\u2e80-\u9fff]+", re.IGNORECASE)


@dataclass(frozen=True)
class PageDoc:
    page: int
    section: str
    text: str
    normalized_text: str
    tokens: Counter[str]


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def tokenize(text: str) -> list[str]:
    normalized = normalize(text)
    tokens: list[str] = []
    for match in WORD_RE.finditer(normalized):
        term = match.group(0)
        if re.fullmatch(r"[\u2e80-\u9fff]+", term):
            if len(term) <= 2:
                tokens.append(term)
            else:
                tokens.append(term)
                tokens.extend(term[i : i + 2] for i in range(len(term) - 1))
                tokens.extend(term[i : i + 3] for i in range(len(term) - 2))
        else:
            tokens.append(term)
    return tokens


def load_docs(path: Path) -> list[PageDoc]:
    docs: list[PageDoc] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            text = record.get("text", "")
            normalized_text = normalize(text)
            docs.append(
                PageDoc(
                    page=int(record["page"]),
                    section=record.get("section", ""),
                    text=unicodedata.normalize("NFKC", text),
                    normalized_text=normalized_text,
                    tokens=Counter(tokenize(text)),
                )
            )
    return docs


def idf_by_token(docs: list[PageDoc]) -> dict[str, float]:
    doc_count = len(docs)
    dfs: Counter[str] = Counter()
    for doc in docs:
        dfs.update(doc.tokens.keys())
    return {token: math.log((doc_count + 1) / (df + 1)) + 1.0 for token, df in dfs.items()}


def phrases(query: str) -> list[str]:
    normalized = normalize(query)
    parts = [normalized]
    parts.extend(part for part in re.split(r"\s+", normalized) if len(part) >= 2)
    return list(dict.fromkeys(parts))


def score_doc(doc: PageDoc, query: str, query_tokens: Counter[str], idf: dict[str, float]) -> float:
    score = 0.0
    for token, weight in query_tokens.items():
        tf = doc.tokens.get(token, 0)
        if tf:
            score += min(tf, 8) * idf.get(token, 1.0) * weight

    for phrase in phrases(query):
        if len(phrase) < 2:
            continue
        hits = doc.normalized_text.count(phrase)
        if hits:
            score += min(hits, 5) * (8.0 + min(len(phrase), 20) / 2)

    return score


def best_snippet(doc: PageDoc, query: str, context: int) -> str:
    text = re.sub(r"\s+", " ", doc.text).strip()
    normalized_text = normalize(text)
    candidates = [phrase for phrase in phrases(query) if len(phrase) >= 2]
    candidates.extend(tokenize(query))

    best_index = -1
    for candidate in candidates:
        best_index = normalized_text.find(candidate)
        if best_index != -1:
            break

    if best_index == -1:
        return text[: context * 2].strip()

    start = max(best_index - context, 0)
    end = min(best_index + context, len(text))
    prefix = "..." if start else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


def search(docs: list[PageDoc], query: str, limit: int) -> list[tuple[float, PageDoc]]:
    query_tokens = Counter(tokenize(query))
    idf = idf_by_token(docs)
    ranked = [
        (score_doc(doc, query, query_tokens, idf), doc)
        for doc in docs
    ]
    ranked = [(score, doc) for score, doc in ranked if score > 0]
    ranked.sort(key=lambda item: (item[0], -item[1].page), reverse=True)
    return ranked[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Search query, for example: RAG 多租户安全")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--context", type=int, default=120)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    if not args.corpus.exists():
        print(f"Corpus not found: {args.corpus}", file=sys.stderr)
        return 2

    docs = load_docs(args.corpus)
    results = search(docs, args.query, args.top)

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "page": doc.page,
                        "section": doc.section,
                        "score": round(score, 3),
                        "snippet": best_snippet(doc, args.query, args.context),
                    }
                    for score, doc in results
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(f"Query: {args.query}")
    print(f"Corpus: {args.corpus} ({len(docs)} pages)")
    if not results:
        print("No matches.")
        return 1

    for rank, (score, doc) in enumerate(results, start=1):
        section = f" | {doc.section}" if doc.section else ""
        print(f"\n{rank}. p.{doc.page}{section} | score={score:.2f}")
        print(best_snippet(doc, args.query, args.context))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
