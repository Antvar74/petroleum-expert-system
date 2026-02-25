import logging
from utils.logger import get_logger

def test_get_logger_returns_named_logger():
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "petroexpert.test_module"

def test_get_logger_has_handler():
    logger = get_logger("handler_test")
    root = logging.getLogger("petroexpert")
    assert len(root.handlers) >= 1
