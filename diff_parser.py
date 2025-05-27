def parse_diff(diff_text):
    lines = diff_text.strip().split('\n')
    changes = []
    current_change = {'removed': [], 'added': []}

    for line in lines[2:]:  # Skip the first two lines (diff header)
        if line.startswith('-'):
            current_change['removed'].append(line[1:])
        elif line.startswith('+'):
            current_change['added'].append(line[1:])
        else:
            if current_change['removed'] or current_change['added']:
                changes.append(current_change)
                current_change = {'removed': [], 'added': []}

    if current_change['removed'] or current_change['added']:
        changes.append(current_change)

    return changes


# Example usage
diff_text = """
--- actual output
+++ expected output
@@ -1,7 +1,7 @@
-n a m e
-u n i t
+===== ========
  wave response
    nm       ct
 ===== ========
 350.0      0.7
 950.0      1.2
+===== ========
"""

parsed_changes = parse_diff(diff_text)

for i, change in enumerate(parsed_changes, 1):
    print(f'Change {i}:')
    if change['removed']:
        print('  Removed:')
        for line in change['removed']:
            print(f'    {line}')
    if change['added']:
        print('  Added:')
        for line in change['added']:
            print(f'    {line}')
    print()
