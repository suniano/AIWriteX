from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime, timedelta
import requests
from io import BytesIO
import os
import mimetypes
import json
import time

from src.ai_write_x.utils import utils
from src.ai_write_x.config.config import Config
from src.ai_write_x.utils import log
from src.ai_write_x.utils.path_manager import PathManager
from src.ai_write_x.tools.image_generator import ImageGenerator


class PublishStatus(Enum):
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"
    DRAFT = "draft"
    SCHEDULED = "scheduled"


@dataclass
class PublishResult:
    publishId: str
    status: PublishStatus
    publishedAt: datetime
    platform: str
    url: Optional[str] = None


class WeixinPublisher:
    BASE_URL = "https://api.weixin.qq.com/cgi-bin"

    def __init__(self, app_id: str, app_secret: str, author: str):
        # 获取配置数据，只能使用确定的配置，微信配置是循环发布的，需要传递
        config = Config.get_instance()

        self.access_token_data = None
        self.app_id = app_id
        self.app_secret = app_secret
        self.author = author
        self.img_api_type = config.img_api_type  # 只有一种模型，统一从配置读取
        self.img_api_key = config.img_api_key
        self.img_api_model = config.img_api_model
        self.image_generator = ImageGenerator(config)

    @property
    def is_verified(self):
        if not hasattr(self, "_is_verified"):
            url = f"{self.BASE_URL}/account/getaccountbasicinfo?access_token={self._ensure_access_token()}"  # noqa 501
            response = requests.get(url, timeout=5)

            try:
                response.raise_for_status()
                data = response.json()
                wx_verify = data.get("wx_verify_info", {})
                self._is_verified = bool(wx_verify.get("qualification_verify", False))
            except (requests.RequestException, ValueError, KeyError):
                self._is_verified = False

        return self._is_verified

    def _ensure_access_token(self):
        # 检查现有token是否有效
        if self.access_token_data and self.access_token_data[
            "expires_at"
        ] > datetime.now() + timedelta(
            minutes=1
        ):  # 预留1分钟余量
            return self.access_token_data["access_token"]

        # 获取新token
        url = f"{self.BASE_URL}/token?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"  # noqa 501

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            access_token = data.get("access_token")
            expires_in = data.get("expires_in")

            if not access_token:
                log.print_log(f"获取access_token失败: {data}")
                return None

            self.access_token_data = {
                "access_token": access_token,
                "expires_in": expires_in,
                "expires_at": datetime.now() + timedelta(seconds=expires_in),
            }
            return access_token
        except requests.exceptions.RequestException as e:
            log.print_log(f"获取微信access_token失败: {e}")

        return None  # 获取不到就返回None，失败交给后面的流程处理

    def _upload_draft(self, article, title, digest, media_id):
        token = self._ensure_access_token()
        url = f"{self.BASE_URL}/draft/add?access_token={token}"

        articles = [
            {
                "title": title[:64],  # 标题长度不能超过64
                "author": self.author,
                "digest": digest[:120],
                "content": article,
                "thumb_media_id": media_id,
                "need_open_comment": 1,
                "only_fans_can_comment": 0,
            },
        ]
        ret = None, None
        try:
            data = {"articles": articles}

            headers = {"Content-Type": "application/json"}
            json_data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            response = requests.post(url, data=json_data, headers=headers)
            response.raise_for_status()
            data = response.json()

            if "errcode" in data and data.get("errcode") != 0:
                ret = None, f"上传草稿失败: {data.get('errmsg')}"
            elif "media_id" not in data:
                ret = None, "上传草稿失败: 响应中缺少 media_id"
            else:
                ret = {"media_id": data.get("media_id")}, None
        except requests.exceptions.RequestException as e:
            ret = None, f"上传微信草稿失败: {e}"

        return ret

    def generate_img(self, prompt, size="1024*1024"):
        try:
            result = self.image_generator.generate(
                prompt,
                provider=self.img_api_type,
                overrides={"size": size},
            )
            return result.get_best_url()
        except Exception as exc:
            log.print_log(f"图片生成失败: {exc}", "error")
            return None

    def upload_image(self, image_url):
        if not image_url:
            # 如果图片URL为空，则返回一个默认的图片ID
            return "SwCSRjrdGJNaWioRQUHzgF68BHFkSlb_f5xlTquvsOSA6Yy0ZRjFo0aW9eS3JJu_", None, None

        ret = None, None, None
        try:
            if image_url.startswith(("http://", "https://")):
                # 处理网络图片
                image_response = requests.get(image_url, stream=True)
                image_response.raise_for_status()
                image_buffer = BytesIO(image_response.content)

                # 动态确定 MIME 类型和文件名后缀
                mime_type = image_response.headers.get("Content-Type")
                if not mime_type:
                    mime_type = "image/jpeg"  # 默认值
                file_ext = mimetypes.guess_extension(mime_type)
                file_name = "image" + file_ext if file_ext else "image.jpg"
            else:
                # 处理本地图片
                if not os.path.exists(image_url):
                    ret = None, None, f"本地图片未找到: {image_url}"

                with open(image_url, "rb") as f:
                    image_buffer = BytesIO(f.read())

                # 动态确定 MIME 类型和文件名后缀
                mime_type, _ = mimetypes.guess_type(image_url)
                if not mime_type:
                    mime_type = "image/jpeg"  # 默认值
                file_name = os.path.basename(image_url)

            token = self._ensure_access_token()
            if self.is_verified:
                url = f"{self.BASE_URL}/media/upload?access_token={token}&type=image"
            else:
                url = f"{self.BASE_URL}/material/add_material?access_token={token}&type=image"

            files = {"media": (file_name, image_buffer, mime_type)}
            response = requests.post(url, files=files)
            response.raise_for_status()
            data = response.json()

            if "errcode" in data and data.get("errcode") != 0:
                ret = None, None, f"图片上传失败: {data.get('errmsg')}"
            elif "media_id" not in data:
                ret = None, None, "图片上传失败: 响应中缺少 media_id"
            else:
                ret = data.get("media_id"), data.get("url"), None

        except requests.exceptions.RequestException as e:
            ret = None, None, f"图片上传失败: {e}"

        return ret

    def add_draft(self, article, title, digest, media_id):
        ret = None, None
        try:
            # 上传草稿
            draft, err_msg = self._upload_draft(article, title, digest, media_id)
            if draft is not None:
                ret = (
                    PublishResult(
                        publishId=draft["media_id"],
                        status=PublishStatus.DRAFT,
                        publishedAt=datetime.now(),
                        platform="wechat",
                        url=f"https://mp.weixin.qq.com/s/{draft['media_id']}",
                    ),
                    None,
                )
            else:
                ret = None, err_msg
        except Exception as e:
            ret = None, f"微信添加草稿失败: {e}"

        return ret

    def publish(self, media_id: str):
        """
        发布草稿箱中的图文素材

        :param media_id: 要发布的草稿的media_id
        :return: 包含发布任务ID的字典
        """
        ret = None, None
        url = f"{self.BASE_URL}/freepublish/submit"
        params = {"access_token": self._ensure_access_token()}
        data = {"media_id": media_id}

        try:
            response = requests.post(url, params=params, json=data)
            response.raise_for_status()
            result = response.json()

            if "errcode" in result and result.get("errcode") != 0:
                ret = None, f"草稿发布失败: {result.get('errmsg')}"
            elif "publish_id" not in result:
                ret = None, "草稿发布失败: 响应中缺少 publish_id"
            else:
                ret = (
                    PublishResult(
                        publishId=result.get("publish_id"),
                        status=PublishStatus.PUBLISHED,
                        publishedAt=datetime.now(),
                        platform="wechat",
                        url="",  # 需要通过轮询获取
                    ),
                    None,
                )
        except Exception as e:
            ret = None, f"发布草稿文章失败：{e}"

        return ret

    # 轮询获取文章链接
    def poll_article_url(self, publish_id, max_retries=10, interval=2):
        url = f"{self.BASE_URL}/freepublish/get?access_token={self._ensure_access_token()}"
        params = {"publish_id": publish_id}

        for _ in range(max_retries):
            response = requests.post(url, json=params).json()
            if response.get("article_id"):
                return response.get("article_detail")["item"][0]["article_url"]

            time.sleep(interval)

        return None

    # ---------------------以下接口需要微信认证[个人用户不可用]-------------------------
    # 单独发布只能通过绑定到菜单的形式访问到，无法显示到公众号文章列表
    def create_menu(self, article_url):
        ret = ""
        menu_data = {
            "button": [
                {
                    "type": "view",
                    "name": "最新文章",
                    "url": article_url,
                }
            ]
        }
        menu_url = f"{self.BASE_URL}/menu/create?access_token={self._ensure_access_token()}"
        try:
            result = requests.post(menu_url, json=menu_data).json()
            if "errcode" in result and result.get("errcode") != 0:
                ret = f"创建菜单失败: {result.get('errmsg')}"
        except Exception as e:
            ret = f"创建菜单失败:{e}"

        return ret

    # 上传图文消息素材【订阅号与服务号认证后均可用】
    def media_uploadnews(self, article, title, digest, media_id):
        token = self._ensure_access_token()
        url = f"{self.BASE_URL}/media/uploadnews?access_token={token}"

        articles = [
            {
                "thumb_media_id": media_id,
                "author": self.author,
                "title": title[:64],
                "content": article,
                "digest": digest[:120],
                "show_cover_pic": 1,
                "need_open_comment": 1,
                "only_fans_can_comment": 0,
            }
        ]

        ret = None, None
        try:
            data = {"articles": articles}
            headers = {"Content-Type": "application/json"}
            json_data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            response = requests.post(url, data=json_data, headers=headers)
            response.raise_for_status()
            result = response.json()

            if "errcode" in result and result.get("errcode") != 0:
                ret = None, f"上传图文素材失败: {result.get('errmsg')}"
            elif "media_id" not in result:
                ret = None, "上传图文素材失败: 响应中缺少 media_id"
            else:
                ret = result.get("media_id"), None
        except requests.exceptions.RequestException as e:
            ret = None, f"上传微信图文素材失败: {e}"

        return ret

    # 根据标签进行群发【订阅号与服务号认证后均可用】
    def message_mass_sendall(self, media_id, is_to_all=True, tag_id=0):
        ret = None

        if is_to_all:
            data_filter = {
                "is_to_all": is_to_all,
            }
        else:
            if tag_id == 0:
                return "根据标签进行群发失败：未勾选群发，且tag_id=0无效"

            data_filter = {
                "is_to_all": is_to_all,
                "tag_id": tag_id,
            }
        data = {
            "filter": data_filter,
            "mpnews": {"media_id": media_id},
            "msgtype": "mpnews",
            "send_ignore_reprint": 1,
        }
        url = f"{self.BASE_URL}/message/mass/sendall?access_token={self._ensure_access_token()}"

        try:
            result = requests.post(url, json=data).json()
            if "errcode" in result and result.get("errcode") != 0:
                ret = f"根据标签进行群发失败: {result.get('errmsg')}"
        except Exception as e:
            ret = f"群发消息失败：{e}"

        return ret


