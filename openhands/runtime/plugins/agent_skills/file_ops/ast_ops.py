import ast


def find_imported_base_class(code, class_name):
    """Find the module from which a base class is imported."""
    tree = ast.parse(code)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == class_name:
                    return node.module or alias.name
    return None


def show_class_structure(file_path: str, class_name: str):
    """Show the methods of a class.
    Args:
        file_path: The path to the file containing the class.
        class_name: The name of the class to show the methods of.
    """
    with open(file_path, 'r') as file:
        code = file.read()
    tree = ast.parse(code)

    # Traverse the AST to find the class with the specified name
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            # Get the parent classes
            parent_classes = [
                base.id for base in node.bases if isinstance(base, ast.Name)
            ]
            parent_str = f"({', '.join(parent_classes)})" if parent_classes else ''
            print(f'class {node.name}{parent_str}:')

            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    # Extract function name and arguments (including 'self')
                    args = [arg.arg for arg in item.args.args]
                    # Format the arguments as a string
                    args_str = ', '.join(args)
                    print(f'    -- {item.name}({args_str})')
            break
    else:
        print(f'Class {class_name} not found in {file_path}')


if __name__ == '__main__':
    # Usage example
    file_name = r'openhands\core\config\sandbox_config.py'
    show_class_structure(file_name, 'SandboxConfig')
