import ast
import os

import libcst as cst
from libcst import FunctionDef, Name, Param, Parameters

from openhands.runtime.plugins.agent_skills.file_ops.file_utils import (
    find_base_class_file,
)


def has_init_method(class_node):
    return any(
        isinstance(elem, FunctionDef) and elem.name.value == '__init__'
        for elem in class_node.body.body
    )


# Converting the AST 'arguments' object to a readable format
def format_signature(args: ast.arguments | None) -> list[str]:
    if args is None:
        return []
    return [arg.arg for arg in args.args]


class CheckParamAssignedInInit(cst.CSTVisitor):
    def __init__(self, class_name: str, param_name: str):
        self.class_name = class_name
        self.param_name = param_name
        self.in_target_class = False
        self.in_init_method = False
        self.param_assigned = False

    def visit_ClassDef(self, node: cst.ClassDef):
        # Check if we're inside the target class (RidgeClassifier)
        if node.name.value == self.class_name:
            self.in_target_class = True

    def leave_ClassDef(self, node: cst.ClassDef):
        # Exit the class scope
        if node.name.value == self.class_name:
            self.in_target_class = False

    def visit_FunctionDef(self, node: cst.FunctionDef):
        # Check if we're inside the __init__ method of the target class
        if self.in_target_class and node.name.value == '__init__':
            self.in_init_method = True

    def leave_FunctionDef(self, node: cst.FunctionDef):
        # Exit the __init__ method scope
        if self.in_init_method:
            self.in_init_method = False

    def visit_Assign(self, node: cst.Assign):
        # Check if we are inside the target class's __init__ method and if self.param_name is assigned
        if self.in_target_class and self.in_init_method:
            if isinstance(node.targets[0].target, cst.Attribute) and isinstance(
                node.targets[0].target.value, cst.Name
            ):
                if (
                    node.targets[0].target.value.value == 'self'
                    and node.targets[0].target.attr.value == self.param_name
                ):
                    self.param_assigned = True


class BaseClassInitFinder(ast.NodeVisitor):
    def __init__(self):
        self.init_signature = None

    def visit_FunctionDef(self, node):
        # Find the __init__ method and get its signature
        if node.name == '__init__':
            self.init_signature = node.args
        return node


def find_imported_base_class(code, class_name):
    tree = ast.parse(code)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == class_name:
                    return node.module or alias.name
    return None


def read_file(file_path):
    with open(file_path, 'r') as f:
        return f.read()


def get_class_init_signature_from_code(code, class_name, param_name=None):
    tree = ast.parse(code)
    cst_tree = cst.parse_module(code)
    finder = BaseClassInitFinder()
    visitor = CheckParamAssignedInInit(class_name, param_name)
    # Traverse to find the class definition
    cst_tree.visit(visitor)
    if visitor.param_assigned:
        os.environ['PARAM_ASSIGNED_IN_INIT'] = '1'
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            finder.visit(node)
            break

    return finder.init_signature


def process_file_for_base_class_init(file_path, base_class_name, param_name=None):
    code = read_file(file_path)
    return get_class_init_signature_from_code(code, base_class_name, param_name)


# Example usage
def get_base_class_init_signature(file_path, base_class_name):
    current_code = read_file(file_path)
    base_class_module = find_imported_base_class(
        current_code, base_class_name.split('.')[0]
    )

    if base_class_module:
        base_class_file = find_base_class_file(file_path, base_class_module)
        if base_class_file:
            base_init_signature = process_file_for_base_class_init(
                base_class_file, base_class_name
            )
            if base_init_signature:
                formatted_signature = format_signature(base_init_signature)
                return formatted_signature
        else:
            print('Base class file not found.')
    else:
        base_init_signature = process_file_for_base_class_init(
            file_path, base_class_name
        )
        if base_init_signature:
            return format_signature(base_init_signature)
    return []


