#!/usr/bin/env python
import sys
import os
import warnings
import yaml

from src.ai_auto_wxgzh.tools import hotnews
from src.ai_auto_wxgzh.crew import AutowxGzh
from src.ai_auto_wxgzh.utils import utils
from src.ai_auto_wxgzh.utils import comm


warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information


def run(inputs, use_template=False, need_auditor=False):
    """
    Run the crew.
    """
    try:
        AutowxGzh(use_template, need_auditor).crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {"topic": "AI LLMs"}
    try:
        AutowxGzh().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        AutowxGzh().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {"topic": "AI LLMs"}
    try:
        AutowxGzh().crew().test(
            n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs
        )

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


def load_config():
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "config",
        "config.yaml",
    )
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return (
        config["wechat"]["credentials"],
        config["platforms"],
        config["api"],
        config["img_api"],
        config["use_template"],
        config["need_auditor"],
    )


def autowx_gzh():
    credentials, platforms, api, img_api, use_template, need_auditor = load_config()
    comm.send_update("status", "配置加载完成!")

    use_api = api[api["api_type"]]
    if api["api_type"] == "openrouter":  # OR每天限量，可以多个账号切换
        os.environ[use_api["key"]] = use_api["api_key"][use_api["key_index"]]
    else:
        os.environ[use_api["key"]] = use_api["api_key"]
    os.environ["MODEL"] = use_api["model"][use_api["model_index"]]  # 采用地
    os.environ["OPENAI_API_BASE"] = use_api["api_base"]

    img_api_type = img_api["api_type"]
    use_img_api = img_api[img_api_type]
    img_api_key = use_img_api["api_key"]
    img_api_model = use_img_api["model"]

    for credential in credentials:
        appid = credential["appid"]
        appsecret = credential["appsecret"]
        author = credential["author"]
        platform = utils.get_random_platform(platforms)
        topics = hotnews.get_platform_news(platform, 1)  # 使用不重复的平台
        if len(topics) == 0:
            topics = ["DeepSeek AI 提效秘籍"]
            comm.send_update("status", "---------无法获取到热榜，请检查网络！------------")

        # 如果没用配置appid，则忽略该条
        if len(appid) == 0 or len(appsecret) == 0:
            continue

        inputs = {
            "platform": platform,
            "topic": topics[0],
            "appid": appid,
            "appsecret": appsecret,
            "author": author,
            "img_api_type": img_api_type,
            "img_api_key": img_api_key,
            "img_api_model": img_api_model,
        }

        comm.send_update("status", "CrewAI开始工作...")
        run(inputs, use_template, need_auditor)


if __name__ == "__main__":
    autowx_gzh()
