# Use this bot at your own risk. I am not resposible for any bans.

## Features:

- Rune solver
- Support for non kanna classes

## controls:

- F1 -- pause bot (no more commands generated/executed, will finish executing current actions though)

- F2 -- resume bot

## Instructions for Kanna

1. `pip install -r requirements.txt`
2. `python ms_bot.py --create-config <map-config-name>.json`
    
    - Follow steps in cmd (drag bounding box on, press space, select waypoints, press space)
3. configure your keybinds in configs/binds. use kanna_example.json as an example (in configs/binds/kanna_example.json).
4. once you have config, go to your map and run

    `python ms_bot.py --config <map-config-name>.json --hotkeys <hotkey-config-name>.json`

- your configs will be stored in configs/


## Setting up your own class that is not kanna or hayato (requires coding knowledge)

The bot currently implements routines for two classes: kanna and hayato.

To configure routines your own class:

1. Create keybinds for your class
2. Go to `ms_bot.py` and scroll to the bottom. Routines for hayato and kanna have already been implemented. Use these as reference.
    
    Basically, you specify commands to run every x seconds. You can create compound commands with commands.CompoundCommand.

## Known bugs

- window size not exactly the same for different computers
- rune solver sometimes causes bot to freeze indefinitely (idk why)

## Docs (bad)

- Movement and rune positioning logic is in `position.py`.
- HP/MP reading logic is in `status.py`
- Rune solver wrapper class is in `rune_solver.py`. Specific implementations are in the same folder. `color_solver.py` works the best for now.
- misc. logic in `util.py`
- Main loops, setup in `ms_bot.py`

### `ms_bot.py`

- This bot uses a producer consumer pattern to generate and execute commands. `generate_moves` and `generate_attack` are coroutines that generate commands and put them into a queue. Then, `process_commands` consumes these commands from the queue sequentially, to try and make sure commands don't overlap each other.
- There are two command queues: the attack queue and the movement queue.
- The movement queue is for move commands. A move command specifies a waypoint for the player to move to. The player will do its best to pathfind to that waypoint. You can specify the distance (squared) threshold in `generate_moves`. The attack queue is for everything else.

## Donate

- ETH: 0x4bc31A98AAb25269A61A1E2a41E9Bd215525e047
- BTC: 33mXp8C39HVU4eUrKDXdU8gFK2cDaNAEJ7
- DOGE: DGCj5dNXgApUaC8bKyfbsyVsyXjeS9favw