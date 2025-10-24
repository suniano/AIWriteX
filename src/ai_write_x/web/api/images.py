#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图片生成相关 API"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.ai_write_x.tools.image_generator import ImageGenerator, ImageGenerationResult
from src.ai_write_x.utils import log

router = APIRouter(prefix="/api/images", tags=["images"])


def _run_generation(
    prompt: str,
    provider: Optional[str],
    overrides: Optional[Dict[str, Any]] = None,
) -> ImageGenerationResult:
    generator = ImageGenerator()
    sanitized_prompt = prompt.strip() or generator.get_default_prompt()

    try:
        return generator.generate(
            sanitized_prompt,
            provider=provider,
            overrides=overrides or {},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        log.print_log(f"图片生成失败: {exc}", "error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(default_factory=ImageGenerator.get_default_prompt)
    provider: Optional[str] = None
    overrides: Optional[Dict[str, Any]] = None


@router.post("/generate")
async def generate_image(request: ImageGenerationRequest):
    result = _run_generation(request.prompt, request.provider, request.overrides)
    return {
        "status": "success",
        "message": "图片生成成功",
        "data": {
            "provider": result.provider,
            "prompt": request.prompt.strip() or ImageGenerator.get_default_prompt(),
            "image_url": result.remote_url,
            "local_path": result.local_path,
        },
    }


class ImageTestRequest(BaseModel):
    provider: Optional[str] = None
    prompt: Optional[str] = None


@router.post("/test")
async def test_image_api(request: ImageTestRequest):
    prompt = request.prompt or ImageGenerator.get_default_prompt()
    result = _run_generation(prompt, request.provider)

    display_provider = request.provider or result.provider
    return {
        "status": "success",
        "message": f"{display_provider} 图片生成测试成功",
        "data": {
            "provider": result.provider,
            "prompt": prompt,
            "image_url": result.remote_url,
            "local_path": result.local_path,
        },
    }
