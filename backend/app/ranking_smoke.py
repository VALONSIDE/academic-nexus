"""Explicit opt-in live evaluation using synthetic text and an in-memory database."""

import argparse
import json
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.tenant import Tenant
from app.services.ranking import Candidate, rank


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Call SiliconFlow with synthetic academic text")
    args = parser.parse_args()
    if not args.live:
        parser.print_help()
        return
    documents = [
        Candidate("nlp", "Natural language processing, multilingual text retrieval and language models", 0),
        Candidate("vision", "Computer vision, medical image segmentation and object detection", 0),
        Candidate("ecology", "Marine biology, ocean ecology and coral reef conservation", 0),
    ]
    cases = [("中文语义检索与自然语言理解", "nlp"),
             ("医学影像分析和视觉识别", "vision"),
             ("海洋生态系统与珊瑚礁保护", "ecology")]
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    report = []
    with Session(engine, autoflush=False, expire_on_commit=False) as db:
        tenant = Tenant(slug="synthetic-smoke", name="Synthetic smoke")
        db.add(tenant); db.commit()
        for query, expected in cases:
            start = time.monotonic()
            result = rank(db, tenant.id, query, documents)
            db.commit()
            elapsed = time.monotonic() - start
            start = time.monotonic()
            cached = rank(db, tenant.id, query, documents)
            db.commit()
            top = max(result.scores, key=result.scores.get)
            report.append({"case": expected, "top": top, "mode": result.mode,
                           "pass": top == expected and result.mode == "hybrid" and cached == result,
                           "cold_seconds": round(elapsed, 3), "cached_seconds": round(time.monotonic() - start, 3)})
    engine.dispose()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not all(row["pass"] for row in report):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
