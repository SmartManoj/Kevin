import warnings

from grep_ast import TreeContext, filename_to_lang
from grep_ast.parsers import PARSERS

from openhands.linter.base import BaseLinter, LintResult
from openhands.linter.languages.treesitter_compat import get_parser

# tree_sitter is throwing a FutureWarning
warnings.simplefilter('ignore', category=FutureWarning)


def tree_context(fname, code, line_nums):
    context = TreeContext(
        fname,
        code,
        color=False,
        line_number=True,
        child_context=False,
        last_line=False,
        margin=0,
        mark_lois=True,
        loi_pad=3,
        # header_max=30,
        show_top_of_file_parent_scope=False,
    )
    line_nums = set(line_nums)
    context.add_lines_of_interest(line_nums)
    context.add_context()
    output = context.format()
    return output


def traverse_tree(node):
    """Traverses the tree to find errors."""
    errors = []
    if node.type == 'ERROR' or node.is_missing:
        line_no = node.start_point[0] + 1
        col_no = node.start_point[1] + 1
        error_type = 'Missing node' if node.is_missing else 'Syntax error'
        errors.append((line_no, col_no, error_type))

    for child in node.children:
        errors += traverse_tree(child)

    return errors


class TreesitterBasicLinter(BaseLinter):
    @property
    def supported_extensions(self) -> list[str]:
        return list(PARSERS.keys())

    def lint(self, file_path: str) -> list[LintResult]:
        """Use tree-sitter to look for syntax errors, display them with tree context."""
        lang = filename_to_lang(file_path)
        if not lang:
            return []
        try:
            parser = get_parser(lang)
        except Exception as e:
            # print(f'Error getting parser for {lang}: {e}')
            return []
        with open(file_path, 'r') as f:
            code = f.read()
        tree = parser.parse(bytes(code, 'utf-8'))
        errors = traverse_tree(tree.root_node)
        if not errors:
            return []
        return [
            LintResult(
                file=file_path,
                line=int(line),
                column=int(col),
                message=error_details,
            )
            for line, col, error_details in errors
        ]
