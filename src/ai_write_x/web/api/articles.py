#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""文章管理 API"""

from __future__ import annotations

import base64
import json
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.ai_write_x.utils import log
from src.ai_write_x.utils.path_manager import PathManager

router = APIRouter(prefix="/api/articles", tags=["articles"])


FORMAT_LABELS = {
    ".html": "HTML",
    ".md": "Markdown",
    ".txt": "Text",
}
STATUS_LABELS = {
    "published": "已发布",
    "failed": "发布失败",
    "unpublished": "未发布",
}
SUPPORTED_PATTERNS = ("*.html", "*.md", "*.txt")


class ArticleSummary(BaseModel):
    id: str
    title: str
    filename: str
    format: str
    size_kb: float
    created_at: datetime
    updated_at: datetime
    excerpt: str
    status: str
    status_text: str


def _get_primary_article_dir() -> Path:
    """返回与当前运行模式一致的文章目录"""

    return PathManager.get_article_dir().resolve()


def _get_release_article_dir() -> Path:
    """返回打包版本默认使用的文章目录, 用于兼容历史数据"""

    system = platform.system()
    if system == "Darwin":
        base_dir = Path.home() / "Library/Application Support/AIWriteX"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            base_dir = Path(appdata) / "AIWriteX"
        else:
            base_dir = Path.home() / "AppData/Roaming/AIWriteX"
    else:
        base_dir = Path.home() / ".config/AIWriteX"

    return (base_dir / "output/article").resolve()


def _get_project_article_dir() -> Path:
    """返回项目根目录下的文章目录, 兼容源码运行时生成的文件"""

    return (Path(__file__).resolve().parents[3] / "output/article").resolve()


def _get_article_base_dirs() -> List[Tuple[str, Path]]:
    """聚合所有可能存在文章文件的目录"""

    primary_dir = _get_primary_article_dir()
    candidates: List[Tuple[str, Path]] = [("primary", primary_dir)]
    seen = {primary_dir}

    project_dir = _get_project_article_dir()
    if project_dir not in seen and project_dir.exists():
        candidates.append(("project", project_dir))
        seen.add(project_dir)

    release_dir = _get_release_article_dir()
    if release_dir not in seen and release_dir.exists():
        candidates.append(("release", release_dir))
        seen.add(release_dir)

    cwd_dir = (Path.cwd() / "output/article").resolve()
    if cwd_dir not in seen and cwd_dir.exists():
        candidates.append(("cwd", cwd_dir))
        seen.add(cwd_dir)

    return candidates


def _encode_article_id(path: Path, base_dir: Path, base_key: str) -> str:
    relative = path.relative_to(base_dir).as_posix()
    payload = relative if base_key == "primary" else f"{base_key}:{relative}"
    encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")
    return encoded.rstrip("=")


def _decode_article_id(article_id: str, base_dirs: Dict[str, Path]) -> Tuple[Path, str]:
    try:
        padded = article_id + "=" * (-len(article_id) % 4)
        relative = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
    except Exception as exc:  # pragma: no cover - 非法ID
        raise HTTPException(status_code=400, detail="非法的文章ID") from exc

    if ":" in relative:
        base_key, relative_path = relative.split(":", 1)
    else:
        base_key, relative_path = "primary", relative

    base_dir = base_dirs.get(base_key)
    if not base_dir:
        raise HTTPException(status_code=400, detail="非法的文章ID")

    candidate = (base_dir / relative_path).resolve()
    base_dir_resolved = base_dir.resolve()

    if candidate.is_dir() or base_dir_resolved not in candidate.parents and candidate != base_dir_resolved:
        raise HTTPException(status_code=400, detail="非法的文章ID")

    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="文章不存在")

    return candidate, base_key


def _load_publish_records(article_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    publish_file = article_dir / "publish_records.json"
    if not publish_file.exists():
        return {}
    try:
        return json.loads(publish_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve_publish_status(title: str, records: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
    entries = records.get(title, [])
    if not entries:
        return {"status": "unpublished", "status_text": STATUS_LABELS["unpublished"]}

    try:
        latest = max(entries, key=lambda item: item.get("publish_time", ""))
    except Exception:
        latest = entries[-1]

    status = "published" if latest.get("success") else "failed"
    return {"status": status, "status_text": STATUS_LABELS.get(status, status)}


def _extract_excerpt(path: Path, max_length: int = 160) -> str:
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        content = path.read_text(encoding="utf-8", errors="ignore")

    text = content
    if path.suffix.lower() == ".html":
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
    else:
        text = " ".join(content.split())

    if len(text) > max_length:
        return text[:max_length].rstrip() + "…"
    return text


def _build_title(path: Path) -> str:
    return path.stem.replace("_", "|")


@router.get("/", response_model=List[ArticleSummary])
async def list_articles() -> List[ArticleSummary]:
    base_dirs = _get_article_base_dirs()
    publish_records_map = {
        key: _load_publish_records(path) for key, path in base_dirs
    }

    articles: List[ArticleSummary] = []
    seen_files: set[Path] = set()

    for base_key, base_dir in base_dirs:
        for pattern in SUPPORTED_PATTERNS:
            for path in base_dir.glob(pattern):
                if not path.is_file():
                    continue

                resolved_path = path.resolve()
                if resolved_path in seen_files:
                    continue
                seen_files.add(resolved_path)

                try:
                    stats = path.stat()
                    title = _build_title(path)
                    status_info = _resolve_publish_status(
                        title, publish_records_map.get(base_key, {})
                    )

                    summary = ArticleSummary(
                        id=_encode_article_id(path, base_dir, base_key),
                        title=title,
                        filename=path.name,
                        format=FORMAT_LABELS.get(
                            path.suffix.lower(), path.suffix.lower().lstrip(".")
                        ),
                        size_kb=round(stats.st_size / 1024, 2),
                        created_at=datetime.fromtimestamp(stats.st_ctime),
                        updated_at=datetime.fromtimestamp(stats.st_mtime),
                        excerpt=_extract_excerpt(path),
                        status=status_info["status"],
                        status_text=status_info["status_text"],
                    )
                    articles.append(summary)
                except Exception as item_error:
                    log.print_log(f"解析文章失败: {path}: {item_error}", "warning")
                    continue

    articles.sort(key=lambda item: item.updated_at, reverse=True)
    return articles


@router.delete("/{article_id}")
async def delete_article(article_id: str):
    base_dirs = dict(_get_article_base_dirs())
    path, base_key = _decode_article_id(article_id, base_dirs)

    try:
        path.unlink()
    except Exception as exc:
        log.print_log(f"删除文章失败: {exc}", "error")
        raise HTTPException(status_code=500, detail="删除文章失败") from exc

    # 清理发布记录
    publish_dir = base_dirs.get(base_key, base_dirs.get("primary")) or path.parent
    publish_file = publish_dir / "publish_records.json"
    if publish_file.exists():
        try:
            records = json.loads(publish_file.read_text(encoding="utf-8"))
            title = _build_title(path)
            if title in records:
                records.pop(title, None)
                publish_file.write_text(
                    json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
                )
        except Exception:
            pass

    return {"status": "success", "message": "文章已删除"}
