#!/usr/bin/python
# -*- coding: UTF-8 -*-

import copy  # noqa 841
import asyncio  # noqa 841
import shutil  # noqa 841
from collections import deque  # noqa 841
import threading  # noqa 841
import queue  # noqa 841
import os  # noqa 841
import webbrowser  # noqa 841
import ctypes  # noqa 841
import sys  # noqa 841
import PySimpleGUI as sg  # noqa 841
import warnings  # noqa 841
import yaml  # noqa 841
import re  # noqa 841
import random  # noqa 841
from bs4 import BeautifulSoup  # noqa 841
import requests  # noqa 841
import time  # noqa 841
from typing import Optional, List, Dict  # noqa 841
from dataclasses import dataclass  # noqa 841
from enum import Enum  # noqa 841
from datetime import datetime, timedelta  # noqa 841
from io import BytesIO  # noqa 841
from http import HTTPStatus  # noqa 841
from urllib.parse import urlparse, unquote  # noqa 841
from pathlib import PurePosixPath  # noqa 841
from dashscope import ImageSynthesis  # noqa 841
import mimetypes  # noqa 841
import json  # noqa 841
import logging  # noqa 841
from enum import Enum  # noqa 841
import unicodedata  # noqa 841
from urllib.parse import quote  # noqa 841
from dateutil.relativedelta import relativedelta  # noqa 841
import html  # noqa 841
import concurrent.futures  # noqa 841
import markdown  # noqa 841
from PIL import Image  # noqa 841
import tempfile  # noqa 841
import subprocess  # noqa 841
import hashlib  # noqa 841
from peewee import CharField, DoubleField, IntegerField, Model, TextField, Case  # noqa 841
from playhouse.sqlite_ext import SqliteExtDatabase  # noqa 841
from crewai.tools import BaseTool  # noqa 841
from crewai_tools import SeleniumScrapingTool  # noqa 841
from typing import Type  # noqa 841
from pydantic import BaseModel, Field  # noqa 841
import glob  # noqa 841
from crewai import Agent, Crew, Process, Task  # noqa 841
from crewai.project import CrewBase, agent, crew, task  # noqa 841
import importlib.util  # noqa 841
from pathlib import Path  # noqa 841
import tomlkit  # noqa 841
from rich.console import Console  # noqa 841
import platform
import multiprocessing
import argparse

# 设置环境变量
os.environ["PYTHONIOENCODING"] = "utf-8"

from aiforge import AIForgeEngine  # noqa 841


def is_admin():
    """检查是否具有管理员权限（跨平台）"""
    try:
        if platform.system() == "Windows":
            return ctypes.windll.shell32.IsUserAnAdmin()
        elif platform.system() == "Darwin":  # macOS
            return True
        elif platform.system() == "Linux":
            return os.getuid() == 0
        else:
            return True
    except Exception:
        return False


def run():
    """启动GUI应用程序"""
    try:
        # 导入新的WebView GUI
        from src.ai_write_x.web.webview_gui import gui_start

        gui_start()
    except KeyboardInterrupt:
        # 捕获Ctrl+C，优雅退出
        sys.exit(0)
    except Exception as e:
        print(f"启动失败: {str(e)}")


def run_old():
    """启动GUI应用程序"""
    try:
        import src.ai_write_x.gui.MainGUI as MainGUI

        MainGUI.gui_start()
    except Exception as fallback_error:
        print(f"启动失败: {str(fallback_error)}")


def launch_ui(ui_version: int):
    """根据版本启动对应的 UI"""
    if ui_version == 1:
        run_old()
    else:
        run()


def admin_run(ui_version: int):
    """以管理员权限运行（跨平台）"""
    if platform.system() == "Windows":
        if is_admin():
            launch_ui(ui_version)
        else:
            script_path = Path(__file__).resolve()
            params = f'"{script_path}" -ui {ui_version}'
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, params, None, 1
            )
    else:
        launch_ui(ui_version)


def parse_arguments(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="AIWriteX Launcher")
    parser.add_argument(
        "-d",
        "--direct",
        action="store_true",
        help="直接启动应用（跳过提权）",
    )
    parser.add_argument(
        "-dn",
        "--direct-new",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-ui",
        type=int,
        choices=[1, 2],
        help="选择 UI 版本：1 为经典版，2 为图片版",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    multiprocessing.set_start_method("spawn", force=True)

    # 检查是否为AIForge子进程，传递执行环境
    if AIForgeEngine.handle_sandbox_subprocess(
        globals_dict=globals().copy(), sys_path=sys.path.copy()
    ):
        sys.exit(0)
    else:
        args = parse_arguments(sys.argv[1:])

        # 兼容旧的 -dn 参数，强制直接启动图片版 UI
        if args.direct_new:
            args.direct = True
            ui_version = 2 if args.ui is None else args.ui
        else:
            if args.ui is None:
                # 保持兼容：direct 时默认经典 UI，其余情况默认图片 UI
                ui_version = 1 if args.direct else 2
            else:
                ui_version = args.ui

        if args.direct:
            launch_ui(ui_version)
        else:
            admin_run(ui_version)