def pub2wx(title, digest, article, appid, appsecret, author):

    publisher = WeixinPublisher(appid, appsecret, author)

    config = Config.get_instance()
    cropped_image_path = ""
    if config.current_preview_cover:
        # 裁剪封面图片
        cropped_image_path = utils.crop_cover_image(config.current_preview_cover, (900, 384))
        if cropped_image_path:
            image_url = cropped_image_path
        else:
            # 裁剪失败，直接使用原图
            image_url = config.current_preview_cover
    else:
        image_url = publisher.generate_img(
            "主题：" + title.split("|")[-1] + "，内容：" + digest,
            "900*384",
        )

    if image_url is None:
        log.print_log("生成图片出错，使用默认图片")
        image_url = utils.get_res_path(
            os.path.join("UI", "bg.png"), os.path.dirname(__file__) + "/../gui/"
        )

    # 封面图片
    media_id, _, err_msg = publisher.upload_image(image_url)

    # 如果使用了临时裁剪文件，上传后删除
    if (
        config.current_preview_cover
        and cropped_image_path
        and cropped_image_path != config.current_preview_cover
    ):
        try:
            os.remove(cropped_image_path)
        except Exception:
            pass

    if media_id is None:
        return f"封面{err_msg}，无法发布文章", article, False

    # 这里需要将文章中的图片url替换为上传到微信返回的图片url
    try:
        image_urls = utils.extract_image_urls(article)
        for image_url in image_urls:
            if utils.is_local_path(image_url):
                # 本地路径，检查文件是否存在
                if os.path.exists(image_url):
                    _, url, _ = publisher.upload_image(image_url)
                    article = article.replace(image_url, url)
                else:
                    log.print_log(f"本地图片文件不存在: {image_url}")
            else:
                # 网络URL，先下载再上传
                local_filename = utils.download_and_save_image(
                    image_url,
                    str(PathManager.get_image_dir()),
                )
                if local_filename:
                    _, url, _ = publisher.upload_image(local_filename)
                    article = article.replace(image_url, url)
                else:
                    log.print_log(f"下载图片失败：{image_url}")
    except Exception as e:
        log.print_log(f"上传配图出错，影响阅读，可继续发布文章:{e}")

    # 账号是否认证
    if not publisher.is_verified:
        add_draft_result, err_msg = publisher.add_draft(article, title, digest, media_id)
        if add_draft_result is None:
            # 添加草稿失败，不再继续执行
            return f"{err_msg}，无法发布文章", article, False

        publish_result, err_msg = publisher.publish(add_draft_result.publishId)
        if publish_result is None:
            if "api unauthorized" in err_msg:  # type: ignore
                return (
                    "自动发布失败，【自2025年7月15日起，个人主体账号、未认证企业账号及不支持认证的账号的发布权限被回收，需到公众号管理后台->草稿箱->发表】",
                    article,
                    False,
                )
            else:
                return f"{err_msg}，无法继续发布文章", article, False
    else:
        # 显示到列表
        media_id, ret = publisher.media_uploadnews(article, title, digest, media_id)
        if media_id is None:
            if "api unauthorized" in ret:  # type: ignore
                return (
                    "账号虽认证（非企业账号），但无发布权限，发布失败，无法自动发布文章",
                    article,
                    False,
                )
            else:
                return f"{ret}，无法显示到公众号文章列表（公众号未认证）", article, False

        """
        article_url = publisher.poll_article_url(publish_result.publishId)
        if article_url is not None:
            # 该接口需要认证,将文章添加到菜单中去，用户可以通过菜单“最新文章”获取到
            ret = publisher.create_menu(article_url)
            if not ret:
                log.print_log(f"{ret}（公众号未认证，发布已成功）")
        else:
            log.print_log("无法获取到文章URL，无法创建菜单（可忽略，发布已成功）")
        """

        # 是否设置为群发
        """
        微信官方说明：https://developers.weixin.qq.com/doc/service/guide/product/message/Batch_Sends.html

        关于群发时设置 is_to_all 为 true 使其进入服务号在微信客户端的历史消息列表的说明：
        设置 is_to_all 为 true 且成功群发，会使得此次群发进入历史消息列表。
        为防止异常，认证服务号在一天内，只能设置 is_to_all 为 true 且成功群发一次，或者在公众平台官网群发一次。以避免一天内有2条群发进入历史消息列表。
        类似地，服务号在一个月内，设置 is_to_all 为 true 且成功群发的次数，加上公众平台官网群发的次数，最多只能是4次。
        服务号设置 is_to_all 为 false 时是可以多次群发的，但每个用户一个月内只会收到最多4条，且这些群发不会进入历史消息列表。
        """
        if config.get_call_sendall_by_appid(appid):
            ret = publisher.message_mass_sendall(
                media_id,
                config.get_sendall_by_appid(appid),
                config.get_tagid_by_appid(appid),
            )
            if ret is not None:
                if "api unauthorized" in ret:
                    return (
                        "没有群发权限，无法显示到公众号文章列表（发布已成功）",
                        article,
                        True,
                    )
                else:
                    return (
                        f"{ret}，无法显示到公众号文章列表（发布已成功）",
                        article,
                        True,
                    )

    return "成功发布文章到微信公众号", article, True
