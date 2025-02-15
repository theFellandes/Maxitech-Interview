"""
A custom logger that is used for logging function calls and their results.
"""
import logging
import functools


class CustomLogger:
    def __init__(self, handler_type='console'):
        """
        Initialize the CustomLogger with the specified handler type.
        handler_type: 'console' or 'file'
        """
        self.handler_type = handler_type
        self.logger = self._configure_logger(handler_type)

    @staticmethod
    def _configure_logger(handler_type):
        """
        Configure and return a logger with the given handler type.
        """
        # Create a logger with a unique name per handler to avoid conflicts
        logger = logging.getLogger(f'custom_logger_{handler_type}')
        logger.setLevel(logging.INFO)
        # Clear any existing handlers to prevent duplicate logs
        logger.handlers.clear()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        if handler_type == 'console':
            handler = logging.StreamHandler()
        elif handler_type == 'file':
            handler = logging.FileHandler("app.log")
        else:
            raise ValueError("Invalid handler_type. Use 'console' or 'file'.")

        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def __call__(self, func):
        """
        Allow the instance to be used as a decorator.
        Logs before and after the function call.
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            self.logger.info("Entering function '%s' with args: %s and kwargs: %s",
                             func.__name__, args, kwargs)
            result = func(*args, **kwargs)
            self.logger.info("Exiting function '%s' with result: %s",
                             func.__name__, result)
            return result

        return wrapper
