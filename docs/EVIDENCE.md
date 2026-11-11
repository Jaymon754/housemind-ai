# 运行证据 / Runtime Evidence

> 本文件记录 2026-11-12 在本机真实运行的调用结果，用于回答“是否真的实现了 Agent、RAG、LLM 与工具调用”。
> 所有结果来自运行中的 FastAPI 服务，不是 README 中的功能列表。

## 1. Agent：DeepSeek Function Calling，5 个工具

- 会话 ID：`b9c348c7-efc4-4342-8e78-ef305e3f61db`
- 模式：`deepseek`
- 事件流：`meta → status → tool_call → tool_result → token → citations → done`
- 工具轨迹：5/5

测试问题：

> 预算 40 万美元，在 98052 买一套 3 室 2 卫、1500 sqft、1985 年建的出租房，挂牌 40 万。请同时做房价预测、价格归因、区域市场分析、投资回报测算，并检索 DSCR、现金流和 Cap Rate 的方法依据，最后给结论。

| # | 工具 | 实际返回摘要 |
|---|---|---|
| 1 | `predict_house_price` | 估值 $500,200，80% 区间 $410,000–$586,500；挂牌价低于区间 |
| 2 | `explain_house_price` | TreeSHAP：纬度 +$60,980、邮编基准 +$55,973；面积 −$59,739、等级 −$45,156 |
| 3 | `analyze_market` | 98052 样本中位价 $615,000，中位单价 $274/sqft，571 笔成交 |
| 4 | `calculate_investment` | 月供 $1,896，月现金流 −$193，Cap Rate 5.11%，IRR 8.9% |
| 5 | `search_property_knowledge` | 命中 5 个片段，最高来源《净运营收入、DSCR 与盈亏平衡入住率》 |

代码路径：

- `backend/app/agent/orchestrator.py`：DeepSeek tool loop，最多 6 轮
- `backend/app/agent/tools.py`：6 个工具 schema 与 `execute_tool`
- `backend/mcp_server.py`：MCP stdio 共享同一套工具
- `frontend/src/views/AgentView.vue`：SSE 轨迹、参数、摘要、耗时

复现：

```bash
curl -N -X POST http://127.0.0.1:8000/api/agent/stream \
  -H 'Content-Type: application/json' \
  -d '{"message":"预算40万美元，在98052买一套3室2卫、1500 sqft、1985年建的出租房，挂牌40万。请同时做房价预测、价格归因、区域市场分析、投资回报测算，并检索DSCR、现金流和Cap Rate的方法依据，最后给结论。"}'
```

## 2. RAG：Top-K、分数与引用

问题：`首付比例和DSCR有什么关系？`，`top_k=6`，回答模式 `deepseek`，引用 6 条。

| 排名 | 混合分数 | 文档 | 章节 |
|---:|---:|---|---|
| 1 | 1.901 | 净运营收入、DSCR 与盈亏平衡入住率 | DSCR |
| 2 | 1.454 | 净运营收入、DSCR 与盈亏平衡入住率 | 盈亏平衡入住率 |
| 3 | 1.102 | 房贷月供、首付与摊还基础 | 本息月供公式 |
| 4 | 1.046 | 房贷月供、首付与摊还基础 | 首付与 PMI |
| 5 | 0.882 | 中国购房政策与交易常识（概览） | 因城施策 |
| 6 | 0.785 | 房地产市场周期与投资时机 | 杠杆的双刃剑 |

引用来源包含 CFPB 等公开机构页面；回答只基于下方 6 条检索片段。

复现：

```bash
curl -X POST http://127.0.0.1:8000/api/knowledge/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"首付比例和DSCR有什么关系？","top_k":6}'
```

## 3. Vision：Qwen3-VL 真实语义

- 模型：`qwen3-vl-plus`
- 模式：`remote-vision`
- 图片：`frontend/public/demo/interior.jpg`
- 结果：客厅；现代简约混搭北欧风；置信度 0.92
- 可见材质：实木、金属、皮革、织物、陶瓷、玻璃、藤编

远程调用失败时自动回退到 Pillow 本地信号，并保留 `fallback_reason`；不把本地统计伪装成语义识别。

## 4. 测试与接口

```text
25 passed in 4.50s
GET  /api/health              → model.loaded=true, rag=71 chunks, vision=remote
POST /api/valuation/analyze   → 200, estimate.value=570000, interval=479800–656200
POST /api/vision/analyze      → 200, mode=remote-vision
```

说明：测试在 `tests/conftest.py` 中显式清空外部 Key，保证离线、确定性；远程调用另用 `scripts/check_remote.py` 验证。
