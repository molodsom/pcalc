import logging


def get_logger(name: str):
    level = logging.DEBUG
    console_level = logging.DEBUG

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger
