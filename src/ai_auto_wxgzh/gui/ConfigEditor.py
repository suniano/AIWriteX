import PySimpleGUI as sg
import yaml
import os
import re


class ConfigEditor:
    def __init__(self, config_file="config.yaml"):
        """初始化配置编辑器，加载配置文件或使用默认配置"""
        sg.theme("systemdefault")

        self.config_file = config_file
        self.default_config = {
            "platforms": [
                {"name": "微博", "weight": 0.3},
                {"name": "抖音", "weight": 0.25},
                {"name": "哔哩哔哩", "weight": 0.12},
                {"name": "知乎热榜", "weight": 0.10},
                {"name": "百度热点", "weight": 0.08},
                {"name": "今日头条", "weight": 0.07},
                {"name": "虎扑", "weight": 0.05},
                {"name": "豆瓣小组", "weight": 0.02},
                {"name": "澎湃新闻", "weight": 0.01},
            ],
            "wechat": {
                "credentials": [
                    {
                        "appid": "【请在此处填写微信公众号appid】",
                        "appsecret": "【请在此处填写微信公众号appsecret】",
                        "author": "作者01",
                    },
                    {"appid": "", "appsecret": "", "author": "作者02"},
                    {"appid": "", "appsecret": "", "author": "作者03"},
                ]
            },
            "api": {
                "api_type": "ollama",
                "grok": {
                    "key": "XAI_API_KEY",
                    "api_key": "【若使用grok，请在此处填写api key】",
                    "model_index": 0,
                    "model": ["xai/grok-2-latest"],
                    "api_base": "https://api.x.ai/v1/chat/completions",
                },
                "qwen": {
                    "key": "OPENAI_API_KEY",
                    "api_key": "【若使用qwen，请在此处填写api key】",
                    "model_index": 3,
                    "model": [
                        "openai/deepseek-v3",
                        "openai/deepseek-r1",
                        "qwen-max-latest",
                        "openai/qwen-max",
                        "openai/qwen-vl-plus",
                        "openai/qwen-plus",
                    ],
                    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                },
                "gemini": {
                    "key": "GEMINI_API_KEY",
                    "api_key": "【若使用gemini，请在此处填写api key】",
                    "model_index": 0,
                    "model": [
                        "gemini-1.5-flash",
                        "gemini-1.5-pro",
                        "gemini-2.0-flash-lite-preview-02-05",
                        "gemini-2.0-flash",
                    ],
                    "api_base": "https://generativelanguage.googleapis.com",
                },
                "openrouter": {
                    "key": "OPENROUTER_API_KEY",
                    "model_index": 0,
                    "key_index": 0,
                    "api_key": [
                        "【若使用openrouter，请在此处填写api key】",
                        "【若使用多个openrouter，请在此处填写第二个api key】",
                    ],
                    "model": [
                        "openrouter/deepseek/deepseek-chat-v3-0324:free",
                        "openrouter/deepseek/deepseek-r1:free",
                        "openrouter/deepseek/deepseek-chat:free",
                        "openrouter/qwen/qwq-32b:free",
                        "openrouter/google/gemini-2.0-flash-lite-preview-02-05:free",
                        "openrouter/google/gemini-2.0-flash-thinking-exp:free",
                    ],
                    "api_base": "https://openrouter.ai/api/v1",
                },
                "ollama": {
                    "key": "OPENAI_API_KEY",
                    "model_index": 0,
                    "api_key": "temp-key",
                    "model": ["ollama/deepseek-r1:14b", "ollama/deepseek-r1:7b"],
                    "api_base": "http://localhost:11434",
                },
            },
            "img_api": {
                "api_type": "picsum",
                "ali": {
                    "api_key": "【若使用qwen，请在此处填写api key】",
                    "model": "wanx2.0-t2i-turbo",
                },
                "picsum": {"api_key": "", "model": ""},
            },
            "use_template": True,
            "need_auditor": False,
        }
        self.config = self.load_config()
        self.platform_count = len(self.config["platforms"])
        self.wechat_count = len(self.config["wechat"]["credentials"])
        self.api_key_counts = {
            api: (
                len(self.config["api"][api]["api_key"])
                if isinstance(self.config["api"][api]["api_key"], list)
                else 1
            )
            for api in ["openrouter"]
        }
        self.model_counts = {
            api: len(self.config["api"][api]["model"])
            for api in ["grok", "qwen", "gemini", "openrouter", "ollama"]
        }
        self.window = None

    def load_config(self):
        """从本地 config.yaml 加载配置，若不存在使用默认配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded_config = yaml.safe_load(f)
                    if loaded_config:
                        return loaded_config
            except Exception as e:
                sg.popup_error(f"加载 config.yaml 失败: {e}")
        return self.default_config

    def save_config(self):
        """保存配置到 config.yaml"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(self.config, f, allow_unicode=True, sort_keys=False)
            sg.popup("配置已保存到 config.yaml")
        except Exception as e:
            sg.popup_error(f"保存失败: {e}")

    def create_platforms_tab(self):
        """创建平台 TAB 布局"""
        platforms = self.config["platforms"]
        platform_rows = [
            [
                sg.Text(f"平台 {i+1}:", size=(10, 1)),
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
                [sg.Text("平台列表")],
                *platform_rows,
                [sg.Button("保存配置", key="-SAVE_PLATFORMS-")],
            ],
        )

    def create_wechat_tab(self):
        """创建微信 TAB 布局"""
        credentials = self.config["wechat"]["credentials"]
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
            "微信",
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
                sg.Text("密钥:", size=(15, 1)),
                sg.InputText(api_data["key"], key=f"-{api_name}_KEY-"),
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
        ]
        if api_name == "openrouter":
            layout.extend(
                [
                    [
                        sg.Text("密钥索引:", size=(15, 1)),
                        sg.InputText(api_data["key_index"], key=f"-{api_name}_KEY_INDEX-"),
                    ],
                    [
                        sg.Text("API 密钥:", size=(15, 1)),
                        sg.InputText(", ".join(api_data["api_key"]), key=f"-{api_name}_API_KEYS-"),
                    ],
                    [sg.Button("添加 API 密钥", key=f"-ADD_{api_name}_API_KEY-")],
                ]
            )
        else:
            layout.append(
                [
                    sg.Text("API 密钥:", size=(15, 1)),
                    sg.InputText(api_data["api_key"], key=f"-{api_name}_API_KEY-"),
                ]
            )
        return layout

    def create_api_tab(self):
        """创建 API TAB 布局"""
        api_data = self.config["api"]
        return sg.Tab(
            "API",
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
        img_api = self.config["img_api"]
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
                [
                    sg.Checkbox(
                        "使用模板", default=self.config["use_template"], key="-USE_TEMPLATE-"
                    )
                ],
                [
                    sg.Checkbox(
                        "需要审核者", default=self.config["need_auditor"], key="-NEED_AUDITOR-"
                    )
                ],
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
        self.window = sg.Window("配置编辑器", self.create_layout(), resizable=True)

        while True:
            event, values = self.window.read()
            if event in (sg.WIN_CLOSED, "-EXIT-"):
                break

            # 添加微信凭证
            if event == "-ADD_WECHAT-":
                self.window.extend_layout(
                    self.window["微信"],
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
                    # 标记需要删除的凭证
                    credentials = self.config["wechat"]["credentials"]
                    if 0 <= index < len(credentials):
                        credentials.pop(index)
                        # 重新构建微信 TAB 布局
                        self.window["微信"].update(self.create_wechat_tab())
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

            # 添加 OpenRouter API 密钥
            if event == "-ADD_openrouter_API_KEY-":
                new_key = sg.popup_get_text("输入新 API 密钥（OpenRouter）:", title="添加 API 密钥")
                if new_key:
                    current_keys = (
                        values["-openrouter_API_KEYS-"].split(", ")
                        if values["-openrouter_API_KEYS-"]
                        else []
                    )
                    current_keys.append(new_key)
                    self.window["-openrouter_API_KEYS-"].update(", ".join(current_keys))

            # 保存平台配置
            if event == "-SAVE_PLATFORMS-":
                platforms = []
                for i in range(self.platform_count):
                    try:
                        weight = float(values[f"-PLATFORM_WEIGHT_{i}-"])
                        platforms.append({"name": values[f"-PLATFORM_NAME_{i}-"], "weight": weight})
                    except ValueError:
                        sg.popup_error(f"平台 {i+1} 权重必须是数字")
                        break
                else:
                    self.config["platforms"] = platforms
                    self.save_config()

            # 保存微信配置
            if event == "-SAVE_WECHAT-":
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
                self.config["wechat"]["credentials"] = credentials
                self.save_config()

            # 保存 API 配置
            if event == "-SAVE_API-":
                self.config["api"]["api_type"] = values["-API_TYPE-"]
                for api_name in ["grok", "qwen", "gemini", "openrouter", "ollama"]:
                    try:
                        model_index = int(values[f"-{api_name}_MODEL_INDEX-"])
                        models = [
                            m.strip() for m in values[f"-{api_name}_MODEL-"].split(",") if m.strip()
                        ]
                        api_data = {
                            "key": values[f"-{api_name}_KEY-"],
                            "model_index": model_index,
                            "api_base": values[f"-{api_name}_API_BASE-"],
                            "model": models,
                        }
                        if api_name == "openrouter":
                            api_data["key_index"] = int(values[f"-openrouter_KEY_INDEX-"])
                            api_data["api_key"] = [
                                k.strip()
                                for k in values[f"-openrouter_API_KEYS-"].split(",")
                                if k.strip()
                            ]
                        else:
                            api_data["api_key"] = values[f"-{api_name}_API_KEY-"]
                        self.config["api"][api_name].update(api_data)
                    except ValueError:
                        sg.popup_error(f"{api_name} 模型索引必须是整数")
                        break
                else:
                    self.save_config()

            # 保存图像 API 配置
            if event == "-SAVE_IMG_API-":
                self.config["img_api"]["api_type"] = values["-IMG_API_TYPE-"]
                self.config["img_api"]["ali"].update(
                    {"api_key": values["-ALI_API_KEY-"], "model": values["-ALI_MODEL-"]}
                )
                self.config["img_api"]["picsum"].update(
                    {"api_key": values["-PICSUM_API_KEY-"], "model": values["-PICSUM_MODEL-"]}
                )
                self.save_config()

            # 保存其他配置
            if event == "-SAVE_OTHER-":
                self.config["use_template"] = values["-USE_TEMPLATE-"]
                self.config["need_auditor"] = values["-NEED_AUDITOR-"]
                self.save_config()

        self.window.close()


def gui_start():
    ConfigEditor().run()
