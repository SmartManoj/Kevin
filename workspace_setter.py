# git clone ARC-Tools
import os
import shutil
if 0:
    os.chdir('workspace')
    cmd = 'git clone https://github.com/SmartManoj/Arc-Tools'
    os.system(cmd)

# copy reference solutions
arc_agi_game_path = r'C:\Users\smart\Desktop\GD\ARC-AGI-3-Agents\games'
shutil.copytree(arc_agi_game_path, 'games')
