import logging
import os


def configure_logging(level=logging.INFO):
    """配置统一的日志格式和级别"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(log_dir, "app.log"), encoding="utf-8"),
        ],
    )
