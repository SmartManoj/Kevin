import json
from time import sleep
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from litellm.llms.openai_like.common_utils import OpenAILikeError

from openhands.core.logger import openhands_logger as logger
from openhands.utils.tenacity_stop import stop_if_should_exit


class RetryMixin:
    """Mixin class for retry logic."""

    def retry_decorator(self, **kwargs):
        """
        Create a LLM retry decorator with customizable parameters. This is used for 429 errors, and a few other exceptions in LLM classes.

        Args:
            **kwargs: Keyword arguments to override default retry behavior.
                      Keys: num_retries, retry_exceptions, retry_min_wait, retry_max_wait, retry_multiplier

        Returns:
            A retry decorator with the parameters customizable in configuration.
        """
        num_retries = kwargs.get('num_retries')
        retry_exceptions = kwargs.get('retry_exceptions')
        retry_min_wait = kwargs.get('retry_min_wait')
        retry_max_wait = kwargs.get('retry_max_wait')
        retry_multiplier = kwargs.get('retry_multiplier')

        return retry(
            before_sleep=self.log_retry_attempt,
            stop=stop_after_attempt(num_retries) | stop_if_should_exit(),
            reraise=True,
            retry=(retry_if_exception_type(retry_exceptions)),
            wait=wait_exponential(
                multiplier=retry_multiplier,
                min=retry_min_wait,
                max=retry_max_wait,
            ),
        )

    def log_retry_attempt(self, retry_state):
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
