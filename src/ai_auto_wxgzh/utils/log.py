import logging
import sys
import re


def strip_ansi_codes(text):
    """去除 ANSI 颜色代码"""
    ansi_pattern = r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
    return re.sub(ansi_pattern, "", text)


class QueueLoggingHandler(logging.Handler):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        try:
            msg = self.format(record)
            msg = strip_ansi_codes(msg)  # 去除 ANSI 代码
            self.queue.put({"type": "status", "value": f"LOG: {msg}"})
        except Exception:
            self.handleError(record)


class QueueStreamHandler:
    def __init__(self, queue):
        self.queue = queue
        self.original_stdout = sys.__stdout__  # 保存原始 stdout

    def write(self, msg):
        if msg.strip():
            clean_msg = strip_ansi_codes(msg.rstrip())  # 移除尾部换行/空格
            self.queue.put({"type": "status", "value": f"PRINT: {clean_msg}"})
            self.original_stdout.write(msg.rstrip() + "\n")  # 强制换行
            self.original_stdout.flush()

    def flush(self):
        self.original_stdout.flush()


def setup_logging(log_name, queue):
    """配置日志处理器，将 CrewAI 日志发送到队列"""
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)
    handler = QueueLoggingHandler(queue)
    formatter = logging.Formatter("[%(asctime)s][%(levelname)s]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False  # 避免重复日志

    # 捕获 print 输出
    sys.stdout = QueueStreamHandler(queue)
