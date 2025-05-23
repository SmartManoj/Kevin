import copy
import logging
import os
import re
import sys
import traceback
from datetime import datetime
from types import TracebackType
import warnings
from typing import Any, Literal, Mapping, MutableMapping, TextIO

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import litellm
from pythonjsonlogger.json import JsonFormatter
from termcolor import colored

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
DEBUG = os.getenv('DEBUG', '').lower() in ['true', '1']
DEBUG_LLM = os.getenv('DEBUG_LLM', '').lower() in ['true', '1']

# Structured logs with JSON, disabled by default
LOG_JSON = os.getenv('LOG_JSON', 'False').lower() in ['true', '1', 'yes']
LOG_JSON_LEVEL_KEY = os.getenv('LOG_JSON_LEVEL_KEY', 'level')


# Configure litellm logging based on DEBUG_LLM
if DEBUG_LLM:
    confirmation = input(
        '\n⚠️ WARNING: You are enabling DEBUG_LLM which may expose sensitive information like API keys.\n'
        'This should NEVER be enabled in production.\n'
        "Type 'y' to confirm you understand the risks: "
    )
    if confirmation.lower() == 'y':
        litellm.suppress_debug_info = False
        litellm.set_verbose = True
    else:
        print('DEBUG_LLM disabled due to lack of confirmation')
        litellm.suppress_debug_info = True
        litellm.set_verbose = False
else:
    litellm.suppress_debug_info = True
    litellm.set_verbose = False

if DEBUG:
    LOG_LEVEL = 'DEBUG'

DISABLE_COLOR_PRINTING = False

LOG_ALL_EVENTS = os.getenv('LOG_ALL_EVENTS', 'False').lower() in ['true', '1', 'yes']

# Controls whether to stream Docker container logs
DEBUG_RUNTIME = os.getenv('DEBUG_RUNTIME', 'False').lower() in ['true', '1', 'yes']

ColorType = Literal[
    'red',
    'green',
    'yellow',
    'blue',
    'magenta',
    'cyan',
    'light_grey',
    'dark_grey',
    'light_red',
    'light_green',
    'light_yellow',
    'light_blue',
    'light_magenta',
    'light_cyan',
    'white',
]

LOG_COLORS: Mapping[str, ColorType] = {
    'ACTION': 'green',
    'USER_ACTION': 'light_red',
    'OBSERVATION': 'yellow',
    'USER_OBSERVATION': 'light_green',
    'DETAIL': 'cyan',
    'ERROR': 'red',
    'PLAN': 'light_magenta',
}


class StackInfoFilter(logging.Filter):
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def filter(self, record):
        if record.levelno >= logging.ERROR:
            if os.getenv('DEBUG') == '2':
                record.stack_info =  self.logger.findCaller(True, 2)[-1]
            record.exc_info = sys.exc_info()
        return True


class NoColorFormatter(logging.Formatter):
    """Formatter for non-colored logging in files."""

    def format(self, record: logging.LogRecord) -> str:
        # Create a deep copy of the record to avoid modifying the original
        new_record = _fix_record(record)

        # Strip ANSI color codes from the message
        new_record.msg = strip_ansi(new_record.msg)

        
        if isinstance(new_record.exc_info, bool):
            new_record.exc_info = None
        return super().format(new_record)


def strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences (terminal color/formatting codes) from string.

    Removes ANSI escape sequences from str, as defined by ECMA-048 in
    http://www.ecma-international.org/publications/files/ECMA-ST/Ecma-048.pdf
    # https://github.com/ewen-lbh/python-strip-ansi/blob/master/strip_ansi/__init__.py
    """
    pattern = re.compile(r'\x1B\[\d+(;\d+){0,2}m')
    stripped = pattern.sub('', s)
    return stripped


class ColoredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg_type = record.__dict__.get('msg_type', '')
        event_source = record.__dict__.get('event_source', '')
        if event_source:
            new_msg_type = f'{event_source.upper()}_{msg_type}'
            if new_msg_type in LOG_COLORS:
                msg_type = new_msg_type
        if msg_type in LOG_COLORS and not DISABLE_COLOR_PRINTING:
            msg_type_color = colored(msg_type, LOG_COLORS[msg_type])
            msg = colored(record.msg, LOG_COLORS[msg_type])
            time_str = colored(
                self.formatTime(record, self.datefmt), LOG_COLORS[msg_type]
            )
            name_str = colored(record.name, LOG_COLORS[msg_type])
            level_str = colored(record.levelname, LOG_COLORS[msg_type])
            if msg_type in ['ERROR'] or DEBUG:
                return f'{time_str} - {name_str}:{level_str}: {record.filename}:{record.lineno}\n{msg_type_color}\n{msg}'
            return f'{time_str} - {msg_type_color}\n{msg}'
        elif msg_type == 'STEP':
            if LOG_ALL_EVENTS:
                msg = '\n\n==============\n' + record.msg + '\n'
                return f'{msg}'
            else:
                return record.msg

        new_record = _fix_record(record)
        return super().format(new_record)


def _fix_record(record: logging.LogRecord) -> logging.LogRecord:
    new_record = copy.copy(record)
    # The formatter expects non boolean values, and will raise an exception if there is a boolean - so we fix these
    # LogRecord attributes are dynamically typed
    if getattr(new_record, 'exc_info', None) is True:
        setattr(new_record, 'exc_info', sys.exc_info())
        setattr(new_record, 'stack_info', None)
    return new_record


file_formatter = NoColorFormatter(
    '%(asctime)s - %(name)s:%(levelname)s: %(filename)s:%(lineno)s - %(message)s',
    datefmt='%H:%M:%S',
)
llm_formatter = logging.Formatter('%(message)s')


class RollingLogger:
    max_lines: int
    char_limit: int
    log_lines: list[str]
    all_lines: str

    def __init__(self, max_lines: int = 10, char_limit: int = 80) -> None:
        self.max_lines = max_lines
        self.char_limit = char_limit
        self.log_lines = [''] * self.max_lines
        self.all_lines = ''

    def is_enabled(self) -> bool:
        return DEBUG and sys.stdout.isatty()

    def start(self, message: str = '') -> None:
        if message:
            print(message)
        self._write('\n' * self.max_lines)
        self._flush()

    def add_line(self, line: str) -> None:
        self.log_lines.pop(0)
        self.log_lines.append(line[: self.char_limit])
        self.print_lines()
        self.all_lines += line + '\n'

    def write_immediately(self, line: str) -> None:
        self._write(line)
        self._flush()

    def print_lines(self) -> None:
        """Display the last n log_lines in the console (not for file logging).

        This will create the effect of a rolling display in the console.
        """
        self.move_back()
        for line in self.log_lines:
            self.replace_current_line(line)

    def move_back(self, amount: int = -1) -> None:
        r"""'\033[F' moves the cursor up one line."""
        if amount == -1:
            amount = self.max_lines
        self._write('\033[F' * (self.max_lines))
        self._flush()

    def replace_current_line(self, line: str = '') -> None:
        r"""'\033[2K\r' clears the line and moves the cursor to the beginning of the line."""
        self._write('\033[2K' + line + '\n')
        self._flush()

    def _write(self, line: str) -> None:
        if not self.is_enabled():
            return
        sys.stdout.write(line)

    def _flush(self) -> None:
        if not self.is_enabled():
            return
        sys.stdout.flush()


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Gather sensitive values which should not ever appear in the logs.
        sensitive_values = []
        for key, value in os.environ.items():
            key_upper = key.upper()
            if (
                len(value) > 2
                and value != 'default'
                and any(s in key_upper for s in ('SECRET', '_KEY', '_CODE', '_TOKEN'))
            ):
                sensitive_values.append(value)

        # Replace sensitive values from env!
        msg = record.getMessage()
        for sensitive_value in sensitive_values:
            msg = msg.replace(sensitive_value, '******')

        # Replace obvious sensitive values from log itself...
        sensitive_patterns = [
            'api_key',
            'aws_access_key_id',
            'aws_secret_access_key',
            'e2b_api_key',
            'github_token',
            'jwt_secret',
            'modal_api_token_id',
            'modal_api_token_secret',
            'llm_api_key',
            'sandbox_env_github_token',
            'daytona_api_key',
        ]

        # add env var names
        env_vars = [attr.upper() for attr in sensitive_patterns]
        sensitive_patterns.extend(env_vars)

        for attr in sensitive_patterns:
            pattern = rf"({attr}='.)([\w_-]+?)([^']')"
            msg = re.sub(pattern, rf"\1******\3", msg)

        # Update the record
        record.msg = msg
        record.args = ()

        return True

class RedactDataUriFilter(logging.Filter):
    def filter(self, record):
        regex = r'data:(?P<mime>[\w/\-\.]+);(?P<encoding>\w+),(?P<data>.*)'
        record.msg = re.sub(regex, r'data:\g<mime>;base64,******', record.msg)
        return True

def get_console_handler(log_level: int = logging.INFO) -> logging.StreamHandler:
    """Returns a console handler for logging."""
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    formatter_str = '\033[92m%(asctime)s - %(name)s:%(levelname)s\033[0m: %(filename)s:%(lineno)s - %(message)s'
    console_handler.setFormatter(ColoredFormatter(formatter_str, datefmt='%H:%M:%S'))
    return console_handler


def get_file_handler(
    log_dir: str, log_level: int = logging.INFO
) -> logging.FileHandler:
    """Returns a file handler for logging."""
    os.makedirs(log_dir, exist_ok=True)
    file_name = 'console.log'
    full_path = os.path.join(log_dir, file_name)
    # clear the log file
    with open(full_path, 'w') as f:
        f.write('')
    file_handler = logging.FileHandler(os.path.join(log_dir, file_name))
    file_handler.setLevel(log_level)
    if LOG_JSON:
        file_handler.setFormatter(json_formatter())
    else:
        file_handler.setFormatter(file_formatter)
    return file_handler


def json_formatter() -> JsonFormatter:
    return JsonFormatter(
        '{message}{levelname}',
        style='{',
        rename_fields={'levelname': LOG_JSON_LEVEL_KEY},
        timestamp=True,
    )


def json_log_handler(
    level: int = logging.INFO,
    _out: TextIO = sys.stdout,
) -> logging.Handler:
    """
    Configure logger instance for structured logging as json lines.
    """

    handler = logging.StreamHandler(_out)
    handler.setLevel(level)
    handler.setFormatter(json_formatter())
    return handler


# Set up logging
logging.basicConfig(level=logging.ERROR)


def log_uncaught_exceptions(
    ex_cls: type[BaseException], ex: BaseException, tb: TracebackType | None
) -> Any:
    """Logs uncaught exceptions along with the traceback.

    Args:
        ex_cls: The type of the exception.
        ex: The exception instance.
        tb: The traceback object.

    Returns:
        None
    """
    if tb:  # Add check since tb can be None
        logging.error(''.join(traceback.format_tb(tb)))
    logging.error('{0}: {1}'.format(ex_cls, ex))


sys.excepthook = log_uncaught_exceptions
openhands_logger = logging.getLogger('openhands')
current_log_level = logging.INFO

if LOG_LEVEL in logging.getLevelNamesMapping():
    current_log_level = logging.getLevelNamesMapping()[LOG_LEVEL]
openhands_logger.setLevel(current_log_level)

if DEBUG:
    openhands_logger.addFilter(StackInfoFilter(openhands_logger))

if current_log_level == logging.DEBUG:
    LOG_TO_FILE = True
    openhands_logger.debug('DEBUG mode enabled.')

if LOG_JSON:
    openhands_logger.addHandler(json_log_handler(current_log_level))
else:
    openhands_logger.addHandler(get_console_handler(current_log_level))

openhands_logger.addFilter(SensitiveDataFilter(openhands_logger.name))
openhands_logger.addFilter(RedactDataUriFilter())
openhands_logger.propagate = False
openhands_logger.debug('Logging initialized')

LOG_DIR = os.path.join(
    # parent dir of openhands/core (i.e., root of the repo)
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'logs',
)
LOG_TO_FILE = True

if LOG_TO_FILE:
    openhands_logger.addHandler(
        get_file_handler(LOG_DIR, current_log_level)
    )  # default log to project root
    # openhands_logger.debug(f'Logging to file in: {LOG_DIR}')

# Exclude LiteLLM from logging output
logging.getLogger('LiteLLM').disabled = True
logging.getLogger('LiteLLM Router').disabled = True
logging.getLogger('LiteLLM Proxy').disabled = True


def clear_llm_logs(dir: str):
    """Clear all LLM logs in the given directory if not in debug mode.

    Args:
        dir (str): The directory to clear.
    """
    openhands_logger.debug(f'Clearing LLM logs in: {dir}')

    if continue_on_step_env := os.getenv('CONTINUE_ON_STEP'):
        continue_on_step = int(continue_on_step_env)
    else:
        continue_on_step = 0
    for file_name in os.listdir(dir):
        try:
            if (
                int(file_name.split('_')[0]) < continue_on_step
                and 'response' in file_name
            ):
                continue
        except Exception:
            pass
        file_path = os.path.join(dir, file_name)
        try:
            os.unlink(file_path)
        except Exception as e:
            openhands_logger.error('Failed to delete %s. Reason: %s', file_path, e)


class LlmFileHandler(logging.FileHandler):
    """LLM prompt and response logging."""

    def __init__(
        self,
        filename: str,
        mode: str = 'a',
        encoding: str = 'utf-8',
        delay: bool = False,
    ) -> None:
        """Initializes an instance of LlmFileHandler.

        Args:
            filename (str): The name of the log file.
            mode (str, optional): The file mode. Defaults to 'a'.
            encoding (str, optional): The file encoding. Defaults to None.
            delay (bool, optional): Whether to delay file opening. Defaults to False.
        """
        self.filename = filename
        self.message_counter = 1
        if DEBUG and not os.getenv('SINGLE_LOG_FOLDER'):
            self.session = datetime.now().strftime('%y-%m-%d_%H-%M')
        else:
            self.session = 'default'
        model_config = os.getenv('model_config')
        if model_config:
            with open('evaluation/benchmarks/swe_bench/config.toml', 'r') as f:
                environ = f.read()
                import toml

                config = toml.loads(environ)
                selection_id = config['selected_ids'][0]
            self.session = (
                model_config.split('.')[-1] + '_' + selection_id.split('-')[-1]
            )
        self.log_directory = os.path.join(LOG_DIR, 'llm', self.session)
        os.makedirs(self.log_directory, exist_ok=True)
        # Clear the log directory if not in debug mode
        clear_llm_logs(self.log_directory)
        # TODO: baseFilename is assigned in emit() too.
        filename = f'{self.filename}_{self.message_counter:03}.log'
        self.baseFilename = os.path.join(self.log_directory, filename)
        super().__init__(self.baseFilename, mode, encoding, delay)

    def emit(self, record: logging.LogRecord) -> None:
        """Emits a log record.

        Args:
            record (logging.LogRecord): The log record to emit.
        """
        filename = f'{self.message_counter:03}_{self.filename}.log'
        self.baseFilename = os.path.join(self.log_directory, filename)
        self.stream = self._open()
        super().emit(record)
        self.stream.close()
        openhands_logger.debug('Logging to %s', self.baseFilename)
        self.message_counter += 1

    def reset_counter(self):
        """Resets the message counter."""
        self.message_counter = 1
        clear_llm_logs(self.log_directory)

def _get_llm_file_handler(name: str, log_level: int) -> LlmFileHandler:
    # The 'delay' parameter, when set to True, postpones the opening of the log file
    # until the first log message is emitted.
    llm_file_handler = LlmFileHandler(name, delay=True)
    llm_file_handler.setFormatter(llm_formatter)
    llm_file_handler.setLevel(log_level)
    return llm_file_handler


def _setup_llm_logger(name: str, log_level: int) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(log_level)
    if LOG_TO_FILE:
        logger.addHandler(_get_llm_file_handler(name, log_level))
    return logger


llm_prompt_logger = _setup_llm_logger('prompt', current_log_level)
llm_response_logger = _setup_llm_logger('response', current_log_level)


class OpenHandsLoggerAdapter(logging.LoggerAdapter):
    extra: dict

    def __init__(
        self, logger: logging.Logger = openhands_logger, extra: dict | None = None
    ) -> None:
        self.logger = logger
        self.extra = extra or {}

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        """
        If 'extra' is supplied in kwargs, merge it with the adapters 'extra' dict
        Starting in Python 3.13, LoggerAdapter's merge_extra option will do this.
        """
        if 'extra' in kwargs and isinstance(kwargs['extra'], dict):
            kwargs['extra'] = {**self.extra, **kwargs['extra']}
        else:
            kwargs['extra'] = self.extra
        return msg, kwargs
