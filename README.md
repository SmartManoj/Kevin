Steps:

1) cp config.template.toml config.toml
2) Configure the config.toml file with your own values.
(delete existing containers if volumes value is updated)
3) Run `workspace_setter.py` to set the workspace. (change line 8)
(in ARC tools, only keep the files in src directory)
(set recording_path in workspace\games\game_data_fetcher.py)
4) Run `python3 game_player.py` to play the game.
