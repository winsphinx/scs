import logging
from typing import Optional


def configure_logging(level=logging.INFO):
    """配置统一的日志格式和级别"""
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def get_logger(name: Optional[str] = None):
    """获取配置好的logger实例"""
    return logging.getLogger(name)
