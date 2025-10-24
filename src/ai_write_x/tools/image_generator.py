#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""统一的图片生成服务封装"""

from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Dict, Optional

import requests
from dashscope import ImageSynthesis

from src.ai_write_x.config.config import Config
from src.ai_write_x.utils import log, utils
from src.ai_write_x.utils.path_manager import PathManager


DEFAULT_NEGATIVE_PROMPT = "低分辨率、错误、最差质量、低质量、残缺、多余的手指、比例不良"
DEFAULT_SD_ENDPOINT = "https://sd.exacg.cc/api/v1/generate_image"
DEFAULT_TEST_PROMPT = "a beautiful anime girl, detailed face, high quality"


@dataclass
class ImageGenerationResult:
    """封装图片生成结果"""

    provider: str
    prompt: str
    remote_url: Optional[str] = None
    local_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def get_best_url(self) -> Optional[str]:
        """返回最适合作为后续处理的图片地址"""

        return self.local_path or self.remote_url


class ImageGenerator:
    """统一的图片生成入口"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.get_instance()
        self.image_dir = PathManager.get_image_dir()
        self._provider_handlers = {
            "ali": self._generate_via_ali,
            "picsum": self._generate_via_picsum,
            "sd_exacg": self._generate_via_sd_exacg,
        }

    @staticmethod
    def get_default_prompt() -> str:
        return DEFAULT_TEST_PROMPT

    def get_provider_settings(self, provider: Optional[str] = None) -> Dict[str, Any]:
        provider = provider or self.config.img_api_type
        return self.config.get_img_api_settings(provider)

    def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> ImageGenerationResult:
        """根据配置调用对应的图片生成服务"""

        provider = provider or self.config.img_api_type
        handler = self._provider_handlers.get(provider)
        if not handler:
            raise ValueError(f"不支持的图片生成服务: {provider}")

        settings = self.get_provider_settings(provider).copy()
        overrides = overrides or {}

        # 允许通过 size 统一设置宽高，例如 "1024*1024"
        size_value = overrides.get("size")
        if isinstance(size_value, str) and "*" in size_value:
            width, height = self._parse_size(size_value)
            overrides.setdefault("width", width)
            overrides.setdefault("height", height)

        for key, value in overrides.items():
            if value is not None:
                settings[key] = value

        result = handler(prompt, settings)

        # 如果只有远程地址，尝试下载保存一份副本
        if result.remote_url and not result.local_path:
            try:
                result.local_path = utils.download_and_save_image(
                    result.remote_url, str(self.image_dir)
                )
            except Exception as exc:  # pragma: no cover - 下载失败时记录日志但不中断
                log.print_log(f"下载图片副本失败: {exc}", "warning")

        return result

    @staticmethod
    def _parse_size(size_value: str) -> tuple[int, int]:
        try:
            width_str, height_str = size_value.lower().split("*")
            return int(width_str), int(height_str)
        except Exception as exc:
            raise ValueError(f"无效的图片尺寸参数: {size_value}") from exc

    def _generate_via_ali(
        self, prompt: str, settings: Dict[str, Any]
    ) -> ImageGenerationResult:
        api_key = settings.get("api_key")
        model = settings.get("model")
        size = settings.get("size", "1024*1024")
        negative_prompt = settings.get("negative_prompt", DEFAULT_NEGATIVE_PROMPT)

        if not api_key:
            raise ValueError("未配置阿里通义万象 API KEY")
        if not model:
            raise ValueError("未配置阿里通义万象模型名称")

        try:
            rsp = ImageSynthesis.call(
                api_key=api_key,
                model=model,
                prompt=prompt,
                negative_prompt=negative_prompt,
                n=1,
                size=size,
            )
            if rsp.status_code != HTTPStatus.OK:
                raise RuntimeError(
                    f"生成失败: status={rsp.status_code}, code={rsp.code}, message={rsp.message}"
                )

            result = rsp.output.results[0]
            remote_url = result.url
            local_path = utils.download_and_save_image(remote_url, str(self.image_dir))

            return ImageGenerationResult(
                provider="ali",
                prompt=prompt,
                remote_url=remote_url,
                local_path=local_path,
                metadata={"raw": rsp.to_dict()},
            )
        except Exception as exc:
            raise RuntimeError(f"阿里图片生成失败: {exc}") from exc

    def _generate_via_picsum(
        self, prompt: str, settings: Dict[str, Any]
    ) -> ImageGenerationResult:
        width = int(settings.get("width", 1024))
        height = int(settings.get("height", 1024))
        download_url = f"https://picsum.photos/{width}/{height}?random=1"

        local_path = utils.download_and_save_image(download_url, str(self.image_dir))
        return ImageGenerationResult(
            provider="picsum",
            prompt=prompt,
            remote_url=download_url,
            local_path=local_path,
            metadata={"width": width, "height": height},
        )

    def _generate_via_sd_exacg(
        self, prompt: str, settings: Dict[str, Any]
    ) -> ImageGenerationResult:
        api_key = settings.get("api_key")
        if not api_key:
            raise ValueError("未配置 SD·ExACG API KEY")

        endpoint = settings.get("endpoint", DEFAULT_SD_ENDPOINT)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        def _to_int(value: Any, default: int) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def _to_float(value: Any, default: float) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        payload: Dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": settings.get("negative_prompt", ""),
            "width": _to_int(settings.get("width", 512), 512),
            "height": _to_int(settings.get("height", 512), 512),
            "steps": _to_int(settings.get("steps", 20), 20),
            "cfg": _to_float(settings.get("cfg", 7.0), 7.0),
            "model_index": _to_int(settings.get("model_index", 0), 0),
            "seed": _to_int(settings.get("seed", -1), -1),
        }

        image_source = settings.get("image_source")
        if image_source:
            payload["image_source"] = image_source

        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise RuntimeError(f"SD·ExACG 请求失败: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError("SD·ExACG 返回了无效的JSON数据") from exc

        if not data.get("success", False):
            error_message = data.get("error") or data.get("message") or "图像生成失败"
            raise RuntimeError(error_message)

        image_url = data.get("data", {}).get("image_url")
        if not image_url:
            raise RuntimeError("SD·ExACG 响应缺少图片地址")

        local_path = utils.download_and_save_image(image_url, str(self.image_dir))

        return ImageGenerationResult(
            provider="sd_exacg",
            prompt=prompt,
            remote_url=image_url,
            local_path=local_path,
            metadata={"response": data},
        )


def decode_article_id(article_id: str) -> str:
    """兼容历史数据的文章ID解码，供外部使用"""

    padded = article_id + "=" * (-len(article_id) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")


__all__ = ["ImageGenerator", "ImageGenerationResult", "DEFAULT_TEST_PROMPT"]