class BaseClassFinder(ast.NodeVisitor):
    def __init__(self):
        self.base_class_names = []

    def visit_ClassDef(self, node):
        # Check if the class has a base class
        for base in node.bases:
            if isinstance(base, ast.Attribute):
                self.base_class_names.append(base.value.id + '.' + base.attr)  # type: ignore
            else:
                self.base_class_names.append(base.id)
        return node


def get_base_class_names(file_path, class_name):
    code = read_file(file_path)
    tree = ast.parse(code)
    finder = BaseClassFinder()
    base_class_names = []
    # Traverse to find the class definition
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            finder.visit(node)
            base_class_names.extend(finder.base_class_names)

    return base_class_names


class AddInitIfNotExistsTransformer(cst.CSTTransformer):
    def __init__(self, class_name):
        self.class_name = class_name
        self.inside_target_class = False

    def leave_ClassDef(self, original_node, updated_node):
        if not self.inside_target_class:  # type: ignore
            return updated_node
        # Check if the class already has an __init__ method
        if has_init_method(updated_node):
            return updated_node

        # Define the parameters for the __init__ function
        params = Parameters(params=[Param(name=Name('self'))])

        # Define the body of the __init__ function
        body = cst.IndentedBlock(body=[])

        # Create the __init__ method
        init_method = FunctionDef(name=Name('__init__'), params=params, body=body)

        # Add the __init__ method to the class body
        new_body = list(updated_node.body.body) + [init_method]
        self.inside_target_class = False
        # Return the class with the added __init__ method
        return updated_node.with_changes(body=cst.IndentedBlock(body=new_body))

    def visit_ClassDef(self, node: cst.ClassDef):
        if node.name.value == self.class_name:
            self.inside_target_class = True


class InitMethodModifier(cst.CSTTransformer):
    def __init__(self, file_path, class_name, param_name, default_value=None):
        self.file_path = file_path
        self.class_name = class_name
        self.param_name = param_name
        self.default_value = default_value
        self.inside_target_class = False

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        # Modify only if we are inside the target class's __init__ method
        if self.inside_target_class and original_node.name.value == '__init__':
            # Add the new parameter to the __init__ method
            if self.default_value:
                new_param = cst.Param(
                    cst.Name(self.param_name), default=cst.Name(self.default_value)
                )
            else:
                new_param = cst.Param(cst.Name(self.param_name))

            new_params = updated_node.params.with_changes(
                params=[*updated_node.params.params, new_param]
            )
            if os.environ['PARAM_ASSIGNED_IN_INIT'] == '1':
                # Add the assignment self.param_name = param_name
                new_assignment = cst.SimpleStatementLine(
                    body=[
                        cst.Assign(
                            targets=[
                                cst.AssignTarget(
                                    cst.Attribute(
                                        cst.Name('self'), cst.Name(self.param_name)
                                    )
                                )
                            ],
                            value=cst.Name(self.param_name),
                        )
                    ]
                )

                # Insert the assignment at the end of the body
                # ignore pass
                is_pass = all(
                    isinstance(elem.body[0], cst.Pass)
                    for elem in updated_node.body.body
                )

                if not is_pass:
                    new_body = list(updated_node.body.body) + [new_assignment]
                else:
                    new_body = [new_assignment]

                # Update the __init__ function with the new parameter and assignment
                return updated_node.with_changes(
                    params=new_params, body=cst.IndentedBlock(body=new_body)
                )
            else:
                return updated_node.with_changes(params=new_params)

        return updated_node

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef):
        # Exit the target class after processing
        self.inside_target_class = False
        return updated_node

    def visit_ClassDef(self, node: cst.ClassDef):
        # Enter the target class
        if node.name.value == self.class_name:
            self.inside_target_class = True

    def leave_Expr(self, original_node: cst.Expr, updated_node: cst.Expr) -> cst.Expr:
        base_class_names = get_base_class_names(self.file_path, self.class_name)
        # print(f"Base class names: {base_class_names}")
        for base_class_name in base_class_names:
            base_class_init_signature = get_base_class_init_signature(
                self.file_path, base_class_name
            )
            self.relevant_base_param = base_class_name and self.param_name in (
                base_class_init_signature
            )
            if self.relevant_base_param:
                break
        if not self.relevant_base_param:
            print(
                f"Parameter '{self.param_name}' not found in base class {base_class_name} __init__ signature ({', '.join(base_class_init_signature)})"
            )
            return updated_node
        # Modify the super().__init__ call to include the new parameter
        if self.inside_target_class and isinstance(original_node.value, cst.Call):
            if isinstance(original_node.value.func, cst.Attribute):
                if original_node.value.func.attr.value == '__init__':
                    # Check if existing arguments contain keyword arguments
                    has_keyword_args = any(
                        isinstance(arg, cst.Arg) and arg.keyword
                        for arg in original_node.value.args
                    )

                    if has_keyword_args:
                        # Add the new parameter as a keyword argument to avoid positional after keyword error
                        new_arg = cst.Arg(
                            keyword=cst.Name(self.param_name),
                            value=cst.Name(self.param_name),
                        )
                    else:
                        # Add the new parameter as a positional argument
                        new_arg = cst.Arg(value=cst.Name(self.param_name))

                    new_args = [*original_node.value.args, new_arg]
                    new_call = updated_node.value.with_changes(args=new_args)
                    return updated_node.with_changes(value=new_call)

        return updated_node


