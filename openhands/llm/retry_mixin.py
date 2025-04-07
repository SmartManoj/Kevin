import json
from time import sleep
from typing import Any, Callable

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from litellm.llms.openai_like.common_utils import OpenAILikeError

from openhands.core.exceptions import LLMNoResponseError
from openhands.core.logger import openhands_logger as logger
from openhands.utils.tenacity_stop import stop_if_should_exit


class RetryMixin:
    """Mixin class for retry logic."""

    def retry_decorator(self, **kwargs: Any) -> Callable:
        """
        Create a LLM retry decorator with customizable parameters. This is used for 429 errors, and a few other exceptions in LLM classes.

        Args:
            **kwargs: Keyword arguments to override default retry behavior.
                      Keys: num_retries, retry_exceptions, retry_min_wait, retry_max_wait, retry_multiplier

        Returns:
            A retry decorator with the parameters customizable in configuration.
        """
        num_retries = kwargs.get('num_retries')
        retry_exceptions: tuple = kwargs.get('retry_exceptions', ())
        retry_min_wait = kwargs.get('retry_min_wait')
        retry_max_wait = kwargs.get('retry_max_wait')
        retry_multiplier = kwargs.get('retry_multiplier')
        retry_listener = kwargs.get('retry_listener')

        def before_sleep(retry_state: Any) -> None:
            self.log_retry_attempt(retry_state)
            if retry_listener:
                retry_listener(retry_state.attempt_number, num_retries)

            # Check if the exception is LLMNoResponseError
            exception = retry_state.outcome.exception()
            if isinstance(exception, LLMNoResponseError):
                if hasattr(retry_state, 'kwargs'):
                    # Only change temperature if it's zero or not set
                    current_temp = retry_state.kwargs.get('temperature', 0)
                    if current_temp == 0:
                        retry_state.kwargs['temperature'] = 1.0
                        logger.warning(
                            'LLMNoResponseError detected with temperature=0, setting temperature to 1.0 for next attempt.'
                        )
                    else:
                        logger.warning(
                            f'LLMNoResponseError detected with temperature={current_temp}, keeping original temperature'
                        )

        retry_decorator: Callable = retry(
            before_sleep=before_sleep,
            stop=stop_after_attempt(num_retries) | stop_if_should_exit(),
            reraise=True,
            retry=(
                retry_if_exception_type(retry_exceptions)
            ),  # retry only for these types
            wait=wait_exponential(
                multiplier=retry_multiplier,
                min=retry_min_wait,
                max=retry_max_wait,
            ),
        )
        return retry_decorator

    def log_retry_attempt(self, retry_state: Any) -> None:
        """Log retry attempts."""
        exception = retry_state.outcome.exception()
        try:
            err = json.loads(exception.message.split(' - ')[1]).get('error', {})
            if isinstance(err, dict):
                err_code = err.get('code')
                if err_code == 'rate_limit_exceeded':   
                    err_msg = err.get('message')
                    wait_seconds = err_msg.split('Please try again in ')[1].split('s')[0]
                    logger.error(f'429 | Attempt #{retry_state.attempt_number} | Waiting {wait_seconds} seconds...')
                    sleep(float(wait_seconds))
                    return
        except Exception as e:
            print(exception.message)
            logger.error(f'Error: {e}')

        if 'RESOURCE_EXHAUSTED' in str(exception):
            logger.error(f'429 | Attempt #{retry_state.attempt_number}')
        else:
            logger.error(
                f'{exception}. Attempt #{retry_state.attempt_number} | You can customize retry values in the configuration.',
            )
        import os

        os.environ['attempt_number'] = str(retry_state.attempt_number)
