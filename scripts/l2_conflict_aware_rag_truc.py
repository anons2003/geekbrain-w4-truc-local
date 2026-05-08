from __future__ import annotations

import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

import boto3

from scripts.env_config import env, load_dotenv


load_dotenv()

# Cấu hình Bedrock đọc từ env/.env. Không để profile, KB ID hoặc model thật trong source.
DEFAULT_PROFILE = None if os.getenv("AWS_EXECUTION_ENV") else env("AWS_PROFILE")
DEFAULT_REGION = env("AWS_REGION", "us-east-1")
DEFAULT_KB_ID = env("BEDROCK_KB_ID", required=True)
DEFAULT_MODEL_ID = env("BEDROCK_MODEL_ID", required=True)

# Prompt dùng cho L1/L2: chỉ trả lời từ context, cite source và nêu rõ conflict nếu có.
SYSTEM_PROMPT = """Answer using only the provided context.
- Cite source document names.
- If sources conflict, state the conflict.
- Prefer current/final sources over archived/draft sources.
- If context is insufficient, say what is missing.
"""

STOPWORDS = {
    "a", "an", "and", "are", "at", "be", "can", "do", "does", "for", "from", "has",
    "if", "in", "is", "it", "of", "on", "or", "the", "their", "they", "to", "what",
    "when", "which", "who", "why", "with", "was", "were", "that", "this",
}


def source_name(result: dict[str, Any]) -> str:
    # Bedrock chunks dùng S3 URI, còn BM25 local dùng localSource; hàm này chuẩn hóa tên source.
    if "localSource" in result:
        return result["localSource"]
    uri = result.get("location", {}).get("s3Location", {}).get("uri", "unknown-source")
    return Path(uri).name


def parse_frontmatter(text: str) -> dict[str, str]:
    # Đọc metadata YAML đơn giản ở đầu markdown để biết status current/archived/draft.
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    metadata: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip().lower()] = value.strip().strip('"').strip("'")
    return metadata


def classify_status(source: str, text: str) -> str:
    # Status giúp L2 hạ ưu tiên tài liệu archived khi có version mâu thuẫn.
    metadata = parse_frontmatter(text)
    if metadata.get("status"):
        return metadata["status"].lower()
    head = (source + "\n" + text[:500]).lower()
    if "archived" in head:
        return "archived"
    if "current" in head:
        return "current"
    return "unknown"


def rerank_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Rerank sau retrieval: archived xuống sau, còn lại ưu tiên score cao.
    def key(result: dict[str, Any]) -> tuple[int, float]:
        source = source_name(result)
        text = result.get("content", {}).get("text", "")
        status = classify_status(source, text)
        return (1 if status == "archived" else 0, -float(result.get("score", 0.0)))

    return sorted(results, key=key)


def tokenize(text: str) -> list[str]:
    # Tokenizer nhẹ cho BM25 local; giữ các token exact như service name, incident id, version.
    return [
        token
        for token in re.findall(r"[a-z0-9][a-z0-9_-]+", text.lower())
        if token not in STOPWORDS and len(token) > 2
    ]


def bm25_scores(query_terms: list[str], docs: list[list[str]], k1: float = 1.5, b: float = 0.75) -> list[float]:
    # BM25 tính độ liên quan keyword dựa trên tần suất từ trong document và độ hiếm của từ.
    if not query_terms or not docs:
        return []
    doc_count = len(docs)
    avg_len = sum(len(doc) for doc in docs) / doc_count
    counts = [Counter(doc) for doc in docs]
    doc_freq: Counter[str] = Counter()
    for count in counts:
        doc_freq.update(count.keys())
    scores = []
    for doc, count in zip(docs, counts):
        doc_len = len(doc) or 1
        score = 0.0
        for term in query_terms:
            tf = count.get(term, 0)
            if tf == 0:
                continue
            idf = math.log(1 + (doc_count - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            denom = tf + k1 * (1 - b + b * doc_len / avg_len)
            score += idf * (tf * (k1 + 1)) / denom
        scores.append(score)
    return scores


def local_keyword_results(question: str, kb_dir: str, limit: int) -> list[dict[str, Any]]:
    # Keyword supplement: quét markdown local để bù cho vector search khi câu hỏi có exact keyword.
    root = Path(kb_dir)
    if limit <= 0 or not root.exists():
        return []
    paths, texts, docs = [], [], []
    for path in root.glob("*.md"):
        text = path.read_text()
        paths.append(path)
        texts.append(text)
        docs.append(tokenize(path.stem.replace("_", " ") + "\n" + text))
    query_terms = tokenize(question)
    scored: list[tuple[float, Path, str]] = []
    for score, path, text in zip(bm25_scores(query_terms, docs), paths, texts):
        if score <= 0:
            continue
        filename_bonus = sum(1 for term in set(query_terms) if term in path.stem.lower()) * 0.75
        scored.append((score + filename_bonus, path, text))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {"localSource": path.name, "score": min(score / 25, 0.99), "retrievalMethod": "local-bm25", "content": {"text": text}}
        for score, path, text in scored[:limit]
    ]


def retrieve_chunks(kb_id: str, question: str, profile: str | None, region: str, top_k: int) -> list[dict[str, Any]]:
    # Lấy raw chunks từ Bedrock Knowledge Base Retrieve API, chưa để Bedrock tự generate.
    session = boto3.Session(profile_name=profile, region_name=region) if profile else boto3.Session(region_name=region)
    client = session.client("bedrock-agent-runtime")
    response = client.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={"text": question},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": top_k}},
    )
    return rerank_results(response.get("retrievalResults", []))


def merge_results(vector_results: list[dict[str, Any]], keyword_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Kết hợp vector retrieval + BM25, bỏ trùng source để context không bị lặp.
    merged, seen = [], set()
    for result in vector_results + keyword_results:
        source = source_name(result)
        if source in seen:
            continue
        seen.add(source)
        merged.append(result)
    return rerank_results(merged)


def build_context(results: list[dict[str, Any]]) -> str:
    # Context đưa vào Claude gồm source/status/score để model có căn cứ xử lý citation và conflict.
    blocks = []
    for index, result in enumerate(results, 1):
        source = source_name(result)
        text = result.get("content", {}).get("text", "")
        status = classify_status(source, text)
        blocks.append(f"[{index}] source={source} status={status} score={result.get('score', 0)}\n---\n{text}")
    return "\n\n".join(blocks)


def ask_claude(question: str, context: str, profile: str | None, region: str, model_id: str) -> str:
    # Gọi Claude Sonnet qua Bedrock Runtime Converse API với temperature 0 để câu trả lời ổn định.
    session = boto3.Session(profile_name=profile, region_name=region) if profile else boto3.Session(region_name=region)
    client = session.client("bedrock-runtime")
    response = client.converse(
        modelId=model_id,
        system=[{"text": SYSTEM_PROMPT}],
        messages=[{"role": "user", "content": [{"text": f"Context:\n{context}\n\nQuestion: {question}"}]}],
        inferenceConfig={"maxTokens": 1200, "temperature": 0.0},
    )
    return response["output"]["message"]["content"][0]["text"]
