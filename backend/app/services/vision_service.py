"""Privacy-preserving image intake and optional multimodal analysis.

Two transparent modes are supported:
1. remote OpenAI-compatible vision model when VISION_API_KEY is configured;
2. local colour/composition analysis with Pillow when it is not.
The local mode never claims to recognise room type, materials or structure.
"""
from __future__ import annotations

import base64
import io
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

from ..core.config import settings

ALLOWED = {"image/jpeg", "image/png", "image/webp"}
MAX_PIXELS = 40_000_000


class VisionError(ValueError):
    pass


STYLE_LABELS = {
    "modern": "现代风格",
    "contemporary": "当代风格",
    "minimalist": "极简风格",
    "traditional": "传统风格",
    "rustic": "乡村风格",
    "industrial": "工业风格",
    "scandinavian": "北欧风格",
    "vintage": "复古风格",
}


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def _local_features(image: Image.Image) -> dict[str, Any]:
    rgb = image.convert("RGB")
    small = rgb.copy()
    small.thumbnail((480, 480))
    gray = ImageOps.grayscale(small)
    stat = ImageStat.Stat(small)
    gray_stat = ImageStat.Stat(gray)
    hsv = small.convert("HSV")
    saturation = ImageStat.Stat(hsv).mean[1] / 255
    brightness = gray_stat.mean[0] / 255
    contrast = gray_stat.stddev[0] / 255
    warmth = (stat.mean[0] - stat.mean[2]) / 255

    edges = gray.filter(ImageFilter.FIND_EDGES)
    edge_stat = ImageStat.Stat(edges)
    edge_density = min(1.0, edge_stat.mean[0] / 55)

    quantized = small.resize((120, 120)).quantize(colors=5, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette() or []
    counts = sorted(quantized.getcolors(), reverse=True) if quantized.getcolors() else []
    dominant = []
    for count, index in counts[:5]:
        base = index * 3
        color = tuple(palette[base : base + 3]) if len(palette) >= base + 3 else (0, 0, 0)
        dominant.append({"hex": _hex(color), "share_pct": round(count / 14400 * 100, 1)})

    if brightness < 0.32:
        light = "画面整体偏暗，可能存在曝光不足或拍摄时段较晚"
    elif brightness > 0.76:
        light = "画面整体明亮，但高光区域可能过曝"
    else:
        light = "画面亮度处于中等范围"
    if contrast < 0.16:
        contrast_text = "明暗层次较平，空间纵深不易判断"
    elif contrast > 0.32:
        contrast_text = "明暗对比明显，空间层次较清晰"
    else:
        contrast_text = "明暗层次适中"
    temperature = "偏暖" if warmth > 0.035 else "偏冷" if warmth < -0.035 else "中性"
    observations = [
        light,
        contrast_text,
        f"色彩整体{temperature}，主色占比最高的是 {dominant[0]['hex'] if dominant else '未知'}",
        "画面细节较丰富" if edge_density > 0.42 else "画面较为简洁或细节较少",
    ]
    return {
        "width": rgb.width,
        "height": rgb.height,
        "aspect_ratio": round(rgb.width / max(rgb.height, 1), 2),
        "orientation": "横向" if rgb.width > rgb.height * 1.05 else "纵向" if rgb.height > rgb.width * 1.05 else "近方形",
        "brightness": round(brightness, 3),
        "contrast": round(contrast, 3),
        "saturation": round(saturation, 3),
        "warmth": round(warmth, 3),
        "temperature": temperature,
        "edge_density": round(edge_density, 3),
        "dominant_colors": dominant,
        "observations": observations,
        "average_color": _hex(tuple(int(v) for v in stat.mean[:3])),
    }


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise VisionError("视觉模型未返回 JSON")
    return json.loads(text[start : end + 1])


class VisionService:
    def __init__(self) -> None:
        self.upload_dir = settings.upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def _validate(self, content: bytes, content_type: str) -> Image.Image:
        if content_type not in ALLOWED:
            raise VisionError("仅支持 JPEG、PNG 或 WebP 图片")
        if len(content) > settings.max_upload_mb * 1024 * 1024:
            raise VisionError(f"图片不能超过 {settings.max_upload_mb} MB")
        try:
            image = Image.open(io.BytesIO(content))
            image.verify()
            image = Image.open(io.BytesIO(content))
        except (UnidentifiedImageError, OSError) as exc:
            raise VisionError("无法解析图片文件") from exc
        if image.width * image.height > MAX_PIXELS:
            raise VisionError("图片像素过大")
        return image.convert("RGB")

    def ingest(self, content: bytes, content_type: str, filename: str) -> dict[str, Any]:
        image = self._validate(content, content_type)
        # Re-encode strips EXIF, GPS, camera identifiers and malicious payloads.
        image = ImageOps.exif_transpose(image)
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        image_id = uuid.uuid4().hex[:16]
        full_path = self.upload_dir / f"{image_id}.jpg"
        thumb = image.copy()
        thumb.thumbnail((720, 720), Image.Resampling.LANCZOS)
        full_path_thumb = self.upload_dir / f"{image_id}_thumb.jpg"
        image.save(full_path, "JPEG", quality=88, optimize=True, progressive=True)
        thumb.save(full_path_thumb, "JPEG", quality=84, optimize=True)
        features = _local_features(image)
        return {
            "image_id": image_id,
            "filename": Path(filename).name[:120],
            "image_url": f"/api/vision/images/{image_id}",
            "thumbnail_url": f"/api/vision/images/{image_id}?variant=thumb",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "metadata_stripped": True,
            "features": features,
            "size_kb": round(full_path.stat().st_size / 1024, 1),
        }

    def analyze(self, image_id: str) -> dict[str, Any]:
        path = self.upload_dir / f"{image_id}.jpg"
        if not path.exists():
            raise VisionError("图片不存在或已过期")
        image = Image.open(path).convert("RGB")
        features = _local_features(image)
        if settings.vision_remote_enabled:
            try:
                semantic = self._remote_analyze(image)
                mode = "remote-vision"
                model = settings.vision_model
            except Exception as exc:
                semantic = self._local_semantic(features)
                mode = "local-fallback"
                model = "Pillow colour/composition analysis"
                semantic["fallback_reason"] = f"远程视觉模型调用失败：{type(exc).__name__}"
        else:
            semantic = self._local_semantic(features)
            mode = "local-vision"
            model = "Pillow colour/composition analysis"
        result = {
            "image_id": image_id,
            "image_url": f"/api/vision/images/{image_id}",
            "thumbnail_url": f"/api/vision/images/{image_id}?variant=thumb",
            "mode": mode,
            "model": model,
            "features": features,
            "semantic": semantic,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": "图片分析仅提供可见线索，不用于判断建筑面积、结构安全、产权或实际成交价。请以现场检查和正式文件为准。",
        }
        (self.upload_dir / f"{image_id}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    def _local_semantic(self, features: dict[str, Any]) -> dict[str, Any]:
        return {
            "room_type": "无法可靠判断",
            "style": "无法可靠判断",
            "style_confidence": 0.0,
            "visible_materials": [],
            "observations": features["observations"],
            "strengths": [
                "画面亮度处于可查看范围，适合进一步人工核对" if features["brightness"] >= 0.45 else "画面偏暗，建议补充白天照片",
                "主色清晰，可用于初步了解空间色彩倾向",
            ],
            "concerns": [
                "单张照片无法判断结构、渗漏、电路或霉菌",
                "无法测量面积或确认装修材料的真实品质",
            ],
            "confidence": 0.28,
            "capability_note": "当前未配置远程多模态模型，仅进行本地图像信号分析，不推断房间类型、风格或材质。",
            "questions_for_viewing": [
                "现场核对采光、通风与噪音",
                "检查天花板、墙角、窗框是否有渗水痕迹",
                "索取屋顶、暖通与电气的维修记录",
            ],
        }

    def _remote_analyze(self, image: Image.Image) -> dict[str, Any]:
        from openai import OpenAI

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=88)
        encoded = base64.b64encode(buffer.getvalue()).decode()
        client = OpenAI(api_key=settings.vision_api_key, base_url=settings.vision_base_url)
        prompt = (
            "你是房产图片辅助分析器。请只描述照片中可见的信息，不要推断面积、结构安全、产权、学区或价格。"
            "返回严格 JSON，字段：room_type（字符串，无法判断则写无法可靠判断）、style（字符串）、"
            "style_confidence（0-1）、visible_materials（字符串数组）、observations（字符串数组，3-5条）、"
            "strengths（字符串数组）、concerns（字符串数组）、confidence（0-1）、questions_for_viewing（字符串数组，3条）。"
            "不要输出 Markdown。"
        )
        response = client.chat.completions.create(
            model=settings.vision_model,
            temperature=0.2,
            max_tokens=700,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}},
                    ],
                }
            ],
        )
        payload = _extract_json(response.choices[0].message.content or "")
        payload["capability_note"] = "远程多模态模型仅基于单张照片提供可见线索，未进行现场核验。"
        payload["confidence"] = float(max(0, min(1, payload.get("confidence", 0.5))))
        payload["style_confidence"] = float(max(0, min(1, payload.get("style_confidence", 0.4))))
        return payload

    def get_image_path(self, image_id: str, variant: str | None = None) -> Path:
        if not image_id.isalnum() or len(image_id) > 40:
            raise VisionError("非法图片 ID")
        suffix = "_thumb" if variant == "thumb" else ""
        path = self.upload_dir / f"{image_id}{suffix}.jpg"
        if not path.exists():
            raise VisionError("图片不存在")
        return path

    def get_cached(self, image_id: str) -> dict[str, Any] | None:
        path = self.upload_dir / f"{image_id}.json"
        if path.exists():
            return json.loads(path.read_text())
        return None


_vision_service: VisionService | None = None


def get_vision_service() -> VisionService:
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service
