# 提交清单

> 截止：2026-11-18 · 当前版本：1.0.0

## 必交物

| 项目 | 状态 | 位置 / 说明 |
|---|---|---|
| 公开代码仓库 | 本地已提交，待推送 | 推送到 GitHub/Gitee，确认无 `.env`、无密钥、无测试数据库 |
| README 与环境配置 | 完成 | `README.md`、`.env.example` |
| README 团队信息 | 待填写 | 学校、队伍、组别、成员、指导教师 |
| 技术文档 PDF（≤30 页） | 完成 | `docs/HouseMind_AI_技术文档.pdf` |
| 演示视频（5–8 分钟，1080p） | 完成 | `docs/HouseMind_AI_Demo_1080p.mp4`（5:37） |
| 在线部署（可选） | 未验证 | 本机无 Docker；提供 Dockerfile / Compose，单端口 8000 |
| 数据集说明 | 完成 | README 数据来源；三数据集隔离说明 |

## 发布前检查

### 仓库

- [x] `git status` 无未跟踪的 `.env`、`backend/data`、`frontend/dist`、`node_modules`
- [x] `.gitignore` 生效
- [x] 无 API key、token、个人路径泄漏（搜索 `sk-`、`API_KEY`、`/Users/`）
- [x] `LICENSE` 与数据许可说明
- [x] 至少 5 条有意义的 commit，而不是一次 “init”
- [x] README 截图路径有效
- [ ] README 团队信息已替换为真实信息
- [x] `docs/` 内 PDF 与 Markdown 一致

### 后端

- [x] `python -m pytest tests -q` 全绿（当前 25 passed）
- [x] 无密钥启动，`/api/health` 返回 `local-planner` / `local`
- [x] 配置密钥启动，Agent 切换 `deepseek`（已用真实 key 验证）
- [ ] `GET /api/meta` 的指标与新 artifacts 一致
- [ ] SQLite 自动建表；MySQL URL 可启动（可选）
- [x] `GET /api/mcp/manifest` 正常
- [x] MCP stdio server 可 `initialize`、`tools/list`、`predict_house_price` 调用
- [x] 上传非图片返回 400；超过 8MB 被拒
- [x] 提示词注入被拦截；手机号/邮箱被脱敏
- [x] SSE 事件顺序完整，浏览器断流不报错

### 前端

- [x] `pnpm build` 成功，`vue-tsc -b` 无错误
- [x] 7 个路由均可直接访问（刷新不 404）
- [x] 桌面 1440/1600 无横向溢出、无破图、无 console error
- [x] 移动 390×844 无横向溢出；侧栏可开合；表格可读
- [x] 图表在路由切换后 resize 正常
- [x] 估值/投资默认值自动跑通
- [x] Agent 深链 `?conversation=<id>` 可打开历史
- [x] 知识库自动查询与拒答都正常
- [x] 图像上传、demo 图、拖拽都正常
- [x] Qwen3-VL 远程语义验证：客厅 / 现代简约混搭北欧风 / 可见材质 / 置信度
- [x] 所有页面有“辅助参考/非评估报告”声明

### 数据与模型

- [x] `ml/artifacts/king_county_metrics.json` 与 README 一致
- [x] `ml/artifacts/rag_eval.json` 与 README 一致
- [x] `ml/reports/*.png` 已复制到 `frontend/public/reports/`
- [x] 模型卡包含数据范围、指标、限制、版本
- [x] 未把 UCI/California 指标与 King County 横向比较
- [x] 未声称“当前市场价”“中国房产定价”

### 视频

- [x] 1080p，5–8 分钟，H.264（5:37，24fps）
- [x] 声音清晰，无通知声
- [x] 画面覆盖估值 + 投资 + Agent（真实截图与数字）
- [x] 说明 DeepSeek 在线模式，并说明无密钥时可回退本地规划器
- [x] 不出现真实个人信息、密钥、测试垃圾数据
- [x] 片头/片尾有项目名
- [ ] 文件命名规范，备份到网盘（需人工上传）

### PDF

- [x] A4，19 页（含 A1–A3 评审附录）
- [x] 目录、架构图、指标表、截图、限制、复现命令
- [x] 需求分析、AI 选型/优化、创新点（A1–A3）
- [x] 中文字体嵌入，无乱码
- [x] 页码/页眉（如需要）
- [x] 文件大小合理（约 5.3 MB）
- [x] 与 README 数字一致

## 演示环境清理

```bash
# 停止后端后执行
rm -f backend/data/housemind.db
find backend/data/uploads -type f -delete
rm -rf backend/data/chroma
```

首次启动会重建表与索引。若需要保留一条演示会话，启动后用 Agent 页发一次完整问题，再录屏。

## 提交话术（仓库简介）

> HouseMind AI：面向金县住宅的 AI 估值与投资决策工作台。XGBoost + 精确 TreeSHAP + OOF 区间 + 混合 RAG + 多工具 Agent + 视觉边界。Vue 3 / FastAPI / Chroma / SQLite。无密钥也可完整演示，但绝不假装有 LLM。

## 风险与预案

| 风险 | 预案 |
|---|---|
| 演示网络中断 | 本地规划器 + 预生成会话；提前录屏备份 |
| 模型/依赖安装失败 | Docker 镜像；锁定 requirements 与 pnpm-lock |
| 评审无法访问在线地址 | 提供本地一键启动 + 视频 + 截图 |
| PDF 超过 30 页 | 压缩截图、合并章节、删附录代码 |
| 视频超时 | 按脚本删 0:35–1:25 或 4:46–5:15，保留估值/投资/Agent |
| 数据许可质疑 | README 标注来源与原始许可；不转售数据 |
