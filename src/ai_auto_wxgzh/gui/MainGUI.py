#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""

主界面

"""

import os
import sys
import webbrowser
import PySimpleGUI as sg
from . import ConfigEditor
from src.ai_auto_wxgzh import crew_main


__author__ = "iniwaper@gmail.com"
__copyright__ = "Copyright (C) 2025 iniwap"
# __date__ = "2025/04/17"


class MainGUI(object):
    def __init__(self):
        self._log_list = []
        # 设置主题
        sg.theme("systemdefault")

        menu_list = [
            ["配置", ["配置"]],
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
                    s=(640, 450),
                    filename=self.__get_res_path("UI\\bg.png", os.path.dirname(__file__)),
                    key="-BG-IMG-",
                    expand_x=True,
                )
            ],
            [
                sg.Push(),  # 左侧占位
                sg.Button(button_text="开始执行", size=(12, 4), key="-START_BTN-"),
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

    def __get_res_path(self, file_name, basedir):
        if getattr(sys, "frozen", None):
            return os.path.join(sys._MEIPASS, file_name)

        return os.path.join(basedir, file_name)

    def __get_icon(self):
        return self.__get_res_path("UI\\icon.ico", os.path.dirname(__file__))

    def __gui_config_start(self):
        ConfigEditor.gui_start()

    def run(self):
        while True:
            event, values = self._window.read()
            if event == sg.WIN_CLOSED:  # always,  always give a way out!
                break
            elif event == "配置":
                self.__gui_config_start()
            elif event == "-START_BTN-":
                sg.popup(
                    "界面功能开发中，敬请期待 :)\n" "【输出请查看TERMINAL...】",
                    title="系统提示",
                    icon=self.__get_icon(),
                )
                crew_main.autowx_gzh()

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


def gui_start():
    MainGUI().run()


if __name__ == "__main__":
    gui_start()
