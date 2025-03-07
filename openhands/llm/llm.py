import copy
import os
import warnings
from functools import partial
from time import sleep
from typing import Any, Union, Callable

import requests

from openhands.core import config2
from openhands.core.config import LLMConfig
from openhands.utils.ensure_httpx_close import ensure_httpx_close

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import litellm

from litellm import ChatCompletionMessageToolCall, ModelInfo, PromptTokensDetails
from litellm import Message as LiteLLMMessage
from litellm import completion as litellm_completion
from litellm import completion_cost as litellm_completion_cost
from litellm.exceptions import (
    RateLimitError,
)
from litellm.types.utils import CostPerToken, ModelResponse, Usage
from litellm.utils import create_pretrained_tokenizer

from openhands.core.logger import openhands_logger as logger
from openhands.core.message import Message
from openhands.core.message import TextContent
from openhands.llm.fn_call_converter import (
    STOP_WORDS,
    convert_fncall_messages_to_non_fncall_messages,
    convert_non_fncall_messages_to_fncall_messages,
)

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import litellm

    if os.getenv('DEBUG_LITTELM'):
        os.environ['LITELLM_LOG'] = 'DEBUG'
    else:
        litellm.suppress_debug_info = True
from litellm import ChatCompletionMessageToolCall, ModelInfo, PromptTokensDetails
from litellm import Message as LiteLLMMessage
from litellm import completion as litellm_completion
from litellm import completion_cost as litellm_completion_cost

# from litellm.caching import Cache
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    ContextWindowExceededError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)
from litellm.llms.openai_like.common_utils import OpenAILikeError
from litellm.types.utils import CostPerToken, ModelResponse, Usage
from litellm.utils import create_pretrained_tokenizer

from openhands.condenser.condenser import CondenserMixin
from openhands.core.logger import LOG_DIR
from openhands.core.logger import openhands_logger as logger
from openhands.core.metrics import Metrics
from openhands.llm.debug_mixin import DebugMixin
from openhands.llm.retry_mixin import RetryMixin

__all__ = ['LLM']

# tuple of exceptions to retry on
LLM_RETRY_EXCEPTIONS: tuple[type[Exception], ...] = (
        APIConnectionError,
        # FIXME: APIError is useful on 502 from a proxy for example,
        # but it also retries on other errors that are permanent
        APIError,
        InternalServerError,
        RateLimitError,
        ServiceUnavailableError,
    )

# cache prompt supporting models
# remove this when we gemini and deepseek are supported
CACHE_PROMPT_SUPPORTED_MODELS = [
    'claude-3-7-sonnet-20250219',
    'claude-3-5-sonnet-20241022',
    'claude-3-5-sonnet-20240620',
    'claude-3-5-haiku-20241022',
    'claude-3-haiku-20240307',
    'claude-3-opus-20240229',
]

# function calling supporting models
FUNCTION_CALLING_SUPPORTED_MODELS = [
    'claude-3-7-sonnet-20250219',
    'claude-3-5-sonnet',
    'claude-3-5-sonnet-20240620',
    'claude-3-5-sonnet-20241022',
    'claude-3.5-haiku',
    'claude-3-5-haiku-20241022',
    'gpt-4o-mini',
    'gpt-4o',
    'grok-beta',
    'o1-2024-12-17',
    'o3-mini-2025-01-31',
    'o3-mini',
]

REASONING_EFFORT_SUPPORTED_MODELS = [
    'o1-2024-12-17',
    'o1',
    'o3-mini-2025-01-31',
    'o3-mini',
]

MODELS_WITHOUT_STOP_WORDS = [
    'o1-mini',
    'o1-preview',
    'o1',
    'o1-2024-12-17',
]


