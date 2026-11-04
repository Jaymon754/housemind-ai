# 远程模型配置

> 默认不需要任何密钥：Agent 使用确定性本地规划器，图像页使用 Pillow 本地信号分析。  
> 本文只说明如何启用可选的 DeepSeek 与 OpenAI-compatible 视觉模型。

## 1. 配置 DeepSeek

在项目根目录的 `.env` 中填入：

```bash
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

DeepSeek 用于：

- Agent 的 Function Calling 规划与最终回答；
- RAG 在检索结果上的组织式回答（仍然必须带引用）；
- 无密钥时自动回退到本地规划器 / 本地 extractive 回答。

## 2. 配置 Vision

以阿里云 DashScope 的 Qwen-VL OpenAI-compatible 接口为例：

```bash
VISION_API_KEY=sk-...
VISION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_MODEL=qwen-vl-max
```

也可以替换成任意兼容 `/chat/completions` 的视觉服务。视觉模型只描述可见内容，不判断结构安全、面积、产权或价格。

## 3. 重启并验证

```bash
# 停止旧后端，重新加载 .env
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# 另一个终端：真实调用两个厂商做连通性检查
.venv/bin/python scripts/check_remote.py
```

成功时检查：

```bash
curl -s http://127.0.0.1:8000/api/health
```

应看到：

```json
{"llm":{"mode":"deepseek","model":"deepseek-chat"},"vision":{"mode":"remote","model":"qwen-vl-max"}}
```

失败时脚本只输出异常类型和截断信息，不打印完整密钥。

## 4. 当前验证状态

- 代码路径、模式切换、回退逻辑与前端标签已实现；
- 当前仓库没有配置真实厂商 key，因此 **真实 DeepSeek / Qwen 调用尚未在本机验证**；
- `scripts/check_remote.py` 用最小请求分别验证聊天与视觉接口，填入 key 后即可执行；
- 不要把 `.env`、key 或带 key 的日志提交到 Git。

## 5. 安全边界

- key 只从环境变量读取，`.env` 已被 `.gitignore` 忽略；
- 输出清洗会移除 `sk-...` 样式内容；
- 工具参数经过白名单与输入长度校验；远程模型不能直接访问数据库；
- 远程模型失败时，Agent 和 RAG 会显式回退，不会伪造“远程成功”。
