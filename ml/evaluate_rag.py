"""Evaluate retrieval on a small, hand-checked gold set.

This is not a claim of general RAG quality.  It measures whether a specific
question retrieves the document section that a domain reader would expect, and
whether clearly out-of-corpus questions are refused.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.rag.engine import get_rag_service

GOLD = [
    {"q": "首付比例和DSCR有什么关系？", "expect": ["DSCR"]},
    {"q": "DSCR 低于 1.25 意味着什么？", "expect": ["DSCR"]},
    {"q": "Cap Rate 和现金回报率有什么区别？", "expect": ["资本化率", "现金回报率"]},
    {"q": "AVM 估值为什么需要参考区间？", "expect": ["AVM", "区间"]},
    {"q": "照片分析能判断结构安全吗？", "expect": ["图片", "结构"]},
    {"q": "1031 置换的基本条件是什么？", "expect": ["1031"]},
    {"q": "什么是盈亏平衡入住率？", "expect": ["盈亏平衡"]},
    {"q": "PMI 什么时候可以取消？", "expect": ["PMI"]},
    {"q": "房产税如何影响 NOI？", "expect": ["NOI", "房产税"]},
    {"q": "如何选择可比房源？", "expect": ["可比"]},
    {"q": "模型为什么用 MAE 而不是只看 R²？", "expect": ["MAE", "误差"]},
    {"q": "提示词注入应该如何防护？", "expect": ["提示词", "注入"]},
    {"q": "中国购房限购政策是什么？", "expect": ["中国", "限购"]},
    {"q": "洪水保险是强制购买的吗？", "expect": ["洪水", "保险"]},
    {"q": "租金回报率怎么计算？", "expect": ["租金", "回报"]},
    {"q": "市场周期可以精确预测吗？", "expect": ["周期"]},
    {"q": "为什么房价区间是不对称的？", "expect": ["区间", "残差"]},
    {"q": "房屋检查应该看哪些项目？", "expect": ["检查"]},
    {"q": "什么是公平住房与代理变量？", "expect": ["公平", "代理"]},
    {"q": "出售房屋的交易成本包括什么？", "expect": ["交易成本", "出售"]},
]

OUT_OF_SCOPE = [
    "如何更换汽车轮胎？",
    "请推荐一款适合玩游戏的显卡。",
    "明天北京会下雨吗？",
    "怎样制作提拉米苏？",
]


def main() -> None:
    rag = get_rag_service()
    rows = []
    hits = {1: 0, 3: 0, 5: 0}
    for item in GOLD:
        results = rag.search(item["q"], top_k=5)
        labels = [f"{r['title']} {r['section']} {r['content']}" for r in results]
        ranks = []
        for rank, label in enumerate(labels, 1):
            if any(term.lower() in label.lower() for term in item["expect"]):
                ranks.append(rank)
        best = min(ranks) if ranks else None
        for k in hits:
            if best is not None and best <= k:
                hits[k] += 1
        rows.append(
            {
                "question": item["q"],
                "expected_terms": item["expect"],
                "rank": best,
                "top1": labels[0][:260] if labels else None,
                "top3": [label[:220] for label in labels[:3]],
            }
        )

    refusals = []
    for question in OUT_OF_SCOPE:
        answer = rag.answer(question, top_k=3)
        refusals.append(
            {
                "question": question,
                "results": len(answer["results"]),
                "refused": len(answer["results"]) == 0,
            }
        )

    total = len(GOLD)
    metrics = {
        "questions": total,
        "hit_at_1": round(hits[1] / total * 100, 1),
        "hit_at_3": round(hits[3] / total * 100, 1),
        "hit_at_5": round(hits[5] / total * 100, 1),
        "out_of_scope_questions": len(OUT_OF_SCOPE),
        "refusal_rate": round(sum(1 for r in refusals if r["refused"]) / len(OUT_OF_SCOPE) * 100, 1),
    }
    payload = {
        "metrics": metrics,
        "gold_set": rows,
        "out_of_scope": refusals,
        "method": "hand-checked retrieval gold set; hit = expected section in top-k",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    path = Path("ml/artifacts/rag_eval.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"wrote {path}")

    misses = [row for row in rows if row["rank"] is None]
    if misses:
        print("\nMISSES")
        for row in misses:
            print("-", row["question"], "->", row["top1"])


if __name__ == "__main__":
    main()
