"""File operations module for OpenHands agent.

This module provides a collection of file manipulation skills that enable the OpenHands
agent to perform various file operations such as opening, searching, and navigating
through files and directories.

Functions:
- open_file(path: str, line_number: int | None = 1, context_lines: int = 100): Opens a file and optionally moves to a specific line.

- goto_line(line_number: int): Moves the window to show the specified line number.
- scroll_down(): Moves the window down by the number of lines specified in WINDOW.
- scroll_up(): Moves the window up by the number of lines specified in WINDOW.
- search_dir(search_term: str, dir_path: str = './'): Searches for a term in all files in the specified directory.
- search_file(search_term: str, file_path: str | None = None): Searches for a term in the specified file or the currently open file.

- find_file(file_name: str, dir_path: str = './'): Finds all files with the given name in the specified directory.

- find_and_replace(file_name: str, find_string: str, replace_string: str): Replaces specific content in a file with new content.
- insert_content_at_line(file_name: str, line_number: int, content: str): Inserts given content at the specified line number in a file.
- delete_line(file_name: str, line_number: int): Deletes the line at the given line number in a file.
- replace_file_content(file_name: str, new_content: str): Replaces the content of the specified file with the given content.
- append_file(file_name: str, content: str): Appends the given content to the end of the specified file.

- kill_port(port_number: int): Kills the process running on the specified port.
"""

import ast
import getpass
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

from openhands.linter import DefaultLinter, LintResult
from openhands.runtime.plugins.agent_skills.file_ops.ast_ops import (
    show_class_structure,
    show_file_structure,
)

CURRENT_FILE: str | None = None
CURRENT_LINE = 1
WINDOW = 100
LAST_WINDOW = 100
SMALL_WINDOW = 20

# This is also used in unit tests!
MSG_FILE_UPDATED = '[File updated (edited at line {line_number}). Please review the changes and make sure they are correct (correct indentation, no duplicate lines, etc). Edit the file again if necessary.]'
LINTER_ERROR_MSG = '[Your proposed edit has introduced new error(s). Please explain why you thought it would work and fix the errors.]\n'


# ==================================================================================================


def _output_error(error_msg: str) -> bool:
    print(f'ERROR: {error_msg}')
    return False


def _is_valid_filename(file_name) -> bool:
    if not file_name or not isinstance(file_name, str) or not file_name.strip():
        return False
    invalid_chars = '<>:"/\\|?*'
    if os.name == 'nt':  # Windows
        invalid_chars = '<>"|?*'
    elif os.name == 'posix':  # Unix-like systems
        invalid_chars = '\0'

    for char in invalid_chars:
        if char in file_name:
            return False
    return True


def _is_valid_path(path) -> bool:
    if not path or not isinstance(path, str):
        return False
    try:
        return os.path.exists(os.path.normpath(path))
    except PermissionError:
        return False


def _create_paths(file_name) -> bool:
    try:
        dirname = os.path.dirname(file_name)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        return True
    except PermissionError:
        return False


def _check_current_file(file_path: str | None = None) -> bool:
    global CURRENT_FILE
    if not file_path:
        file_path = CURRENT_FILE
    if not file_path:
        return _output_error('No file open. Use the open_file function first.')
    if not check_file_exists(file_path):
        return False
    return True


def _clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def _lint_file(file_path: str) -> tuple[str | None, int | None]:
    """Perform linting on a file and identify the first error location.

    Lint the file at the given path and return a tuple with a boolean indicating if there are errors,
    and the line number of the first error, if any.

    Args:
        file_path: str: The path to the file to lint.

    Returns:
    A tuple containing:
        - The lint error message if found, None otherwise
        - The line number of the first error, None if no errors
    """
    # skip rst files
    if file_path.endswith('.rst'):
        # failed for the above content
        _ = """===== ========
wave response
nm       ct
===== ========
350.0      0.7
950.0      1.2
===== ========
        """
        return None, None
    linter = DefaultLinter()
    lint_error: list[LintResult] = linter.lint(file_path)
    if not lint_error:
        # Linting successful. No issues found.
        return None, None
    first_error_line = lint_error[0].line if len(lint_error) > 0 else None
    error_text = 'ERRORS:\n' + '\n'.join(
        [f'{file_path}:{err.line}:{err.column}: {err.message}' for err in lint_error]
    )
    return error_text, first_error_line


