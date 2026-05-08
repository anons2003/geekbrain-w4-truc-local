# W4 GeekBrain AI Q&A - Local Demo

Local demo repo for W4 GeekBrain AI Q&A.

## Architecture

- FastAPI UI/API.
- L1/L2: Bedrock Knowledge Base Retrieve + local BM25 supplement + custom conflict-aware prompt.
- L3: Dynamic tool planner over SQLite + monitoring data.
- L4: Compact session memory resolves follow-up references, then calls retrieval/tools.
- Bonus A/B/C: trace UI, investigation route, KB sync script.

## Run

```bash
cd geekbrain-w4-truc-local
uv sync
cp .env.example .env
./run-local.sh
```

Sau khi copy, điền giá trị thật vào `.env` trên máy local. File `.env` đã nằm trong `.gitignore`; không đưa AWS access key hoặc secret key vào repo.

Open:

```text
http://127.0.0.1:8080
```

## Smoke Tests

L1:

```text
Who is the Team Platform lead?
```

L2:

```text
What is PaymentGW's API rate limit?
```

L3:

```text
What was PaymentGW's total cost in Q1 2026?
```

L4:

```text
Which service had the highest infrastructure cost in March 2026?
What was the main cause of the cost increase that month?
Which team is responsible?
The postmortem mentioned a review deadline. Is it overdue?
```

Do not commit real AWS access keys.
