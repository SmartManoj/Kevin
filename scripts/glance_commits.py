import subprocess

cmd = 'git log kevin..upstream/main --oneline'

result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

commits = (result.stdout.splitlines())

# no of commits
print('Total commits:', len(commits))

# print the commits
i = 0
blocked_words = ['release', 'fix', 'feat(frontend)']
for commit in commits:
    if (':' not in commit  and not any(word in commit.lower() for word in blocked_words)) or 'feat:' in commit:
        i += 1
        print(i, commit.split(' ', 1)[1])
        print()
