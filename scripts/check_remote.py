#!/usr/bin/env python3
"""Smoke-test optional DeepSeek and vision providers without leaking keys.

Fill `.env` first, then run:

    .venv/bin/python scripts/check_remote.py

Exit codes: 0 = both configured providers returned a response;
1 = at least one configured provider failed; 2 = no provider configured.
"""
from __future__ import annotations

import base64
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image

from backend.app.core.config import settings


def check_deepseek() -> bool | None:
    if not settings.deepseek_api_key:
        print("DeepSeek: 未配置 DEEPSEEK_API_KEY")
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url, timeout=30.0)
        response = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[{"role": "user", "content": "只回复两个字：可用。"}],
            max_tokens=8,
            temperature=0,
        )
        content = (response.choices[0].message.content or "").strip()
        print(f"DeepSeek: 可用 · {settings.deepseek_model} · {content[:40]!r}")
        return True
    except Exception as exc:  # noqa: BLE001 - diagnostic script must report provider errors
        print(f"DeepSeek: 失败 · {type(exc).__name__}: {str(exc)[:180]}")
        return False


def check_vision() -> bool | None:
    if not settings.vision_api_key:
        print("Vision: 未配置 VISION_API_KEY")
        return None
    try:
        from openai import OpenAI

        image = Image.new("RGB", (96, 96), (214, 197, 170))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=88)
        data_url = "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
        client = OpenAI(api_key=settings.vision_api_key, base_url=settings.vision_base_url, timeout=30.0)
        response = client.chat.completions.create(
            model=settings.vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "用一句中文描述这张图片的颜色。"},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            max_tokens=40,
            temperature=0,
        )
        content = (response.choices[0].message.content or "").strip()
        print(f"Vision: 可用 · {settings.vision_model} · {content[:80]!r}")
        return True
    except Exception as exc:  # noqa: BLE001 - diagnostic script must report provider errors
        print(f"Vision: 失败 · {type(exc).__name__}: {str(exc)[:180]}")
        return False


def main() -> int:
    print(f"DeepSeek endpoint: {settings.deepseek_base_url}")
    print(f"Vision endpoint:   {settings.vision_base_url}")
    results = [check_deepseek(), check_vision()]
    if all(result is None for result in results):
        print("\n没有配置任何远程模型。应用会继续使用 local-planner / 本地图像分析。")
        print("在 .env 填入 key 后重启后端，再运行本脚本。")
        return 2
    if any(result is False for result in results):
        return 1
    if all(result is True for result in results):
        print("\nDeepSeek 与 Vision 均可用；重启后端后 /api/health 会显示对应模式。")
    else:
        print("\n部分远程模式可用；未配置的 provider 会保持本地模式。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
