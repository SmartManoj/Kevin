import os


def find_base_class_file(file_path, base_class_module):
    """Find the file path for a given base class module."""
    # Move up the directory tree to find the base package root dynamically
    length_of_module_name = len(base_class_module.split('.'))
    for i in range(length_of_module_name):
        dir_name = os.path.dirname(file_path)
        if dir_name == '':
            dir_name = os.getcwd()
        possible_paths = [
            os.path.join(dir_name, base_class_module.replace('.', '/') + '.py'),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        file_path = dir_name
    return None
