import logging
import os
import re
import sys
import traceback
from datetime import datetime
from typing import Literal, Mapping

from termcolor import colored

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
DEBUG = os.getenv('DEBUG', 'False').lower() in ['true', '1', 'yes']
LOG_TO_FILE = os.getenv('USER') not in ['openhands', 'root']
if DEBUG:
    LOG_LEVEL = 'DEBUG'

DISABLE_COLOR_PRINTING = False

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


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        msg_type = record.__dict__.get('msg_type')
        event_source = record.__dict__.get('event_source')
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
            msg = '\n\n==============\n' + record.msg + '\n'
            return f'{msg}'
        return super().format(record)


console_formatter = ColoredFormatter(
    '\033[92m%(asctime)s - %(name)s:%(levelname)s\033[0m: %(filename)s:%(lineno)s - %(message)s',
    datefmt='%H:%M:%S',
)

file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s:%(levelname)s: %(filename)s:%(lineno)s - %(message)s',
    datefmt='%H:%M:%S',
)
llm_formatter = logging.Formatter('%(message)s')


class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        # start with attributes
        sensitive_patterns = [
            'api_key',
            'aws_access_key_id',
            'aws_secret_access_key',
            'e2b_api_key',
            'github_token',
            'jwt_secret',
            'modal_api_token_id',
            'modal_api_token_secret',
        ]

        # add env var names
        env_vars = [attr.upper() for attr in sensitive_patterns]
        sensitive_patterns.extend(env_vars)

        # and some special cases
        sensitive_patterns.append('JWT_SECRET')
        sensitive_patterns.append('LLM_API_KEY')
        sensitive_patterns.append('GITHUB_TOKEN')
        sensitive_patterns.append('SANDBOX_ENV_GITHUB_TOKEN')

        # this also formats the message with % args
        msg = record.getMessage()
        record.args = ()

        for attr in sensitive_patterns:
            pattern = rf"{attr}='?([\w-]+)'?"
            msg = re.sub(pattern, f"{attr}='******'", msg)

        # passed with msg
        record.msg = msg
        return True


def get_console_handler(log_level=logging.INFO):
    """Returns a console handler for logging."""
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    return console_handler


def get_file_handler(log_dir, log_level=logging.INFO):
    """Returns a file handler for logging."""
    os.makedirs(log_dir, exist_ok=True)
    file_name = 'console.log'
    full_path = os.path.join(log_dir, file_name)
    # clear the log file
    with open(full_path, 'w') as f:
        f.write('')
    file_handler = logging.FileHandler(os.path.join(log_dir, file_name))
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    return file_handler


# Set up logging
logging.basicConfig(level=logging.ERROR)


def log_uncaught_exceptions(ex_cls, ex, tb):
    """Logs uncaught exceptions along with the traceback.

    Args:
        ex_cls (type): The type of the exception.
        ex (Exception): The exception instance.
        tb (traceback): The traceback object.

    Returns:
        None
    """
    logging.error(''.join(traceback.format_tb(tb)))
    logging.error('{0}: {1}'.format(ex_cls, ex))


sys.excepthook = log_uncaught_exceptions
openhands_logger = logging.getLogger('openhands')
current_log_level = logging.INFO

if LOG_LEVEL in logging.getLevelNamesMapping():
    current_log_level = logging.getLevelNamesMapping()[LOG_LEVEL]
openhands_logger.setLevel(current_log_level)

if current_log_level == logging.DEBUG:
    LOG_TO_FILE = True
    openhands_logger.info('DEBUG mode enabled.')

openhands_logger.addHandler(get_console_handler(current_log_level))
openhands_logger.addFilter(SensitiveDataFilter(openhands_logger.name))
openhands_logger.propagate = False
openhands_logger.debug('Logging initialized')

LOG_DIR = os.path.join(
    # parent dir of openhands/core (i.e., root of the repo)
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'logs',
)

if LOG_TO_FILE:
    openhands_logger.addHandler(
        get_file_handler(LOG_DIR, current_log_level)
    )  # default log to project root
    # openhands_logger.info(f'Logging to file in: {LOG_DIR}')

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
    """# LLM prompt and response logging"""

    def __init__(self, filename, mode='a', encoding='utf-8', delay=False):
        """Initializes an instance of LlmFileHandler.

        Args:
            filename (str): The name of the log file.
            mode (str, optional): The file mode. Defaults to 'a'.
            encoding (str, optional): The file encoding. Defaults to None.
            delay (bool, optional): Whether to delay file opening. Defaults to False.
        """
        self.filename = filename
        self.message_counter = 1
        if DEBUG:
            self.session = datetime.now().strftime('%y-%m-%d_%H-%M')
        else:
            model_config = os.getenv('model_config')
            if model_config is None:
                self.session = 'default'
            else:
                with open('evaluation/swe_bench/config.toml', 'r') as f:
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

    def emit(self, record):
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


def _get_llm_file_handler(name: str, log_level: int):
    # The 'delay' parameter, when set to True, postpones the opening of the log file
    # until the first log message is emitted.
    llm_file_handler = LlmFileHandler(name, delay=True)
    llm_file_handler.setFormatter(llm_formatter)
    llm_file_handler.setLevel(log_level)
    return llm_file_handler


def _setup_llm_logger(name: str, log_level: int):
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(log_level)
    if LOG_TO_FILE:
        logger.addHandler(_get_llm_file_handler(name, log_level))
    return logger


llm_prompt_logger = _setup_llm_logger('prompt', logging.DEBUG)
llm_response_logger = _setup_llm_logger('response', logging.DEBUG)
