#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""

主界面

"""

import time
import queue
import threading
import os
import webbrowser
from collections import deque

import PySimpleGUI as sg
from . import ConfigEditor
from src.ai_auto_wxgzh import crew_main
from src.ai_auto_wxgzh.utils import comm
from src.ai_auto_wxgzh.utils import utils
from src.ai_auto_wxgzh.utils import log


__author__ = "iniwaper@gmail.com"
__copyright__ = "Copyright (C) 2025 iniwap"
# __date__ = "2025/04/17"


class MainGUI(object):
    def __init__(self):
        self._log_list = []
        self._is_running = False  # 跟踪任务状态
        self._update_queue = comm.get_update_queue()
        self._log_buffer = deque(maxlen=100)
        self._ui_log_path = utils.get_log_path("UI")
        # 配置 CrewAI 日志处理器
        log.setup_logging("crewai", self._update_queue)

        # 设置主题
        sg.theme("systemdefault")

        menu_list = [
            ["配置", ["打开配置"]],
            ["文件", ["日志", "文章"]],
            ["帮助", ["帮助", "关于", "官网"]],
        ]

        layout = [
            [
                sg.Menu(
                    menu_list,
                )
            ],
            [
                sg.Image(
                    s=(640, 200),
                    filename=utils.get_res_path("UI\\bg.png", os.path.dirname(__file__)),
                    key="-BG-IMG-",
                    expand_x=True,
                )
            ],
            [
                sg.Push(),  # 左侧占位
                sg.Button(button_text="开始执行", size=(12, 2), key="-START_BTN-"),
                # sg.Button(button_text="结束执行", size=(12, 2), key="-STOP_BTN-"),
                sg.Push(),  # 右侧占位
            ],
            [
                sg.Text("——" * 20, size=(60, 1), text_color="gray"),
                sg.Push(),
            ],
            [
                sg.Text("日志:", size=(6, 1)),
                sg.Spin([10, 20, 50, 100, 200, 500, 1000], initial_value=100, key="-LOG_LIMIT-"),
                sg.Button("设置显示条数", key="-SET_LOG_LIMIT-"),
                sg.Button("清空日志", key="-CLEAR_LOG-"),
            ],
            [
                sg.Push(),  # 左侧占位
                sg.Multiline(size=(100, 18), key="-STATUS-", disabled=True, autoscroll=True),
                sg.Push(),  # 右侧占位
            ],
        ]

        self._window = sg.Window(
            "微信公众号AI工具 v1.0",
            layout,
            default_element_size=(12, 1),
            size=(640, 640),  # 展开650
            icon=self.__get_icon(),
        )

    def __get_icon(self):
        return utils.get_res_path("UI\\icon.ico", os.path.dirname(__file__))

    def __gui_config_start(self):
        ConfigEditor.gui_start()

    def __save_ui_log(self, log_entry):
        with open(self._ui_log_path, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
            f.flush()

    # 处理消息队列
    def process_queue(self):
        try:
            msg = self._update_queue.get_nowait()
            if msg["type"] == "progress":
                self._window["-PROGRESS-"].update(f"{msg['value']}%")
                self._window["-PROGRESS_BAR-"].update(msg["value"])
            elif msg["type"] == "status":
                # 追加日志到缓冲区
                if msg["value"].startswith("PRINT:"):
                    log_entry = f"[{time.strftime('%H:%M:%S')}][PRINT]: {msg['value'][6:]}"
                elif msg["value"].startswith("FILE_LOG:"):
                    log_entry = f"[{time.strftime('%H:%M:%S')}][FILE]: {msg['value'][9:]}"
                elif msg["value"].startswith("LOG:"):
                    log_entry = f"[{time.strftime('%H:%M:%S')}][LOG]: {msg['value']}"
                else:
                    log_entry = (
                        f"[{time.strftime('%H:%M:%S')}] [{msg['type'].upper()}]: {msg['value']}"
                    )
                self._log_buffer.append(log_entry)
                self.__save_ui_log(log_entry)
                # 更新 Multiline，显示所有日志
                self._window["-STATUS-"].update("\n".join(self._log_buffer), append=False)
                if msg["value"] in ["任务完成！", "任务被终止"]:
                    self._window["-START_BTN-"].update(disabled=False)
                    self._window["-STOP_BTN-"].update(disabled=True)
            elif msg["type"] == "error":
                sg.popup_error(f"任务错误: {msg['value']}", title="错误")
                self._window["-START_BTN-"].update(disabled=False)
                self._window["-STOP_BTN-"].update(disabled=True)
        except queue.Empty:
            pass

    def run(self):
        while True:
            event, values = self._window.read(timeout=100)
            if event == sg.WIN_CLOSED:  # always,  always give a way out!
                break
            elif event == "打开配置":
                self.__gui_config_start()
            elif event == "-START_BTN-":
                sg.popup(
                    "界面功能开发中，敬请期待 :)\n" "点击OK开始执行",
                    title="系统提示",
                    icon=self.__get_icon(),
                )
                self._window["-START_BTN-"].update(disabled=True)  # 禁用按钮
                self._is_running = True
                # 启动子线程运行逻辑
                threading.Thread(target=crew_main.autowx_gzh, daemon=True).start()

            elif event == "关于":
                sg.popup(
                    "关于软件",
                    "当前Version 1.0",
                    "Copyright (C) 2025 iniwap,All Rights Reserved",
                    title="系统提示",
                    icon=self.__get_icon(),
                )
            elif event == "官网":
                webbrowser.open("https://github.com/iniwap")
            elif event == "帮助":
                sg.popup(
                    "————————————操作说明————————————\n"
                    "一、打开配置界面，首先进行必要的配置\n"
                    "二、点击开始执行，AI自动开始公众\n"
                    "三、陆续加入更多操作中...",
                    title="使用帮助",
                    icon=self.__get_icon(),
                )
            elif event == "-SET_LOG_LIMIT-":
                self._log_buffer = deque(self._log_buffer, maxlen=values["-LOG_LIMIT-"])
                self._window["-STATUS-"].update("\n".join(self._log_buffer))
            elif event == "-CLEAR_LOG-":
                self._log_buffer.clear()
                self._window["-STATUS-"].update("")
            elif event == "日志":
                logs_path = utils.get_res_path("logs", os.path.dirname(__file__))
                if not utils.get_is_release_ver():
                    logs_path = utils.get_res_path("..\\..\\..\\logs", os.path.dirname(__file__))

                filename = sg.popup_get_file(
                    "打开文件",
                    default_path=logs_path,
                    file_types=(("log文件", "*.log"),),
                    no_window=True,
                )

                if len(filename) == 0:
                    continue

                try:
                    os.system("start /B  notepad " + filename)
                except Exception as e:
                    sg.popup(
                        "无法打开日志文件 :( \n错误信息：" + str(e),
                        title="系统提示",
                        icon=self.__get_icon(),
                    )
            elif event == "文章":
                # 生成的最终文章
                pass

            # 处理队列更新（非阻塞）
            if self._is_running:
                self.process_queue()


def gui_start():
    MainGUI().run()


if __name__ == "__main__":
    gui_start()
