import asyncio
import util
import numpy as np
import position
import json

###############
# KANNA BINDS #
###############
hotkeys = {
    'tp': 'x',
    'orochi': 'w',
    'yaksha': 's',
    'foot': 'r',
    'fox': 't',
    'tengu': 'v',
    'haku': 'page up',
    'buff': 'del',
    'auto': 'ctrl',
    'cards': 'shift',
    'domain': '4',
    'yuki': '3',
    'lord': 'g',
    'kishin': 'f',
    'hs': 'page down',
    'boost': 'a',
    'princess vow': '5',
    'exorcist': 'z',
    'pet food': '6',
    'sengoku summon': '2',  
}

PATH_TO_CONFIGS = 'configs/binds/'

def load_hotkey_config(filename):
    global hotkeys
    with open(f'{PATH_TO_CONFIGS}{filename}', 'r') as f:
        hotkeys = json.load(f)
    print(hotkeys)

class Command():
    def __init__(self):
        self.start = asyncio.Event()
        self.end = asyncio.Event()

    def __lt__(self, other):
        return 0

    async def execute(self):
        try:
            self.start.set()
            await self.execute_internal()
            self.end.set()
        except Exception as e:
            util.err(f'ERR: Exception in {str(self)}: {str(e)}')

class MoveCommand(Command):
    def __init__(self, x, y, method, threshold=20):
        super().__init__()
        self.x = x
        self.y = y
        self.method = method
        self.threshold = threshold

    async def execute_internal(self):
        # MAYBE BROKEN
        await position.move_to((self.x, self.y), method=self.method, thresh=self.threshold)

    def __str__(self):
        return f'MoveCommand({self.x}, {self.y})'

class AttackCommand(Command):
    def __init__(self, move_name, press_time=.1, wait_duration=.1, wait_for=None):
        super().__init__()
        self.move_name = move_name
        self.press_time = press_time
        self.wait_duration = wait_duration
        self.event = asyncio.Event()
        self.wait_for = wait_for

    def clone(self):
        return AttackCommand(self.move_name, self.press_time, self.wait_duration, self.wait_for)
    
    async def execute_internal(self):

        if self.wait_for is not None:
            await self.wait_for.wait()

        pos = position.get_player_pos() # await get_pos()
        w, h = position.get_bounds()

        rel_x_pos = np.clip(pos[0] / w, 0, 1)
            
        if util.random_bool(rel_x_pos):
            await util.hold_key('left')
        else:
            await util.hold_key('right')

        await util.hold_key(hotkeys[self.move_name], press_time=self.press_time)
        await asyncio.sleep(self.wait_duration)
        self.event.set()
    
    def __str__(self, verbose=True):
        if verbose:
            return f'AttackCommand({self.move_name}, press_time={self.press_time}, wait_duration={self.wait_duration}, wait_for={self.wait_for is not None})'
        else:
            return f'AttackCommand({self.move_name})'

# press a key on the keyboard
class KeyCommand(Command):
    def __init__(self, key, press_time=.3, randomize=True, variance_pct=.2):
        super().__init__()
        self.key = key
        self.press_time = press_time
        self.randomize = randomize
        self.variance_pct = variance_pct

    def clone(self):
        return KeyCommand(self.key, self.press_time)
    
    async def execute_internal(self):
        await util.hold_key(self.key, self.press_time, self.randomize, self.variance_pct)

    def __str__(self):
        return f'KeyCommand({self.key}, {self.press_time})'

class WaitCommand(Command):
    def __init__(self, duration):
        super().__init__()
        self.duration = duration


    def clone(self):
        return WaitCommand(self.duration)

    async def execute_internal(self):
        await asyncio.sleep(self.duration)

    def __str__(self):
        return f'WaitCommand({self.duration})' 

class CompoundCommand(Command):
    def __init__(self, cmds):
        super().__init__()
        self.cmds = cmds

    def clone(self):
        cmds = [cmd.clone() for cmd in self.cmds]
        return CompoundCommand(cmds)
    
    async def execute_internal(self):
        for cmd in self.cmds:
            print('executing', str(cmd))
            await cmd.execute()

    def __str__(self):
        return f'CompoundCommand({[str(c) for c in self.cmds]})'

class DebugCommand(Command):
    def __init__(self, msg):
        super().__init__()
        self.msg = msg

    def clone(self):
        return DebugCommand(self.msg)
    
    async def execute_internal(self):
        print(self.msg)

    def __str__(self):
        return f'DebugCommand({self.msg})'