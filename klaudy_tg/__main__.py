import logging
import argparse

from . import telegram_bot
from . import config


class CustomLoggingFormatter(logging.Formatter):
    green = "\x1b[32;20m"
    blue = "\x1b[34;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    white = "\x1b[0m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s (%(filename)-12s:%(lineno)-4d) %(levelname)-8s %(message)s"

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
        "default": white + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.FORMATS["default"])
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def beautiful_logging():
    logger = logging.getLogger()
    logger.setLevel(config.log_level)
    console = logging.StreamHandler()
    console.setFormatter(CustomLoggingFormatter())
    logger.addHandler(console)


def start_app():
    beautiful_logging()
    telegram_bot.run_bot()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Klaudy')
    parser.add_argument("-d", "--debug", action='store_true')
    args = parser.parse_args()
    if args.debug:
        config.log_level = logging.DEBUG
    else:
        config.log_level = logging.INFO
    start_app()