class LLM(RetryMixin, DebugMixin, CondenserMixin):
    """The LLM class represents a Language Model instance.

    Attributes:
        config: an LLMConfig object specifying the configuration of the LLM.
    """

    def __init__(
        self,
        config: LLMConfig,
        metrics: Metrics | None = None,
        retry_listener: Callable[[int, int], None] | None = None,
    ):
        """Initializes the LLM. If LLMConfig is passed, its values will be the fallback.

        Passing simple parameters always overrides config.

        Args:
            config: The LLM configuration.
            metrics: The metrics to use.
        """
        self._tried_model_info = False
        self.metrics: Metrics = (
            metrics if metrics is not None else Metrics(model_name=config.model)
        )
        self.cost_metric_supported: bool = True
        self.config: LLMConfig = copy.deepcopy(config)
        self.log_prompt_once = True
        self.reload_counter = 0
        self.api_idx = 0

        # if self.config.enable_cache:
        #     litellm.cache = Cache()

        self.model_info: ModelInfo | None = None
        self.retry_listener = retry_listener
        if self.config.log_completions:
            if self.config.log_completions_folder is None:
                raise RuntimeError(
                    'log_completions_folder is required when log_completions is enabled'
                )
            os.makedirs(self.config.log_completions_folder, exist_ok=True)

        # call init_model_info to initialize config.max_output_tokens
        # which is used in partial function
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self.init_model_info()
        if self.vision_is_active():
            logger.debug('LLM: model has vision enabled')
        if self.is_caching_prompt_active():
            logger.debug('LLM: caching prompt enabled')
        if self.is_function_calling_active():
            logger.debug('LLM: model supports function calling')

        logger.info(f'{self.config.model=}')
        logger.info(f'{self.config.max_input_tokens=}')
        logger.info(f'{self.config.max_output_tokens=}')
        if os.getenv('DEBUG_KEY'):
            logger.debug(
                f'{self.config.api_key=}'
            )
        if self.config.drop_params:
            litellm.drop_params = self.config.drop_params

        if self.config.model.startswith('ollama'):
            max_input_tokens = self.config.max_input_tokens
            max_output_tokens = self.config.max_output_tokens
            if max_input_tokens and max_output_tokens:
                logger.info(f'{max_input_tokens=}, {max_output_tokens=}')
                total = max_input_tokens + max_output_tokens
                litellm.OllamaConfig.num_ctx = total
                logger.info(f'Setting OllamaConfig.num_ctx to {total}')

        if self.config.model.split('/')[-1].startswith('o1-'):
            #  temperature, top_p and n are fixed at 1, while presence_penalty and frequency_penalty are fixed at 0.
            self.config.temperature = 1
            self.config.top_p = 1
        # Compatibility flag: use string serializer for DeepSeek models
        # See this issue: https://github.com/All-Hands-AI/OpenHands/issues/5818
        self._use_string_serializer = False
        if 'deepseek' in self.config.model:
            self._use_string_serializer = True

        # if using a custom tokenizer, make sure it's loaded and accessible in the format expected by litellm
        if self.config.custom_tokenizer is not None:
            self.tokenizer = create_pretrained_tokenizer(self.config.custom_tokenizer)
        else:
            self.tokenizer = None

        # set up the completion function
        kwargs: dict[str, Any] = {
            'temperature': self.config.temperature,
        }
        if (
            self.config.model.lower() in REASONING_EFFORT_SUPPORTED_MODELS
            or self.config.model.split('/')[-1] in REASONING_EFFORT_SUPPORTED_MODELS
        ):
            kwargs['reasoning_effort'] = self.config.reasoning_effort
            kwargs.pop(
                'temperature'
            )  # temperature is not supported for reasoning models
        # Azure issue: https://github.com/All-Hands-AI/OpenHands/issues/6777
        if self.config.model.startswith('azure'):
            kwargs['max_tokens'] = self.config.max_output_tokens

        # if o3-mini or o3-mini-2025-01-31, add max_completion_tokens
        if self.config.model.split('/')[-1] in ['o3-mini', 'o3-mini-2025-01-31']:
            kwargs['max_completion_tokens'] = self.config.max_output_tokens
        self._completion = partial(
            litellm_completion,
            model=self.config.model,
            api_key=self.config.api_key.get_secret_value()
            if self.config.api_key
            else None,
            base_url=self.config.base_url,
            api_version=self.config.api_version,
            custom_llm_provider=self.config.custom_llm_provider,
            timeout=self.config.timeout,
            top_p=self.config.top_p,
            caching=self.config.enable_cache,
            drop_params=self.config.drop_params,
            seed=self.config.seed,
            **kwargs,
        )

        def is_hallucination(text) -> bool:
            lines = text.strip().split('\n')
            if len(lines) < 2:
                return False
            line_index = -2
            while line_index >= -len(lines):
                second_last_line = lines[line_index].strip()
                if second_last_line.strip():
                    break
                line_index -= 1
            repetition_count = sum(
                1 for line in lines if line.strip() == second_last_line
            )
            return repetition_count >= 5

        self._completion_unwrapped = self._completion

        @self.retry_decorator(
            num_retries=self.config.num_retries,
            retry_exceptions=LLM_RETRY_EXCEPTIONS,
            retry_min_wait=self.config.retry_min_wait,
            retry_max_wait=self.config.retry_max_wait,
            retry_multiplier=self.config.retry_multiplier,
            retry_listener=self.retry_listener,
        )
        def wrapper(*args, **kwargs):
            """Wrapper for the litellm completion function. Logs the input and output of the completion function."""
            messages: list[Message] | Message = []
            from openhands.io import json

            mock_function_calling = not self.is_function_calling_active()

            if self.config.model.split('/')[-1].startswith('o1-mini'):
                kwargs['messages'].append(Message(role='assistant', content=[TextContent(text='DO NOT PRODUCE INVALID CONTENT')]))

            # some callers might send the model and messages directly
            # litellm allows positional args, like completion(model, messages, **kwargs)
            if len(args) > 1:
                # ignore the first argument if it's provided (it would be the model)
                # design wise: we don't allow overriding the configured values
                # implementation wise: the partial function set the model as a kwarg already
                # as well as other kwargs
                messages = args[1] if len(args) > 1 else args[0]
                kwargs['messages'] = messages

                # remove the first args, they're sent in kwargs
                args = args[2:]
            elif 'messages' in kwargs:
                messages = kwargs['messages']

            # ensure we work with a list of messages
            messages = messages if isinstance(messages, list) else [messages]
            if isinstance(messages[0], Message):
                messages = self.format_messages_for_llm(messages)
                kwargs['messages'] = messages
            # original_fncall_messages = copy.deepcopy(messages)
            mock_fncall_tools = None
            # if the agent or caller has defined tools, and we mock via prompting, convert the messages
            if mock_function_calling and 'tools' in kwargs:
                messages = convert_fncall_messages_to_non_fncall_messages(
                    messages,  # type: ignore
                    kwargs['tools'],  # type: ignore
                )
                kwargs['messages'] = messages

                # add stop words if the model supports it
                if self.config.model not in MODELS_WITHOUT_STOP_WORDS:
                    kwargs['stop'] = STOP_WORDS

                mock_fncall_tools = kwargs.pop('tools')
                # tool_choice should not be specified when mocking function calling
                kwargs.pop('tool_choice', None)

            if self.config.model.split('/')[-1].startswith('o1-'):
                # Message types: user and assistant messages only, system messages are not supported.
                messages[0]['role'] = 'user'

            if self.is_over_token_limit(messages):
                # if kwargs['condense'] and 0:
                #     summary_action = self.condense(messages=messages)
                #     return summary_action
                raise ContextWindowExceededError(
                    message='Context window exceeded',
                    model=self.config.model.split('/', 1)[1],
                    llm_provider=self.config.model.split('/', 1)[0],
                )

            kwargs.pop('condense', None)

            if not messages:
                raise ValueError(
                    'The messages list is empty. At least one message is required.'
                )

            # log the entire LLM prompt
            self.log_prompt(messages)

            if self.is_caching_prompt_active():
                # Anthropic-specific prompt caching
                if 'claude-3' in self.config.model:
                    kwargs['extra_headers'] = {
                        'anthropic-beta': 'prompt-caching-2024-07-31',
                    }
            source = kwargs.pop('origin', None)
            resp = {}
            if (
                continue_on_step_env := os.environ.get('CONTINUE_ON_STEP')
            ) and source == 'Agent':
                # int
                continue_on_step = int(continue_on_step_env)
                self.reload_counter += 1
                if self.reload_counter < continue_on_step:
                    model_config = os.getenv('model_config')
                    if model_config:
                        with open(
                            'evaluation/benchmarks/swe_bench/config.toml', 'r'
                        ) as f:
                            environ = f.read()
                            import toml

                            config = toml.loads(environ)
                            selection_id = config['selected_ids'][0]
                        session = (
                            model_config.split('.')[-1]
                            + '_'
                            + selection_id.split('-')[-1]
                        )
                    else:
                        session = 'default'
                    log_directory = os.path.join(LOG_DIR, 'llm', session)
                    filename = f'{self.reload_counter:03}_response.log'
                    file_name = os.path.join(log_directory, filename)
                    if os.path.exists(file_name):
                        logger.info('Using cached response')
                        with open(file_name, 'r') as f:
                            message_back = f.read()
                        with open(file_name, 'w') as f:
                            f.write('')
                        if message_back:
                            resp = {'choices': [{'message': {'content': message_back}}]}
                            
           

            # set litellm modify_params to the configured value
            # True by default to allow litellm to do transformations like adding a default message, when a message is empty
            # NOTE: this setting is global; unlike drop_params, it cannot be overridden in the litellm completion partial
            litellm.modify_params = self.config.modify_params

            if resp:
                pass
            else:
                kwargs2 = kwargs.copy()
                for _ in range(5):
                    if os.getenv('attempt_number'):
                        attempt_number = int(os.getenv('attempt_number', '-1'))
                        if attempt_number != -1 and 'gemini/' in config2.model:
                            try:
                                from api_keys import api_keys

                                self.api_idx = (self.api_idx + 1) % len(api_keys)
                                print('Using API key', self.api_idx)
                                kwargs['api_key'] = api_keys[self.api_idx]
                            except Exception as e:
                                print('Error in changing API key', e)
                                pass
                            os.environ['attempt_number'] = '-1'
                    logger.debug(f'Calling LLM ...')
                    self.log_first_request(*args, **kwargs)
                    resp = self._completion_unwrapped(*args, **kwargs)
                    # # non_fncall_response = copy.deepcopy(resp)
                    # if mock_function_calling:
                    #     # assert len(resp.choices) == 1
                    #     assert mock_fncall_tools is not None
                    #     non_fncall_response_message = resp.choices[0].message  # type: ignore
                    #     fn_call_messages_with_response = (
                    #         convert_non_fncall_messages_to_fncall_messages(
                    #             messages + [non_fncall_response_message],
                    #             mock_fncall_tools,
                    #         )
                    #     )  # type: ignore
                    #     fn_call_response_message = fn_call_messages_with_response[-1]
                    #     if not isinstance(fn_call_response_message, LiteLLMMessage):
                    #         fn_call_response_message = LiteLLMMessage(
                    #             **fn_call_response_message
                    #         )
                    #     resp.choices[0].message = fn_call_response_message  # type: ignore
                    message_back = resp['choices'][0]['message']['content'] or ''
                    self_analyse = int(os.environ.get('SELF_ANALYSE', '0'))
                    if self_analyse:
                        logger.info(f'{self_analyse=}')
                        kwargs2['messages'].append(
                            {'role': 'assistant', 'content': message_back}
                        )
                        self_analyse_question = (
                            'If the above approach is wrong, just reply yes.'
                        )
                        kwargs2['messages'].append(
                            {'role': 'user', 'content': self_analyse_question}
                        )
                        self_analyse_response = self._completion_unwrapped(
                            *args, **kwargs2
                        )
                        self_analyse_response_content = self_analyse_response[
                            'choices'
                        ][0]['message']['content'].strip()
                        print(f'{self_analyse_response_content=}')
                        if self_analyse_response_content == 'yes':
                            logger.info(
                                f'Response is incorrect. {self_analyse_response_content}'
                            )
                            new_messages = [
                                {'role': 'assistant', 'content': message_back},
                                {'role': 'user', 'content': self_analyse_question},
                                {
                                    'role': 'assistant',
                                    'content': self_analyse_response_content,
                                },
                                {
                                    'role': 'user',
                                    'content': 'Then, please correctly respond.',
                                },
                            ]
                            kwargs['messages'].extend(new_messages)
                            continue
                    if message_back and message_back != 'None':
                        if is_hallucination(message_back):
                            logger.warning(f'Hallucination detected!\n{message_back}')
                            sleep(2)
                            continue
                        break
                    else:
                        msg = 'Why are you not responding to the user?'
                        kwargs['messages'].append({'role': 'user', 'content': msg})
                        logger.warning('No completion messages!')

                message_back = resp['choices'][0]['message']['content'] or ''

                # think model tweaks; add <think> to the beginning of the response if it's not there
                if not message_back.startswith('<think>') and '</think>' in message_back:
                    message_back = '<think>\n' + message_back
                    resp['choices'][0]['message']['content'] = message_back

                tool_calls: list[ChatCompletionMessageToolCall] = resp['choices'][0][
                    'message'
                ].get('tool_calls', [])  # type: ignore
                if tool_calls:
                    for tool_call in tool_calls:
                        fn_name: str = tool_call.function.name  # type: ignore
                        fn_args: str = tool_call.function.arguments  # type: ignore
                        message_back += f'\nFunction call: {fn_name}({fn_args})'

            # log the LLM response
            self.log_response(message_back)
            if not os.environ.get('DISABLE_METRICS'):
                # post-process to log costs
                self._post_completion(resp)
            return resp

        self._completion = wrapper

    @property
    def completion(self):
        """Decorator for the litellm completion function.

        Check the complete documentation at https://litellm.vercel.app/docs/completion
        """
        return self._completion

    def init_model_info(self):
        if self._tried_model_info:
            return
        self._tried_model_info = True
        try:
            if self.config.model.startswith('openrouter'):
                self.model_info = litellm.get_model_info(self.config.model)
        except Exception as e:
            logger.debug(f'Error getting model info: {e}')

        if self.config.model.startswith('litellm_proxy/'):
            # IF we are using LiteLLM proxy, get model info from LiteLLM proxy
            # GET {base_url}/v1/model/info with litellm_model_id as path param
            response = requests.get(
                f'{self.config.base_url}/v1/model/info',
                headers={
                    'Authorization': f'Bearer {self.config.api_key.get_secret_value() if self.config.api_key else None}'
                },
            )
            resp_json = response.json()
            if 'data' not in resp_json:
                logger.error(
                    f'Error getting model info from LiteLLM proxy: {resp_json}'
                )
            all_model_info = resp_json.get('data', [])
            current_model_info = next(
                (
                    info
                    for info in all_model_info
                    if info['model_name']
                    == self.config.model.removeprefix('litellm_proxy/')
                ),
                None,
            )
            if current_model_info:
                self.model_info = current_model_info['model_info']

        # Last two attempts to get model info from NAME
        if not self.model_info:
            try:
                self.model_info = litellm.get_model_info(
                    self.config.model.split(':')[0]
                )
            # noinspection PyBroadException
            except Exception:
                pass
        if not self.model_info:
            try:
                self.model_info = litellm.get_model_info(
                    self.config.model.split('/')[-1]
                )
            # noinspection PyBroadException
            except Exception:
                pass
        from openhands.io import json

        # logger.debug(f'Model info: {json.dumps(self.model_info, indent=2)}')

        if self.config.model.startswith('huggingface'):
            # HF doesn't support the OpenAI default value for top_p (1)
            logger.debug(
                f'Setting top_p to 0.9 for Hugging Face model: {self.config.model}'
            )
            self.config.top_p = 0.9 if self.config.top_p == 1 else self.config.top_p

        # Set the max tokens in an LM-specific way if not set
        if self.config.max_input_tokens is None:
            if (
                self.model_info is not None
                and 'max_input_tokens' in self.model_info
                and isinstance(self.model_info['max_input_tokens'], int)
            ):
                self.config.max_input_tokens = self.model_info['max_input_tokens']
            else:
                # Safe fallback for any potentially viable model
                self.config.max_input_tokens = 4096

        if self.config.max_output_tokens is None:
            # Safe default for any potentially viable model
            self.config.max_output_tokens = 4096
            if self.model_info is not None:
                # max_output_tokens has precedence over max_tokens, if either exists.
                # litellm has models with both, one or none of these 2 parameters!
                self.config.max_output_tokens = self.model_info.get('max_output_tokens') or self.model_info.get('max_tokens')
            if 'claude-3-7-sonnet' in self.config.model:
                self.config.max_output_tokens = 64000  # litellm set max to 128k, but that requires a header to be set

        # Initialize function calling capability
        # Check if model name is in our supported list
        model_name_supported = (
            self.config.model in FUNCTION_CALLING_SUPPORTED_MODELS
            or self.config.model.split('/')[-1] in FUNCTION_CALLING_SUPPORTED_MODELS
            or any(m in self.config.model for m in FUNCTION_CALLING_SUPPORTED_MODELS)
        )

        # Handle native_tool_calling user-defined configuration
        if self.config.native_tool_calling is None:
            self._function_calling_active = model_name_supported
        elif self.config.native_tool_calling is False:
            self._function_calling_active = False
        else:
            # try to enable native tool calling if supported by the model
            self._function_calling_active = litellm.supports_function_calling(
                model=self.config.model
            )

    def vision_is_active(self) -> bool:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            return not self.config.disable_vision and self._supports_vision()

    def _supports_vision(self) -> bool:
        """Acquire from litellm if model is vision capable.

        Returns:
            bool: True if model is vision capable. Return False if model not supported by litellm.
        """
        # litellm.supports_vision currently returns False for 'openai/gpt-...' or 'anthropic/claude-...' (with prefixes)
        # but model_info will have the correct value for some reason.
        # we can go with it, but we will need to keep an eye if model_info is correct for Vertex or other providers
        # remove when litellm is updated to fix https://github.com/BerriAI/litellm/issues/5608
        # Check both the full model name and the name after proxy prefix for vision support
        return (
            litellm.supports_vision(self.config.model)
            or litellm.supports_vision(self.config.model.split('/')[-1])
            or (
                self.model_info is not None
                and self.model_info.get('supports_vision', False)
            )
        )

    def is_caching_prompt_active(self) -> bool:
        """Check if prompt caching is supported and enabled for current model.

        Returns:
            boolean: True if prompt caching is supported and enabled for the given model.
        """
        if self.config.model.startswith('gemini'):
            # GeminiException - Gemini Context Caching only supports 1 message/block of continuous messages. Cause: Environment reminder is added in the prompt?
            return False
        return (
            self.config.caching_prompt is True
            and (
                self.config.model in CACHE_PROMPT_SUPPORTED_MODELS
                or self.config.model.split('/')[-1] in CACHE_PROMPT_SUPPORTED_MODELS
            )
            # We don't need to look-up model_info, because only Anthropic models needs the explicit caching breakpoint
        )

    def is_function_calling_active(self) -> bool:
        """Returns whether function calling is supported and enabled for this LLM instance.

        The result is cached during initialization for performance.
        """
        return self._function_calling_active

    def _post_completion(self, response: ModelResponse) -> float:
        """Post-process the completion response.

        Logs the cost and usage stats of the completion call.
        """
        try:
            cur_cost = self._completion_cost(response)
        except Exception:
            cur_cost = 0

        stats = ''
        if self.cost_metric_supported:
            # keep track of the cost
            stats = 'Cost: %.2f USD | Accumulated Cost: %.2f USD\n' % (
                cur_cost,
                self.metrics.accumulated_cost,
            )

        # Add latency to stats if available
        if self.metrics.response_latencies:
            latest_latency = self.metrics.response_latencies[-1]
            stats += 'Response Latency: %.3f seconds\n' % latest_latency.latency

        usage: Usage | None = response.get('usage')
        response_id = response.get('id', 'unknown')

        if usage:
            # keep track of the input and output tokens
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)

            if prompt_tokens:
                stats += 'Input tokens: ' + str(prompt_tokens)

            if completion_tokens:
                stats += (
                    (' | ' if prompt_tokens else '')
                    + 'Output tokens: '
                    + str(completion_tokens)
                    + '\n'
                )

            # read the prompt cache hit, if any
            prompt_tokens_details: PromptTokensDetails = usage.get(
                'prompt_tokens_details'
            )
            cache_hit_tokens = (
                prompt_tokens_details.cached_tokens if prompt_tokens_details else 0
            )
            if cache_hit_tokens:
                stats += 'Input tokens (cache hit): ' + str(cache_hit_tokens) + '\n'

            # For Anthropic, the cache writes have a different cost than regular input tokens
            # but litellm doesn't separate them in the usage stats
            # so we can read it from the provider-specific extra field
            model_extra = usage.get('model_extra', {})
            cache_write_tokens = model_extra.get('cache_creation_input_tokens', 0)
            if cache_write_tokens:
                stats += 'Input tokens (cache write): ' + str(cache_write_tokens) + '\n'

            # Record in metrics
            # We'll treat cache_hit_tokens as "cache read" and cache_write_tokens as "cache write"
            self.metrics.add_token_usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cache_read_tokens=cache_hit_tokens,
                cache_write_tokens=cache_write_tokens,
                response_id=response_id,
            )

        # log the stats
        # if stats:
        #     logger.debug(stats)

        return cur_cost

    def get_token_count(self, messages=None, text=None) -> int:
        """Get the number of tokens in a list of messages. Use dicts for better token counting.

        Args:
            messages (list): A list of messages, either as a list of dicts or as a list of Message objects.
        Returns:
            int: The number of tokens.
        """
        # attempt to convert Message objects to dicts, litellm expects dicts
        if (
            isinstance(messages, list)
            and len(messages) > 0
            and isinstance(messages[0], Message)
        ):
            # logger.info(
            #     'Message objects now include serialized tool calls in token counting'
            # )
            messages = self.format_messages_for_llm(messages)  # type: ignore

        # try to get the token count with the default litellm tokenizers
        # or the custom tokenizer if set for this LLM configuration
        try:
            return litellm.token_counter(
                model=self.config.model,
                messages=messages,
                custom_tokenizer=self.tokenizer,
                text=text,
            )
        except Exception as e:
            # limit logspam in case token count is not supported
            logger.error(
                f'Error getting token count for\n model {self.config.model}\n{e}'
                + (
                    f'\ncustom_tokenizer: {self.config.custom_tokenizer}'
                    if self.config.custom_tokenizer is not None
                    else ''
                )
            )
            return 0

    def _is_local(self) -> bool:
        """Determines if the system is using a locally running LLM.

        Returns:
            boolean: True if executing a local model.
        """
        if self.config.base_url is not None:
            for substring in ['localhost', '127.0.0.1' '0.0.0.0']:
                if substring in self.config.base_url:
                    return True
        elif self.config.model is not None:
            if self.config.model.startswith('ollama'):
                return True
        return False

    def _completion_cost(self, response) -> float:
        """Calculate completion cost and update metrics with running total.

        Calculate the cost of a completion response based on the model. Local models are treated as free.
        Add the current cost into total cost in metrics.

        Args:
            response: A response from a model invocation.

        Returns:
            number: The cost of the response.
        """
        if os.getenv('IGNORE_COST'):
            return 0.0
        if not self.cost_metric_supported:
            return 0.0

        extra_kwargs = {}
        if (
            self.config.input_cost_per_token is not None
            and self.config.output_cost_per_token is not None
        ):
            cost_per_token = CostPerToken(
                input_cost_per_token=self.config.input_cost_per_token,
                output_cost_per_token=self.config.output_cost_per_token,
            )
            logger.debug(f'Using custom cost per token: {cost_per_token}')
            extra_kwargs['custom_cost_per_token'] = cost_per_token

        # try directly get response_cost from response
        _hidden_params = getattr(response, '_hidden_params', {})
        cost = _hidden_params.get('additional_headers', {}).get(
            'llm_provider-x-litellm-response-cost', None
        )
        if cost is not None:
            cost = float(cost)
            logger.debug(f'Got response_cost from response: {cost}')

        try:
            if cost is None:
                try:
                    cost = litellm_completion_cost(
                        completion_response=response, **extra_kwargs
                    )
                except Exception as e:
                    logger.error(f'Error getting cost from litellm: {e}')

            if cost is None:
                _model_name = '/'.join(self.config.model.split('/')[1:])
                cost = litellm_completion_cost(
                    completion_response=response, model=_model_name, **extra_kwargs
                )
                logger.debug(
                    f'Using fallback model name {_model_name} to get cost: {cost}'
                )
            self.metrics.add_cost(cost)
            return cost
        except Exception:
            self.cost_metric_supported = False
            logger.debug('Cost calculation not supported for this model.')
        return 0.0

    def __str__(self):
        if self.config.api_version:
            return f'LLM(model={self.config.model}, api_version={self.config.api_version}, base_url={self.config.base_url})'
        elif self.config.base_url:
            return f'LLM(model={self.config.model}, base_url={self.config.base_url})'
        return f'LLM(model={self.config.model})'

    def __repr__(self):
        return str(self)

    def reset(self) -> None:
        self.metrics.reset()

    def is_over_token_limit(self, messages: list[Message]) -> bool:
        """
        Estimates the token count of the given events using litellm tokenizer and returns True if over the max_input_tokens value.

        Parameters:
        - messages: List of messages to estimate the token count for.

        Returns:
        - Estimated token count.
        """
        # max_input_tokens will always be set in init to some sensible default
        # 0 in config.llm disables the check
        MAX_TOKEN_COUNT_PADDING = 512
        if not self.config.max_input_tokens:
            return False
        token_count = self.get_token_count(messages=messages) + MAX_TOKEN_COUNT_PADDING
        output = token_count >= self.config.max_input_tokens
        if output or 1:
            logger.info(f'Token count: {token_count}')
        return output

    def get_text_messages(self, messages: list[Message]) -> list[dict]:
        text_messages = []
        for message in messages:
            text_messages.append(message.model_dump())
        return text_messages

    def format_messages_for_llm(
        self, messages: Union[Message, list[Message]]
    ) -> list[dict]:
        if isinstance(messages, Message):
            messages = [messages]

        # set flags to know how to serialize the messages
        for message in messages:
            message.cache_enabled = self.is_caching_prompt_active()
            message.vision_enabled = self.vision_is_active()
            message.function_calling_enabled = self.is_function_calling_active()
            if 'deepseek' in self.config.model:
                message.force_string_serializer = True

        # let pydantic handle the serialization
        return [message.model_dump() for message in messages]


if __name__ == '__main__':
    from openhands.core.config.utils import get_llm_config_arg
    config = get_llm_config_arg('hf')
    llm = LLM(config=config)
    messages = [Message(role='user', content=[TextContent(text='Hello, world!')])]
    print(llm.format_messages_for_llm(messages))
