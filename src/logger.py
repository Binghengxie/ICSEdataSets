import logging
import os
import colorlog
from logging.handlers import RotatingFileHandler
from datetime import datetime

cur_path = os.path.dirname(os.path.realpath(__file__))  # 当前项目路径
log_path = os.path.join(os.path.dirname(cur_path), 'logs')  # log_path为存放日志的路径
if not os.path.exists(log_path):
    os.mkdir(log_path)  # 若不存在logs文件夹，则自动创建

log_colors_config = {
    # 终端输出日志颜色配置
    'DEBUG': 'cyan',
    'INFO': 'white',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}

default_formats = {
    # 终端输出格式
    'color_format':
    '%(asctime)s-%(name)s-%(filename)s-[line:%(lineno)d]-%(log_color)s%(levelname)s: %(message)s',
    # 日志输出格式
    'log_format':
    '%(asctime)s-%(name)s-%(filename)s-[line:%(lineno)d]-%(levelname)s: %(message)s'
}


def init_logger_handler(log_path):
    """
    创建日志记录器handler，用于收集日志
    :param log_path: 日志文件路径
    :return: 日志记录器
    """
    # 写入文件，如果文件超过1M大小时，切割日志文件，仅保留3个文件
    logger_handler = RotatingFileHandler(filename=log_path,
                                         maxBytes=1 * 1024 * 1024,
                                         backupCount=3,
                                         encoding='utf-8')
    return logger_handler


def set_log_formatter(file_handler):
    """
    设置日志输出格式-日志文件
    :param file_handler: 日志记录器
    """
    formatter = logging.Formatter(default_formats["log_format"],
                                  datefmt='%a, %d %b %Y %H:%M:%S')
    file_handler.setFormatter(formatter)


def set_color_formatter(console_handle, color_config):
    """
    设置输出格式-控制台
    :param console_handle: 终端日志记录器
    :param color_config: 控制台打印颜色配置信息
    :return:
    """
    formatter = colorlog.ColoredFormatter(default_formats["color_format"],
                                          log_colors=color_config)
    console_handle.setFormatter(formatter)


def set_log_handler(logger_handler, logger, level=logging.INFO):
    """
    设置handler级别并添加到logger收集器
    :param logger_handler: 日志记录器
    :param level: 日志记录器级别
    """
    logger_handler.setLevel(level=level)
    logger.addHandler(logger_handler)


def set_color_handle(console_handle, logger):
    """
    设置handler级别并添加到终端logger收集器
    :param console_handle: 终端日志记录器
    :param level: 日志记录器级别
    """
    console_handle.setLevel(logging.INFO)
    logger.addHandler(console_handle)


now_time = datetime.now().strftime('%Y-%m-%d')  # 当前日期格式化
all_log_path = os.path.join(log_path, now_time + "-all" + ".log")  # 收集所有日志信息文件
error_log_path = os.path.join(log_path,
                              now_time + "-error" + ".log")  # 收集错误日志信息文件
logger = logging.getLogger()  # 创建日志记录器
logger.setLevel(logging.DEBUG)  # 设置默认日志记录器记录级别

all_logger_handler = init_logger_handler(all_log_path)  # 创建日志文件
error_logger_handler = init_logger_handler(error_log_path)
console_handle = colorlog.StreamHandler()

set_log_formatter(all_logger_handler)
set_log_formatter(error_logger_handler)
set_color_formatter(console_handle, log_colors_config)

if not logger.handlers:
    set_log_handler(all_logger_handler, logger)  # 设置handler级别并添加到logger收集器
    set_log_handler(error_logger_handler, logger, level=logging.ERROR)
    set_color_handle(console_handle, logger)

# logger.info("这是日志信息")
# logger.debug("这是debug信息")
# logger.warning("这是警告信息")
# logger.error("这是错误日志信息")
# logger.critical("这是严重级别信息")

# logger.removeHandler(all_logger_handler)  # 避免日志输出重复问题
# logger.removeHandler(error_logger_handler)
# logger.removeHandler(console_handle)
all_logger_handler.close()  # 关闭handler
error_logger_handler.close()

if __name__ == '__main__':
    logger.info("这是日志信息")
    logger.debug("这是debug信息")
    logger.warning("这是警告信息")
    logger.error("这是错误日志信息")
    logger.critical("这是严重级别信息")