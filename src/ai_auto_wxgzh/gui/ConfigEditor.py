import PySimpleGUI as sg
import re
from src.ai_auto_wxgzh.config.config import Config


class ConfigEditor:
    def __init__(self):
        """初始化配置编辑器，使用单例配置"""
        sg.theme("systemdefault")
        self.config = Config.get_instance()
        self.platform_count = len(self.config.platforms)
        self.wechat_count = len(self.config.wechat_credentials)
        self.window = None

    def create_platforms_tab(self):
        """创建平台 TAB 布局"""
        platforms = self.config.platforms
        platform_rows = [
            [
                sg.InputText(
                    platform["name"], key=f"-PLATFORM_NAME_{i}-", size=(20, 1), disabled=True
                ),
                sg.Text("权重:", size=(6, 1)),
                sg.InputText(platform["weight"], key=f"-PLATFORM_WEIGHT_{i}-", size=(10, 1)),
            ]
            for i, platform in enumerate(platforms)
        ]
        return sg.Tab(
            "平台",
            [
                [sg.Text("热搜平台列表（权重之和需要为1）：")],
                *platform_rows,
                [sg.Button("保存配置", key="-SAVE_PLATFORMS-")],
            ],
        )

    def create_wechat_tab(self):
        """创建微信 TAB 布局"""
        credentials = self.config.wechat_credentials
        wechat_rows = [
            [
                sg.Text(f"凭证 {i+1}:", size=(10, 1), key=f"-WECHAT_TITLE_{i}-"),
                sg.Text("AppID:", size=(8, 1)),
                sg.InputText(cred["appid"], key=f"-WECHAT_APPID_{i}-", size=(30, 1)),
                sg.Text("AppSecret:", size=(10, 1)),
                sg.InputText(cred["appsecret"], key=f"-WECHAT_SECRET_{i}-", size=(30, 1)),
                sg.Text("作者:", size=(8, 1)),
                sg.InputText(cred["author"], key=f"-WECHAT_AUTHOR_{i}-", size=(15, 1)),
                sg.Button("删除", key=f"-DELETE_WECHAT_{i}-"),
            ]
            for i, cred in enumerate(credentials)
        ]
        return sg.Tab(
            "微信*",
            [
                [sg.Text("微信公众号凭证")],
                *wechat_rows,
                [sg.Button("添加凭证", key="-ADD_WECHAT-")],
                [sg.Button("保存配置", key="-SAVE_WECHAT-")],
            ],
        )

    def create_api_sub_tab(self, api_name, api_data):
        """创建 API 子 TAB 布局"""
        layout = [
            [sg.Text(f"{api_name.upper()} 配置")],
            [
                sg.Text("密钥名称:", size=(15, 1)),
                sg.InputText(api_data["key"], key=f"-{api_name}_KEY-"),
            ],
            [
                sg.Text("密钥索引:", size=(15, 1)),
                sg.InputText(api_data["key_index"], key=f"-{api_name}_KEY_INDEX-"),
            ],
            [
                sg.Text("API 密钥:", size=(15, 1)),
                sg.InputText(", ".join(api_data["api_key"]), key=f"-{api_name}_API_KEYS-"),
            ],
            [
                sg.Text("模型索引:", size=(15, 1)),
                sg.InputText(api_data["model_index"], key=f"-{api_name}_MODEL_INDEX-"),
            ],
            [
                sg.Text("API 基础地址:", size=(15, 1)),
                sg.InputText(api_data["api_base"], key=f"-{api_name}_API_BASE-"),
            ],
            [
                sg.Text("模型:", size=(15, 1)),
                sg.InputText(", ".join(api_data["model"]), key=f"-{api_name}_MODEL-"),
            ],
            [sg.Button("添加模型", key=f"-ADD_{api_name}_MODEL-")],
            [sg.Button("添加 API 密钥", key=f"-ADD_{api_name}_API_KEY-")],
        ]
        return layout

    def create_api_tab(self):
        """创建 API TAB 布局"""
        api_data = self.config.get_config()["api"]
        return sg.Tab(
            "API*",
            [
                [
                    sg.Text("API 类型"),
                    sg.Combo(
                        ["ollama", "grok", "qwen", "gemini", "openrouter"],
                        default_value=api_data["api_type"],
                        key="-API_TYPE-",
                    ),
                ],
                [
                    sg.TabGroup(
                        [
                            [sg.Tab("Grok", self.create_api_sub_tab("grok", api_data["grok"]))],
                            [sg.Tab("Qwen", self.create_api_sub_tab("qwen", api_data["qwen"]))],
                            [
                                sg.Tab(
                                    "Gemini", self.create_api_sub_tab("gemini", api_data["gemini"])
                                )
                            ],
                            [
                                sg.Tab(
                                    "OpenRouter",
                                    self.create_api_sub_tab("openrouter", api_data["openrouter"]),
                                )
                            ],
                            [
                                sg.Tab(
                                    "Ollama", self.create_api_sub_tab("ollama", api_data["ollama"])
                                )
                            ],
                        ]
                    )
                ],
                [sg.Button("保存配置", key="-SAVE_API-")],
            ],
        )

    def create_img_api_tab(self):
        """创建图像 API TAB 布局"""
        img_api = self.config.get_config()["img_api"]
        return sg.Tab(
            "图像 API",
            [
                [
                    sg.Text("API 类型"),
                    sg.Combo(
                        ["picsum", "ali"], default_value=img_api["api_type"], key="-IMG_API_TYPE-"
                    ),
                ],
                [sg.Text("阿里 API 配置")],
                [
                    sg.Text("API 密钥:", size=(15, 1)),
                    sg.InputText(img_api["ali"]["api_key"], key="-ALI_API_KEY-"),
                ],
                [
                    sg.Text("模型:", size=(15, 1)),
                    sg.InputText(img_api["ali"]["model"], key="-ALI_MODEL-"),
                ],
                [sg.Text("Picsum API 配置")],
                [
                    sg.Text("API 密钥:", size=(15, 1)),
                    sg.InputText(img_api["picsum"]["api_key"], key="-PICSUM_API_KEY-"),
                ],
                [
                    sg.Text("模型:", size=(15, 1)),
                    sg.InputText(img_api["picsum"]["model"], key="-PICSUM_MODEL-"),
                ],
                [sg.Button("保存配置", key="-SAVE_IMG_API-")],
            ],
        )

    def create_other_tab(self):
        """创建其他 TAB 布局"""
        return sg.Tab(
            "其他",
            [
                [sg.Checkbox("使用模板", default=self.config.use_template, key="-USE_TEMPLATE-")],
                [sg.Checkbox("需要审核者", default=self.config.need_auditor, key="-NEED_AUDITOR-")],
                [sg.Button("保存配置", key="-SAVE_OTHER-")],
            ],
        )

    def create_layout(self):
        """创建主布局"""
        return [
            [
                sg.TabGroup(
                    [
                        [self.create_platforms_tab()],
                        [self.create_wechat_tab()],
                        [self.create_api_tab()],
                        [self.create_img_api_tab()],
                        [self.create_other_tab()],
                    ]
                )
            ],
            [sg.Button("退出", key="-EXIT-")],
        ]

    def run(self):
        """运行配置编辑器主循环"""
        if not self.config.load_config():
            sg.popup_error(self.config.error_message)
            return

        self.window = sg.Window("配置编辑器", self.create_layout(), resizable=True)

        while True:
            event, values = self.window.read()
            if event in (sg.WIN_CLOSED, "-EXIT-"):
                break

            # 添加微信凭证
            if event == "-ADD_WECHAT-":
                self.window.extend_layout(
                    self.window["微信*"],
                    [
                        [
                            sg.Text(
                                f"凭证 {self.wechat_count+1}:",
                                size=(10, 1),
                                key=f"-WECHAT_TITLE_{self.wechat_count}-",
                            ),
                            sg.Text("AppID:", size=(8, 1)),
                            sg.InputText(
                                "", key=f"-WECHAT_APPID_{self.wechat_count}-", size=(30, 1)
                            ),
                            sg.Text("AppSecret:", size=(10, 1)),
                            sg.InputText(
                                "", key=f"-WECHAT_SECRET_{self.wechat_count}-", size=(30, 1)
                            ),
                            sg.Text("作者:", size=(8, 1)),
                            sg.InputText(
                                "", key=f"-WECHAT_AUTHOR_{self.wechat_count}-", size=(15, 1)
                            ),
                            sg.Button("删除", key=f"-DELETE_WECHAT_{self.wechat_count}-"),
                        ]
                    ],
                )
                self.wechat_count += 1

            # 删除微信凭证
            if event.startswith("-DELETE_WECHAT_"):
                match = re.search(r"-DELETE_WECHAT_(\d+)", event)
                if match:
                    index = int(match.group(1))
                    credentials = self.config.get_config()["wechat"]["credentials"]
                    if 0 <= index < len(credentials):
                        credentials.pop(index)
                        self.window["微信*"].update(self.create_wechat_tab())
                        self.wechat_count = len(credentials)

            # 添加 API 模型
            if event.startswith("-ADD_") and event.endswith("_MODEL-"):
                api_name = event.split("_")[1].lower()
                new_model = sg.popup_get_text(f"输入新模型名称（{api_name}）:", title="添加模型")
                if new_model:
                    current_models = (
                        values[f"-{api_name}_MODEL-"].split(", ")
                        if values[f"-{api_name}_MODEL-"]
                        else []
                    )
                    current_models.append(new_model)
                    self.window[f"-{api_name}_MODEL-"].update(", ".join(current_models))

            # 添加 API 密钥
            if event.startswith("-ADD_") and event.endswith("_API_KEY-"):
                api_name = event.split("_")[1].lower()
                new_key = sg.popup_get_text(
                    f"输入新 API 密钥（{api_name}）:", title="添加 API 密钥"
                )
                if new_key:
                    current_keys = (
                        values[f"-{api_name}_API_KEYS-"].split(", ")
                        if values[f"-{api_name}_API_KEYS-"]
                        else []
                    )
                    current_keys.append(new_key)
                    self.window[f"-{api_name}_API_KEYS-"].update(", ".join(current_keys))

            # 保存平台配置
            if event == "-SAVE_PLATFORMS-":
                config = self.config.get_config().copy()
                platforms = []
                for i in range(self.platform_count):
                    try:
                        weight = float(values[f"-PLATFORM_WEIGHT_{i}-"])
                        platforms.append({"name": values[f"-PLATFORM_NAME_{i}-"], "weight": weight})
                    except ValueError:
                        sg.popup_error(f"平台 {i+1} 权重必须是数字")
                        break
                else:
                    config["platforms"] = platforms
                    if self.config.save_config(config):
                        sg.popup("平台配置已保存")
                    else:
                        sg.popup_error(self.config.error_message)

            # 保存微信配置
            if event == "-SAVE_WECHAT-":
                config = self.config.get_config().copy()
                credentials = []
                for i in range(self.wechat_count):
                    if self.window[f"-WECHAT_APPID_{i}-"].visible:
                        credentials.append(
                            {
                                "appid": values[f"-WECHAT_APPID_{i}-"],
                                "appsecret": values[f"-WECHAT_SECRET_{i}-"],
                                "author": values[f"-WECHAT_AUTHOR_{i}-"],
                            }
                        )
                config["wechat"]["credentials"] = credentials
                if self.config.save_config(config):
                    sg.popup("微信配置已保存")
                else:
                    sg.popup_error(self.config.error_message)

            # 保存 API 配置
            if event == "-SAVE_API-":
                config = self.config.get_config().copy()
                config["api"]["api_type"] = values["-API_TYPE-"]
                for api_name in ["grok", "qwen", "gemini", "openrouter", "ollama"]:
                    try:
                        model_index = int(values[f"-{api_name}_MODEL_INDEX-"])
                        key_index = int(values[f"-{api_name}_KEY_INDEX-"])
                        models = [
                            m.strip() for m in values[f"-{api_name}_MODEL-"].split(",") if m.strip()
                        ]
                        api_keys = [
                            k.strip()
                            for k in values[f"-{api_name}_API_KEYS-"].split(",")
                            if k.strip()
                        ]
                        if not api_keys:
                            api_keys = [""]  # 确保至少有一个空密钥
                        if key_index >= len(api_keys):
                            raise ValueError(f"{api_name} 密钥索引超出范围")
                        if model_index >= len(models):
                            raise ValueError(f"{api_name} 模型索引超出范围")
                        api_data = {
                            "key": values[f"-{api_name}_KEY-"],
                            "key_index": key_index,
                            "api_key": api_keys,
                            "model_index": model_index,
                            "api_base": values[f"-{api_name}_API_BASE-"],
                            "model": models,
                        }
                        config["api"][api_name].update(api_data)
                    except ValueError as e:
                        sg.popup_error(f"{api_name} 配置错误: {e}")
                        break
                else:
                    if self.config.save_config(config):
                        sg.popup("API 配置已保存")
                    else:
                        sg.popup_error(self.config.error_message)

            # 保存图像 API 配置
            if event == "-SAVE_IMG_API-":
                config = self.config.get_config().copy()
                config["img_api"]["api_type"] = values["-IMG_API_TYPE-"]
                config["img_api"]["ali"].update(
                    {"api_key": values["-ALI_API_KEY-"], "model": values["-ALI_MODEL-"]}
                )
                config["img_api"]["picsum"].update(
                    {"api_key": values["-PICSUM_API_KEY-"], "model": values["-PICSUM_MODEL-"]}
                )
                if self.config.save_config(config):
                    sg.popup("图像 API 配置已保存")
                else:
                    sg.popup_error(self.config.error_message)

            # 保存其他配置
            if event == "-SAVE_OTHER-":
                config = self.config.get_config().copy()
                config["use_template"] = values["-USE_TEMPLATE-"]
                config["need_auditor"] = values["-NEED_AUDITOR-"]
                if self.config.save_config(config):
                    sg.popup("其他配置已保存")
                else:
                    sg.popup_error(self.config.error_message)

        self.window.close()


def gui_start():
    ConfigEditor().run()
