"""Offline retrieval evaluation scaffold.

Dataset format: [{"question": "...", "expected_document_ids": ["uuid"]}].
Run against a populated local stack: python scripts/evaluate.py --dataset eval.json
"""
import argparse
import asyncio
import json
from uuid import UUID
from app.db import SessionLocal
from app.services.retrieval import retrieve


async def main(dataset: str) -> None:
    cases = json.loads(open(dataset, encoding="utf-8").read())
    reciprocal_ranks = []
    async with SessionLocal() as session:
        for case in cases:
            found, _ = await retrieve(session, case["question"], None, 10)
            expected = {UUID(value) for value in case["expected_document_ids"]}
            rank = next((i for i, hit in enumerate(found, 1) if hit.chunk.document_id in expected), None)
            reciprocal_ranks.append(1 / rank if rank else 0)
    print(json.dumps({"cases": len(cases), "mrr@10": sum(reciprocal_ranks) / len(cases) if cases else 0}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    args = parser.parse_args()
    asyncio.run(main(args.dataset))