def add_param_to_init_in_subclass(
    file_path, class_name, param_name, default_value=None
):
    """
    This function adds a new parameter to the __init__ method of a specified sub class in a given file and adds it to the super().__init__ call automatically by checking if the parameter is present in the base class __init__ method using AST.

    Args:
        file_path (str): The path to the file containing the class.
        class_name (str): The name of the subclass to modify.
        param_name (str): The name of the new parameter to add to the __init__ method.

    """
    os.environ['PARAM_ASSIGNED_IN_INIT'] = '0'
    code = read_file(file_path)
    # Parse the code into a CST tree
    # Apply the transformer to add the __init__ method if it doesn't exist
    module = cst.parse_module(code)
    transformer = AddInitIfNotExistsTransformer(class_name)
    new_module = module.visit(transformer)
    code = new_module.code

    tree = cst.parse_module(code)

    if param_name in format_signature(
        get_class_init_signature_from_code(code, class_name, param_name)
    ):
        print(
            f"Parameter '{param_name}' already exists in {class_name} class __init__ method."
        )
        return
    # Create the transformer to modify the __init__ method
    transformer = InitMethodModifier(file_path, class_name, param_name, default_value)

    # Apply the transformation
    modified_tree = tree.visit(transformer)
    new_code = modified_tree.code
    if new_code != code:
        # exit()
        with open(file_path, 'w') as f:
            f.write(modified_tree.code)
        extra = ''
        if os.environ['PARAM_ASSIGNED_IN_INIT'] == '1':
            extra = ' and added self assignment'

        if transformer.relevant_base_param:
            base_class_names = get_base_class_names(file_path, class_name)
            base_class_init_signature = ''
            for base_class_name in base_class_names:
                _ = get_base_class_init_signature(file_path, base_class_name)
                if _:
                    base_class_init_signature += f"Base class {base_class_name} __init__ signature: {', '.join(_)}\n"
            print(
                f"[Modified {class_name} class to include '{param_name}' in __init__, super().__init__{extra}.]\n{base_class_init_signature}"
            )
            # TODO get the line number of the super().__init__ call
            os.environ[file_path] = (
                os.environ.get(file_path, '')
                + f';{class_name}=super().__init__(delimiter_pad=None, bookend=False, header_rows = header_rows)'
            )
        else:
            print(
                f"[Modified {class_name} class to include '{param_name}' in __init__, super().__init__{extra}]"
            )
    os.environ['PARAM_ASSIGNED_IN_INIT'] = '0'


if __name__ == '__main__':
    add_param_to_init_in_subclass(
        r'C:\Users\smart\Desktop\GD\scikit-learn\sklearn\ensemble\iforest.py',
        'IsolationForest',
        'warm_start',
        'False',
    )