def _print_window(
    file_path, targeted_line, window, return_str=False, ignore_window=False
):
    global CURRENT_LINE
    file_path = os.path.abspath(file_path)
    if not _check_current_file(file_path):
        return
    with open(file_path) as file:
        content = file.read()

        # Ensure the content ends with a newline character
        if not content.endswith('\n'):
            content += '\n'

        lines = content.splitlines(True)  # Keep all line ending characters
        total_lines = len(lines)

        # cover edge cases
        CURRENT_LINE = _clamp(targeted_line, 1, total_lines)
        half_window = max(1, window // 2)
        if ignore_window:
            # Use CURRENT_LINE as starting line (for e.g. scroll_down)
            start = max(1, CURRENT_LINE)
            end = min(total_lines, CURRENT_LINE + window - 1)
        else:
            # Ensure at least one line above and below the targeted line
            start = max(1, CURRENT_LINE - half_window)
            end = min(total_lines, CURRENT_LINE + half_window - 1)

        output = ''

        # only display this when there's at least one line above
        if start > 1:
            output += f'({start - 1} more lines above)\n'
        else:
            output += f'(File name: {file_path})\n'
        for i in range(start, end + 1):
            width = len(str(end))
            _new_line = f'{i:>{width}}|{lines[i-1]}'
            if not _new_line.endswith('\n'):
                _new_line += '\n'
            output += _new_line
        if end < total_lines:
            output += f'({total_lines - end} more lines below)\n'
        else:
            output += '(this is the end of the file)\n'
        output = output.rstrip()

        if return_str:
            return output
        else:
            print(output)


def _cur_file_header(current_file, total_lines) -> str:
    if not current_file:
        return ''
    return f'[File: {os.path.abspath(current_file)} ({total_lines} lines total)]\n'


def open_file(
    file_path: str, line_number: int | None = 1, context_lines: int | None = WINDOW
) -> None:
    """Opens a file in the editor and optionally positions at a specific line.

    The function displays a limited window of content, centered around the specified line
    number if provided. To view the complete file content, the agent should use scroll_down and scroll_up
    commands iteratively.

    Args:
        file_path: The path to the file to open. Absolute path is recommended.
        line_number: The target line number to center the view on (if possible).
            Defaults to 1.
        context_lines: Maximum number of lines to display in the view window.
            Limited to 100 lines. Defaults to 100.
    """
    global CURRENT_FILE, CURRENT_LINE, WINDOW, LAST_WINDOW
    LAST_WINDOW = WINDOW

    if not check_file_exists(file_path):
        return

    CURRENT_FILE = os.path.abspath(file_path)
    with open(CURRENT_FILE) as file:
        total_lines = max(1, sum(1 for _ in file))

    if not isinstance(line_number, int) or line_number < 1 or line_number > total_lines:
        _output_error(f'Line number must be between 1 and {total_lines}')
        return
    CURRENT_LINE = line_number

    # Override WINDOW with context_lines
    if context_lines is None or context_lines < 1:
        context_lines = WINDOW

    output = _cur_file_header(CURRENT_FILE, total_lines)
    output += _print_window(
        CURRENT_FILE,
        CURRENT_LINE,
        _clamp(context_lines, 1, total_lines),
        return_str=True,
        ignore_window=True,
    )
    if output.strip().endswith('more lines below)'):
        output += f'\n[Use `search_in_file()` or `scroll_down()` to view the next {WINDOW} lines of the file!]'
    print(output)


def goto_line(line_number: int, file_path: str | None = None) -> None:
    """Moves the window to show the specified line number.

    Args:
        line_number: int: The line number to move to.
        file_path: str | None = None: The path to the file to open, preferred absolute path. Defaults to the current file.
    """
    global CURRENT_FILE, CURRENT_LINE, WINDOW
    if file_path:
        CURRENT_FILE = os.path.abspath(file_path)
    _check_current_file()

    with open(str(CURRENT_FILE)) as file:
        total_lines = max(1, sum(1 for _ in file))
    if not isinstance(line_number, int) or line_number < 1 or line_number > total_lines:
        _output_error(f'Line number must be between 1 and {total_lines}.')
        return

    CURRENT_LINE = _clamp(line_number, 1, total_lines)

    output = _cur_file_header(CURRENT_FILE, total_lines)
    output += _print_window(
        CURRENT_FILE, CURRENT_LINE, WINDOW, return_str=True, ignore_window=True
    )
    print(output)


def scroll_down() -> None:
    """Moves the window down by 100 lines.

    Args:
        None
    """
    global CURRENT_FILE, CURRENT_LINE, WINDOW, LAST_WINDOW
    _check_current_file()

    with open(str(CURRENT_FILE)) as file:
        total_lines = max(1, sum(1 for _ in file))
    CURRENT_LINE = _clamp(CURRENT_LINE + LAST_WINDOW, 1, total_lines)
    output = _cur_file_header(CURRENT_FILE, total_lines)
    output += _print_window(
        CURRENT_FILE, CURRENT_LINE, WINDOW, return_str=True, ignore_window=True
    )
    print(output)


def scroll_up() -> None:
    """Moves the window up by 100 lines.

    Args:
        None
    """
    global CURRENT_FILE, CURRENT_LINE, WINDOW, LAST_WINDOW
    _check_current_file()

    with open(str(CURRENT_FILE)) as file:
        total_lines = max(1, sum(1 for _ in file))
    CURRENT_LINE = _clamp(CURRENT_LINE - LAST_WINDOW, 1, total_lines)
    output = _cur_file_header(CURRENT_FILE, total_lines)
    output += _print_window(
        CURRENT_FILE, CURRENT_LINE, WINDOW, return_str=True, ignore_window=True
    )
    print(output)


def create_file(filename: str, content: str = '', overwrite: bool = False) -> None:
    """Creates a new file with the given name and appends the content to it.

    Args:
        filename: str: The name of the file to create.
        content: str = '': The content to write to the file. Defaults to an empty string.
    """
    if os.path.exists(filename) and not overwrite:
        _output_error(f"File '{filename}' already exists.")
    else:
        try:
            # Ensure directory exists
            dirname = os.path.dirname(filename)
            if dirname:
                os.makedirs(dirname, exist_ok=True)

            with open(filename, 'w') as file:
                file.write('')
            if filename == '/tmp/test_task.py':
                with open(filename, 'w') as file:
                    file.write(content)
            elif content:
                insert_content_before_line(filename, 1, content)
                # if the file is empty, delete it
                with open(filename, 'r') as file:
                    if file.read() == '':
                        os.remove(filename)
                        print(f'[File {filename} is not created.]')
            else:
                print(f'[File {filename} created.]')
        except Exception as e:
            print(f'Error creating file {filename}: {e}')
            raise


class LineNumberError(Exception):
    pass


def _append_impl(lines, content):
    """Internal method to handle appending to a file.

    Args:
        lines: list[str]: The lines in the original file.
        content: str: The content to append to the file.

    Returns:
        content: str: The new content of the file.
        n_added_lines: int: The number of lines added to the file.
    """
    content_lines = content.splitlines(keepends=True)
    n_added_lines = len(content_lines)
    if lines and not (len(lines) == 1 and lines[0].strip() == ''):
        # file is not empty
        if not lines[-1].endswith('\n'):
            lines[-1] += '\n'
        new_lines = lines + content_lines
        content = ''.join(new_lines)
    else:
        # file is empty
        content = ''.join(content_lines)

    return content, n_added_lines


def _insert_impl(lines, start, content):
    """Internal method to handle inserting to a file.

    Args:
        lines: list[str]: The lines in the original file.
        start: int: The start line number for inserting.
        content: str: The content to insert to the file.

    Returns:
        content: str: The new content of the file.
        n_added_lines: int: The number of lines added to the file.

    Raises:
        LineNumberError: If the start line number is invalid.
    """
    inserted_lines = [content + '\n' if not content.endswith('\n') else content]
    if len(lines) == 0:
        new_lines = inserted_lines
    elif start is not None:
        if len(lines) == 1 and lines[0].strip() == '':
            # if the file with only 1 line and that line is empty
            lines = []

        if len(lines) == 0:
            new_lines = inserted_lines
        else:
            new_lines = lines[: start - 1] + inserted_lines + lines[start - 1 :]
    else:
        raise LineNumberError(
            f'Invalid line number: {start}. Line numbers must be between 1 and {len(lines)} (inclusive).'
        )

    content = ''.join(new_lines)
    n_added_lines = len(inserted_lines)
    return content, n_added_lines


def _edit_impl(lines, start, end, content):
    """Internal method to handle editing a file.

    REQUIRES (should be checked by caller):
        start <= end
        start and end are between 1 and len(lines) (inclusive)
        content ends with a newline

    Args:
        lines: list[str]: The lines in the original file.
        start: int: The start line number for editing.
        end: int: The end line number for editing.
        content: str: The content to replace the lines with.

    Returns:
        content: str: The new content of the file.
        n_added_lines: int: The number of lines added to the file.
    """
    # for empty file
    if lines == []:
        lines = ['']

    # Handle cases where start or end are None
    if start is None:
        start = 1  # Default to the beginning
    if end is None:
        end = len(lines)  # Default to the end
    # Check arguments
    if start < 1:
        raise LineNumberError(
            f'Start line number should be positive.'
        )
    if end < 1:
        raise LineNumberError(
            f'End line number should be positive.'
        )
    if not (start <= len(lines)):
        raise LineNumberError(
            f'Invalid start line number: {start}. Total number of lines is {len(lines)} only.'
        )
    if not (end <= len(lines)):
        raise LineNumberError(
            f'Invalid end line number: {end}. Total number of lines is {len(lines)} only.'
        )
    if start > end:
        raise LineNumberError(
            f'Invalid line range: {start}-{end}. Start must be less than or equal to end.'
        )

    if content and not content.endswith('\n'):
        content += '\n'
    content_lines = content.splitlines(True)
    n_added_lines = len(content_lines)
    new_lines = lines[: start - 1] + content_lines + lines[end:]
    content = ''.join(new_lines)
    return content, n_added_lines


def is_test_file(file_name: str) -> bool:
    """Check if the file is a test file."""
    if file_name == '/tmp/test_task.py':
        print(
            "[The content in this file is absolutely correct. Also, you can't modify this test file. You must pass this test case. You should correct the codebase instead.]"
        )
        return True
    return False


def _edit_file_impl(
    file_name: str,
    start: int | None = None,
    end: int | None = None,
    content: str = '',
    is_insert: bool = False,
    is_append: bool = False,
) -> str | None:
    """Internal method to handle common logic for edit_/append_file methods.

    Args:
        file_name: str: The name of the file to edit or append to.
        start: int | None = None: The start line number for editing. Ignored if is_append is True.
        end: int | None = None: The end line number for editing. Ignored if is_append is True.
        content: str: The content to replace the lines with or to append.
        is_insert: bool = False: Whether to insert content at the given line number instead of editing.
        is_append: bool = False: Whether to append content to the file instead of editing.
    """
    ret_str = ''
    global CURRENT_FILE, CURRENT_LINE, WINDOW

    ERROR_MSG = f'[Error editing file {file_name}. Please confirm the file is correct.]'
    ERROR_MSG_SUFFIX = 'Your changes have NOT been applied.\n'

    if is_test_file(file_name):
        return None
    if not _is_valid_filename(file_name):
        _output_error('Invalid file name.')
        return None

    if not _is_valid_path(file_name):
        _output_error('Invalid path or file name.')
        return None

    if not _create_paths(file_name):
        _output_error('Could not access or create directories.')
        return None

    if not check_file_exists(file_name):
        return None

    if is_insert and is_append:
        _output_error('Cannot insert and append at the same time.')
        return None

    with open(file_name, 'r') as file:
        old_content = file.read()
    if not start:
        start = len(old_content.splitlines())
    content = indent_lines(content, level=get_indent_level(old_content, line_start=start-1))

    # Use a temporary file to write changes
    content = str(content or '')
    temp_file_path = ''
    first_error_line = None

    try:
        n_added_lines = None

        # lint the original file
        enable_auto_lint = os.getenv('ENABLE_AUTO_LINT', 'true').lower() == 'true'
        if enable_auto_lint:
            # Copy the original file to a temporary file (with the same ext) and lint it
            suffix = os.path.splitext(file_name)[1]
            with tempfile.NamedTemporaryFile(
                suffix=suffix, mode='w', delete=False
            ) as orig_file_clone:
                shutil.copy2(file_name, orig_file_clone.name)
                original_lint_error, _ = _lint_file(orig_file_clone.name)
            os.remove(orig_file_clone.name)

        # Create a temporary file in the same directory as the original file
        original_dir = os.path.dirname(file_name)
        original_ext = os.path.splitext(file_name)[1]
        temp_file_name = f'.temp_{uuid.uuid4().hex}{original_ext}'
        temp_file_path = os.path.join(original_dir, temp_file_name)

        with open(temp_file_path, 'w') as temp_file:
            # Read the original file and check if empty and for a trailing newline
            with open(file_name) as original_file:
                lines = original_file.readlines()

            if is_append:
                content, n_added_lines = _append_impl(lines, content)
            elif is_insert:
                try:
                    content, n_added_lines = _insert_impl(lines, start, content)
                except LineNumberError as e:
                    ret_str += (f'{ERROR_MSG}\n' f'{e}\n' f'{ERROR_MSG_SUFFIX}') + '\n'
                    return ret_str
            else:
                try:
                    content, n_added_lines = _edit_impl(lines, start, end, content)
                except LineNumberError as e:
                    ret_str += (f'{ERROR_MSG}\n' f'{e}\n' f'{ERROR_MSG_SUFFIX}') + '\n'
                    return ret_str

            if not content.endswith('\n'):
                content += '\n'

            # Write the new content to the temporary file
            temp_file.write(content)

        # Replace the original file with the temporary file
        os.replace(temp_file_path, file_name)

        # Handle linting
        # NOTE: we need to get env var inside this function
        # because the env var will be set AFTER the agentskills is imported
        if enable_auto_lint:
            # Generate a random temporary file path
            suffix = os.path.splitext(file_name)[1]
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tfile:
                original_file_backup_path = tfile.name

            with open(original_file_backup_path, 'w') as f:
                f.writelines(lines)

            file_name_abs = os.path.abspath(file_name)
            lint_error, first_error_line = _lint_file(file_name_abs)

            # Select the errors caused by the modification
            def extract_last_part(line):
                parts = line.split(':')
                if len(parts) > 1:
                    return parts[-1].strip()
                return line.strip()

            def subtract_strings(str1, str2) -> str:
                lines1 = str1.splitlines()
                lines2 = str2.splitlines()

                last_parts1 = [extract_last_part(line) for line in lines1]

                remaining_lines = [
                    line
                    for line in lines2
                    if extract_last_part(line) not in last_parts1
                ]

                result = '\n'.join(remaining_lines)
                return result

            if original_lint_error and lint_error:
                lint_error = subtract_strings(original_lint_error, lint_error)
                if lint_error == '':
                    lint_error = None
                    first_error_line = None

            if lint_error is not None:
                if first_error_line is not None:
                    show_line = int(first_error_line)
                elif is_append:
                    # original end-of-file
                    show_line = len(lines)
                # insert OR edit WILL provide meaningful line numbers
                elif start is not None and end is not None:
                    show_line = int((start + end) / 2)
                else:
                    raise ValueError('Invalid state. This should never happen.')

                ret_str += LINTER_ERROR_MSG
                ret_str += lint_error + '\n'

                editor_lines = n_added_lines + 20
                sep = '-' * 49 + '\n'
                ret_str += (
                    f'[This is how your edit would have looked if applied]\n{sep}'
                )
                ret_str += (
                    _print_window(file_name, show_line, editor_lines, return_str=True)
                    + '\n'
                )
                ret_str += f'{sep}\n'

                ret_str += '[This is the original code before your edit]\n'
                ret_str += sep
                ret_str += (
                    _print_window(
                        original_file_backup_path,
                        show_line,
                        editor_lines,
                        return_str=True,
                    )
                    + '\n'
                )
                ret_str += sep
                ret_str += (
                    'Your changes have NOT been applied. Please fix your edit command and try again.\n'
                    'You either need to 1) Specify the correct start/end line arguments or 2) Correct your edit code.\n'
                    'DO NOT re-run the same failed edit command. Running it again will lead to the same error.'
                )

                # recover the original file
                with open(original_file_backup_path) as fin, open(
                    file_name, 'w'
                ) as fout:
                    fout.write(fin.read())

                # Don't forget to remove the temporary file after you're done
                os.unlink(original_file_backup_path)
                return ret_str

    except FileNotFoundError as e:
        ret_str += f'File not found: {e}\n'
    except PermissionError as e:
        ret_str += f'Permission error during file operation: {str(e)}\n'
    except IOError as e:
        ret_str += f'An error occurred while handling the file: {e}\n'
    except ValueError as e:
        ret_str += f'Invalid input: {e}\n'
    except Exception as e:
        # Clean up the temporary file if an error occurs
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        print(f'An unexpected error occurred: {e}')
        raise e

    # Update the file information and print the updated content
    with open(file_name, 'r', encoding='utf-8') as file:
        n_total_lines = max(1, len(file.readlines()))
    if first_error_line is not None and int(first_error_line) > 0:
        CURRENT_LINE = first_error_line
    else:
        if is_append:
            CURRENT_LINE = max(1, len(lines))  # end of original file
        else:
            CURRENT_LINE = start or n_total_lines or 1
    # ret_str += f'[File: {os.path.abspath(file_name)} ({n_total_lines} lines total after edit)]\n'
    CURRENT_FILE = file_name
    ret_str += (
        _print_window(CURRENT_FILE, CURRENT_LINE, SMALL_WINDOW, return_str=True) + '\n'
    )
    # ret_str += MSG_FILE_UPDATED.format(line_number=CURRENT_LINE)
    ret_str += '[File updated successfully]'
    return ret_str


def find_and_replace(file_name: str, find_string: str, replace_string: str) -> None:
    """Find and replace a string in a file."""
    # simple method:
    if find_string == '':
        _output_error('`find_string` must not be empty.')
        return

    if find_string == replace_string:
        _output_error('`find_string` and `replace_string` must be different.')
        return

    if not check_file_exists(file_name):
        return

    if is_test_file(file_name):
        return
    with open(file_name, 'r') as file:
        file_content = file.read()
    occurrences = file_content.count(find_string)
    file_content = file_content.replace(find_string, replace_string)
    if occurrences > 0:
        ret_str = _edit_file_impl(
            file_name,
            start=1,
            end=None,
            content=file_content,
            is_insert=False,
            is_append=False,
        )
        if ret_str == '[File updated successfully]':
            print(
                f'[File updated successfully with {occurrences} occurrences replaced]'
            )
        elif ret_str is not None:
            print(ret_str)
    else:
        print(f'[No matches found for "{find_string}" in {file_name}]')
    return
    # # FIXME: support replacing *all* occurrences

    # # search for `find_string` in the file
    # # if found, replace it with `replace_string`
    # # if not found, perform a fuzzy search to find the closest match and replace it with `replace_string`
    # with open(file_name, 'r') as file:
    #     file_content = file.read()

    # if file_content.count(find_string) > 1:
    #     _output_error(
    #         '`find_string` appears more than once, please include enough lines to make code in `find_string` unique.'
    #     )

    #     return

    # start = file_content.find(find_string)
    # if start != -1:
    #     # Convert start from index to line number
    #     start_line_number = file_content[:start].count('\n') + 1
    #     end_line_number = start_line_number + len(find_string.splitlines()) - 1
    # else:

    #     def _fuzzy_transform(s: str) -> str:
    #         # remove all space except newline
    #         return re.sub(r'[^\S\n]+', '', s)

    #     # perform a fuzzy search (remove all spaces except newlines)
    #     find_string_fuzzy = _fuzzy_transform(find_string)
    #     file_content_fuzzy = _fuzzy_transform(file_content)
    #     # find the closest match
    #     start = file_content_fuzzy.find(find_string_fuzzy)
    #     if start == -1:
    #         print(
    #             f'[No exact match found in {file_name} for\n```\n{find_string}\n```\n]'
    #         )
    #         return
    #     # Convert start from index to line number for fuzzy match
    #     start_line_number = file_content_fuzzy[:start].count('\n') + 1
    #     end_line_number = start_line_number + len(find_string.splitlines()) - 1

    # ret_str = _edit_file_impl(
    #     file_name,
    #     start=start_line_number,
    #     end=end_line_number,
    #     content=replace_string,
    #     is_insert=False,
    # )
    # # lint_error = bool(LINTER_ERROR_MSG in ret_str)
    # # TODO: automatically tries to fix linter error (maybe involve some static analysis tools on the location near the edit to figure out indentation)
    # if ret_str is not None:
    #     print(ret_str)


def find_and_replace_regex(file_name: str, pattern: str, replacement: str) -> None:
    """
    Find and replace a string in a file using regex pattern.
    """
    with open(file_name, 'r+') as f:
        content = f.read()
        occurrences = len(re.findall(pattern, content))
        new_content = re.sub(pattern, replacement, content)
        f.seek(0)
        f.write(new_content)
        f.truncate()
    if occurrences > 0:
        print(f'[File updated successfully with {occurrences} occurrences replaced]')
    else:
        print(f'[No matches found for "{pattern}" in {file_name}]')
    return


def insert_content_before_line(file_name: str, line_number: int, content: str) -> None:
    """Insert content before the given line number in a file. Remeber line number start from 1."""
    line_number = int(line_number)
    ret_str = _edit_file_impl(
        file_name,
        start=line_number,
        end=line_number,
        content=content,
        is_insert=True,
        is_append=False,
    )
    if ret_str is not None:
        print(ret_str)


def insert_content_after_line(file_name: str, line_number: int, content: str) -> None:
    """Insert content after the given line number in a file. Remeber line number start from 1."""
    line_number = int(line_number)
    line_number += 1
    ret_str = _edit_file_impl(
        file_name,
        start=line_number,
        end=line_number,
        content=content,
        is_insert=True,
        is_append=False,
    )
    if ret_str is not None:
        print(ret_str)


def delete_line(file_name: str, line_number: int) -> None:
    """Delete the line at the given line number in a file.
    This will NOT modify the content of the lines before OR after the given line number.
    """
    ret_str = _edit_file_impl(
        file_name,
        start=line_number,
        end=line_number,
        content='',
        is_insert=False,
        is_append=False,
    )
    if ret_str is not None:
        print(ret_str)


def delete_lines(file_name: str, start_line_number: int, end_line_number: int) -> None:
    """Delete the lines from the start line number to the end line number (inclusive) in a file.
    This will NOT modify the content of the lines before OR after the given line number.
    """
    ret_str = _edit_file_impl(
        file_name,
        start=start_line_number,
        end=end_line_number,
        content='',
        is_insert=False,
        is_append=False,
    )
    if ret_str is not None:
        print(ret_str)


def replace_full_file_content(file_name: str, new_content: str) -> None:
    """Replace the full content of the specified file with the given new content."""
    current_content = open(file_name, 'r').read()
    if current_content == new_content:
        print(
            "[The file's content is already identical to the proposed changes. What did you exactly expect to change in the file?]"
        )
        return
    if super_check := os.environ.get(file_name, ''):
        for expr in super_check.split(';'):
            if expr:
                class_name, expr = expr.split('=', 1)
                if (
                    expr not in new_content
                    and expr.replace(' = ', '=') not in new_content
                ):
                    print(
                        f'Error: {expr} in the {class_name} class is missing in the new content, where all parameters are properly handled, preventing the changes from being applied'
                    )
                    return
    ret_str = _edit_file_impl(
        file_name,
        start=1,
        end=None,
        content=new_content,
        is_insert=False,
        is_append=False,
    )
    if ret_str is not None:
        print(ret_str)


def replace_line_content(file_name: str, line_number: int, new_content: str) -> None:
    """Replace the content of the given line number in a file."""
    # check if the old content is the same as the new content
    with open(file_name, 'r') as f:
        old_content = f.read()
    if old_content.splitlines()[line_number - 1] == new_content:
        print(
            f'[The content of line {line_number} is already the same as the proposed changes]'
        )
        return
    ret_str = _edit_file_impl(
        file_name,
        start=line_number,
        end=line_number,
        content=new_content,
        is_insert=False,
        is_append=False,
    )
    if ret_str is not None:
        print(ret_str)


def replace_lines_content(
    file_name: str, start_line_number: int, end_line_number: int, new_content: str
) -> None:
    """Replace the content of the lines from the start line number to the end line number (inclusive) in a file."""
    # check if the old content is the same as the new content
    with open(file_name, 'r') as f:
        old_content = f.read()
    if (
        old_content.splitlines()[start_line_number - 1 : end_line_number]
        == new_content.splitlines()
    ):
        print(
            f'[The content of the lines from {start_line_number} to {end_line_number} is already the same as the proposed changes]'
        )
        return
    ret_str = _edit_file_impl(
        file_name,
        start=start_line_number,
        end=end_line_number,
        content=new_content,
        is_insert=False,
        is_append=False,
    )
    if ret_str is not None:
        print(ret_str)


def append_file(file_name: str, content: str) -> None:
    """Append content to the given file.
    It appends text `content` to the end of the specified file, ideal after a `create_file`!

    Args:
        file_name: str: The name of the file to edit.
        content: str: The content to insert.
    """
    ret_str = _edit_file_impl(
        file_name,
        start=None,
        end=None,
        content=content,
        is_insert=False,
        is_append=True,
    )
    if ret_str is not None:
        print(ret_str)


def search_in_dir(search_term: str, dir_path: str = './') -> None:
    """Searches for search_term in all files in dir. If dir is not provided, searches in the current directory.

    Args:
        search_term: str: The term to search for.
        dir_path (optional): str: The path to the directory to search. Defaults to the current directory.
    """
    if not os.path.isdir(dir_path):
        _output_error(f'Directory {dir_path} not found')
        return
    matches = []
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.startswith('.'):
                continue
            file_path = os.path.join(root, file)
            with open(file_path, 'r', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if search_term in line:
                        matches.append((file_path, line_num, line.strip()))

    if not matches:
        print(f'No matches found for "{search_term}" in {dir_path}')
        return

    num_matches = len(matches)
    num_files = len(set(match[0] for match in matches))

    if num_files > 100:
        print(
            f'More than {num_files} files matched for "{search_term}" in {dir_path}. Please narrow your search.'
        )
        return

    print(f'[Found {num_matches} matches for "{search_term}" in {dir_path}]')
    for file_path, line_num, line in matches:
        print(f'{file_path} (Line {line_num}): {line}')
    print(f'[End of matches for "{search_term}" in {dir_path}]')


def check_file_exists(file_path: str) -> bool:
    if not os.path.isfile(file_path):
        is_extension_missing = '.' not in file_path
        extra_info = (
            ' (Did you forget to include the file extension?)'
            if is_extension_missing
            else ''
        )
        _output_error(f'File {file_path} not found.{extra_info}')
        return False

    return True


def search_in_file(search_term: str, file_path: str | None = None) -> None:
    """Searches for search_term in file. If file is not provided, searches in the current open file.

    Args:
        search_term: The term to search for.
        file_path: The path to the file to search.
    """
    global CURRENT_FILE
    if file_path is None:
        file_path = CURRENT_FILE
    if file_path is None:
        _output_error('No file specified or open. Use the open_file function first.')
        return
    if not check_file_exists(file_path):
        return

    matches = []
    with open(file_path) as file:
        for i, line in enumerate(file, 1):
            if search_term in line:
                matches.append((i, line.strip()))

    if matches:
        print(f'[Found {len(matches)} matches for "{search_term}" in {file_path}]')
        for match in matches:
            print(f'Line {match[0]}: {match[1]}')
        print(f'[End of matches for "{search_term}" in {file_path}]')
    else:
        print(f'[No matches found for "{search_term}" in {file_path}]')


def find_file(file_name: str, dir_path: str = './') -> None:
    """Finds all files with the given name in the specified directory.

    Args:
        file_name: str: The name of the file to find.
        dir_path (optional): str: The path to the directory to search. Defaults to the current directory.
    """
    if not os.path.isdir(dir_path):
        _output_error(f'Directory {dir_path} not found')
        return

    matches = []
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file_name in file:
                matches.append(os.path.join(root, file))

    if matches:
        print(f'[Found {len(matches)} matches for "{file_name}" in {dir_path}]')
        for match in matches:
            print(f'{match}')
    else:
        print(f'[No matches found for "{file_name}" in {dir_path}]')


def kill_port(port: int):
    """Kills the process running on the specified port.

    Args:
        port: int: The port number to kill the process on.
    """
    process = subprocess.run(
        ['lsof', '-t', '-i', f':{port}'], capture_output=True, text=True
    )
    if process.returncode != 0:
        print(f'No process found running on port {port}')
        return
    kill_process = subprocess.run(
        ['kill', '-9', process.stdout.strip()], capture_output=True, text=True
    )
    if kill_process.returncode != 0:
        print(f'Failed to kill process running on port {port}. {kill_process.stderr}')
        return
    print(f'Killed process running on port {port}')


def clean_workspace():
    """Clean the workspace directory and all its contents except for the test files and directories."""
    root_dir = os.getcwd()
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.startswith('test'):
                file_path = os.path.join(dirpath, filename)
                os.remove(file_path)
        for dirname in dirnames:
            if not dirname.startswith('test'):
                dir_path = os.path.join(dirpath, dirname)
                shutil.rmtree(dir_path)


original_import = __import__


# Monkey-patch the import function
def custom_import(name, *args, **kwargs):
    """Custom import function to prevent running Flask app in Jupyter Notebook."""
    if name in [
        'flask',
    ]:
        print(
            "Don't run the Flask app in Jupyter Notebook. Save the code to a Python file and run it in the terminal in the background."
        )
        sys.exit(1)
    prohibited_packages = [
        'astropy',
        'sympy',
        'sklearn',
        'matplotlib',
        'django',
        'xarray',
    ]
    if os.getenv('SWE_BENCH') == '1' and any(p in name for p in prohibited_packages):
        print(
            f"Don't use {name.split('.')[0]} in Jupyter Notebook as file changes will not be reflected. Save the code to a Python file and test it in the terminal"
        )
        sys.exit(1)
    return original_import(name, *args, **kwargs)


def search_symbol(symbol_name, prefix='', suffix=''):
    try:
        symbol_name = prefix + ' ' + symbol_name + suffix
        result = subprocess.run(
            ['git', 'grep', '-n', symbol_name],
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError:
        # print(f"Symbol '{symbol_name}' not found in the repository.")
        # print(e.stderr)
        return False


def search_function(function_name: str, **kwargs):
    """Search for a function in the current directory.

    Args:
        function_name: str: The name of the function to search for.
    """
    # TODO: IMPLEMENT dir_path or file_path
    # workaround for class methods; search_function("DataArray.to_unstacked_dataset")
    function_name = function_name.split('.')[-1]

    if not search_symbol(function_name, 'def', '('):
        print(f"Function '{function_name}' not found in the repository.")


def search_class(class_name: str, **kwargs):
    """Search for a class in the current directory.

    Args:
        class_name: str: The name of the class to search for.
    """
    # TODO: IMPLEMENT dir_path or file_path
    if not search_symbol(class_name, 'class', '[:(]'):
        print(f"Class '{class_name}' not found in the repository.")


def show_class(file_path: str, class_name: str):
    """
    Show the class definition of the given class name in the given file path.

    Args:
        file_path: str: The path to the file containing the class definition.
        class_name: str: The name of the class to search for.
    """
    with open(file_path, 'r') as file:
        code = file.read()
    tree = ast.parse(code)

    lines = code.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            start_line: int = node.lineno - 1  # AST line numbers are 1-based
            end_line: int = node.end_lineno  # type: ignore

            for i in range(start_line, end_line):
                print(f'{i + 1:3}| {lines[i]}')
            return

    print(f"Class '{class_name}' not found in the code.")


def show_function(file_path: str, qualified_function_name: str) -> None:
    """
    Show the definition of the given qualified function name in the given file path.

    Args:
        file_path: str: The path to the file containing the function definition.
        qualified_function_name: str: The qualified name of the function to search for within the file context.
    """
    parts = qualified_function_name.split('.')

    if len(parts) == 1:  # Top-level function (no class)
        class_name = None
        function_name = parts[0]
    else:  # Method inside a class
        class_name = parts[0]
        function_name = parts[1]

    with open(file_path, 'r') as file:
        code = file.read()

    tree = ast.parse(code)

    lines = code.splitlines()

    def print_function_code(node):
        start_line = node.lineno - 1  # AST line numbers are 1-based
        end_line = node.end_lineno  # type: ignore
        for i in range(start_line, end_line):
            print(f'{i + 1:3}| {lines[i]}')
        return

    if class_name:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for sub_node in node.body:
                    if (
                        isinstance(sub_node, ast.FunctionDef)
                        and sub_node.name == function_name
                    ):
                        print_function_code(sub_node)
                        return
                print(f"Function '{function_name}' not found in class '{class_name}'.")
                return
        print(f"Class '{class_name}' not found in the code.")
    else:
        # Top-level function (no class)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                print_function_code(node)
                return
        print(f"Function '{function_name}' not found in the code.")


def show_function_at_line(file_path: str, line_number: int) -> None:
    """
    Show the function definition containing the given line number in the given file path.

    Args:
        file_path: str: The path to the file containing the function definition.
        line_number: int: The line number to search for within the file.
    """
    with open(file_path, 'r') as file:
        code = file.read()

    tree = ast.parse(code)
    lines = code.splitlines()

    def print_function_code(node):
        start_line = node.lineno - 1  # AST line numbers are 1-based
        end_line = node.end_lineno  # type: ignore
        for i in range(start_line, end_line):
            print(f'{i + 1:3}| {lines[i]}')
        return

    # Walk through the AST and find the function containing the line_number
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            start_line = node.lineno
            end_line = getattr(
                node, 'end_lineno', start_line
            )  # To handle multi-line functions
            if start_line <= line_number < end_line:
                print_function_code(node)
                return

    print(f'[No function found for line {line_number} in the file. Using open_file() to view the file.]')
    open_file(file_path, line_number, context_lines=10)

def indent_lines(text, level=1):
    """
    Indents each line of the given text by the specified number of indentation levels.

    Args:
        text (str): The input text to be indented.
        level (int, optional): The number of indentation levels to apply (default is 1).

    Returns:
        str: The indented text.
    """
    current_indent_level = get_indent_level(text)
    level = level - current_indent_level
    if level == 0:
        return text
    elif level > 0: 
        return '\n'.join(['    ' * level + line for line in text.split('\n')])
    else:
        # remove indent
        indent_str = '    ' * abs(level)
        return re.sub(r'^' + indent_str, '', text, flags=re.MULTILINE)


def get_indent_level(text: str, line_start: int | None = None) -> int:
    for line in text.split('\n')[line_start:]:
        if line.strip():
            return line.count('    ')
    return 0

def delete_file(file_name: str):
    try:
        os.remove(file_name)
    except Exception as e:
        print(f"Error deleting file {file_name}: {e}")

__all__ = [
    'search_function',
    'search_class',
    'show_class',
    'show_function',
    'show_function_at_line',
    'show_class_structure',
    'show_file_structure',
    'search_in_dir',
    'search_in_file',
    'open_file',
    'goto_line',
    'scroll_down',
    'scroll_up',
    'create_file',
    'delete_file',
    'find_and_replace',
    'delete_line',
    'delete_lines',
    'insert_content_after_line',
    'insert_content_before_line',
    'append_file',
    'replace_line_content',
    'replace_lines_content',
    # 'replace_full_file_content',
    'find_file',
    'kill_port',
    'clean_workspace',
    'custom_import',
]

try:
    if getpass.getuser() == 'root':
        from .cst_ops import add_param_to_init_in_subclass  # noqa

        __all__.append('add_param_to_init_in_subclass')
except ImportError:
    print('libcst not installed')
    # pip install libcst

if not getpass.getuser() == 'root':
    from openhands.runtime.plugins.agent_skills.file_ops.so import search_in_stack_overflow  # noqa
    __all__.append('search_in_stack_overflow')
    if os.getenv('RESEARCH_AGENT') == '1':
        import openhands.runtime.plugins.agent_skills.file_ops.academic_utils as academic_utils
        __all__.extend(academic_utils.__all__)

if __name__ == '__main__':
    full_content = """
print("hello world")
"""
    from datetime import datetime

    dt = datetime.now()
    file_name = r'../astroid/astroid/nodes/node_classes.py'
    insert_content_after_line(file_name, 4302, "if isinstance(operand, objects.Property):\n    # Handle property inference for unary operations\n    yield operand.infer_unary_op(self.op)\n    continue\n")
    # add_param_to_init_in_subclass(file_name, 'RST', 'header_rows')
    new_content = 'dummy'
    replace_line_content(file_name, 1, new_content)
