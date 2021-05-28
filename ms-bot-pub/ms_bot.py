import PIL
import numpy as np
import cv2
from PIL import ImageGrab
import mouse
import keyboard
import asyncio
import time
from mss import mss
import util
import commands
import position
import sys
import status
import math
import screenshot
import rune_solvers.rune_solver as rs

print_pos = False

player_template = cv2.imread('player.png')

template_matching_thresh = 5e6
command_queue = asyncio.PriorityQueue()
move_queue = asyncio.PriorityQueue()
attack_queue = asyncio.PriorityQueue()
waypoints = None
program_running = True
rune_position = None
solving_rune_in_progress = False

current_move = None
hp = 1
mp = 1

async def update_screen(target_fps=5):
    
    while True:
        
        try:
            screenshot.update_screen()
        except Exception as e:
            util.err(f'(fatal) exception in update screen: {e}')

        await asyncio.sleep(1.0 / target_fps)

async def update_position(show_cv=True): 

    global current_move, rune_position

    while True:

        img = await position.update_minimap()
        pl_pos, pl_top_left, pl_bottom_right = await position.update_position()
        rune_pos, rune_top_left, rune_bottom_right, rune_val = await position.get_rune_position()

        if print_pos:
            print(pl_pos)

        if show_cv:

            # next waypoint
            if current_move is not None:
                cv2.circle(img, (current_move.x, current_move.y), 4, (0, 0, 255), -1)

            # display player
            if pl_pos is not None:
                cv2.rectangle(img, pl_top_left, pl_bottom_right, (255, 0, 0), 2)

            # display rune
            if rune_pos is not None:
                cv2.rectangle(img, rune_top_left, rune_bottom_right, (0, 0, 255), 2)
                rune_position = rune_pos

            img = cv2.resize(img, (img.shape[1] * 2, img.shape[0] * 2), fx=2, fy=2)

            if pl_pos is not None:
                cv2.putText(img, f'({pl_pos[0]}, {pl_pos[1]})', (5, 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 255, 0), 1, cv2.LINE_AA)
            else:
                cv2.putText(img, 'player not found', (5, 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 255, 0), 1, cv2.LINE_AA)

            cv2.putText(img, f'rune: {rune_val}', (5, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 255, 0), 1, cv2.LINE_AA)
            
            cv2.imshow('screen', img)

            if (cv2.waitKey(1) & 0xFF) == ord('q'):
                cv2.destroyAllWindows()
                sys.exit(1)
                break

        # target fps
        await asyncio.sleep(1.0 / 5)

async def update_status(update_hp=True, update_mp=False):

    global hp, mp

    exception_count = 0

    while True:

        try:
            hp, mp, img = await status.update_stats(update_hp, update_mp)

            img = cv2.resize(img, (img.shape[1] * 2, img.shape[0] * 2), fx=2, fy=2)
            cv2.putText(img, f'hp={util.truncate(hp, 2)} mp={util.truncate(mp, 2)}', (5, 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 255, 0), 1, cv2.LINE_AA)

            cv2.imshow('hp/mp', img)

            if (cv2.waitKey(1) & 0xFF) == ord('q'):
                cv2.destroyAllWindows()
                sys.exit(1)
        except Exception as e:
            util.err(f'Something went wrong in update_status: {e}')
            exception_count += 1

            # HUGE band aid solution to mss crashing
            if exception_count >= 5:
                util.warning('Too many errors with update_status, falling back to timed potion drinking')
                while exception_count > 0:
                    mp = 0
                    await asyncio.sleep(5)
                    mp = 1
                    await asyncio.sleep(60)
                    exception_count -= 1

        await asyncio.sleep(1.0 / 1)

def should_run_normally():
    global program_running, solving_rune_in_progress
    return program_running and not solving_rune_in_progress

async def solve_rune(move_to_method='tp'):

    global rune_position, solving_rune_in_progress

    while True:
        if rune_position is not None and program_running:

            print('Rune detected, beginning solve in 2 seconds')
            solving_rune_in_progress = True

            await asyncio.sleep(2)

            arrows = None

            iters = 0

            while arrows is None and iters < 5:

                if rune_position is None:
                    break
                
                try:
                    await asyncio.wait_for(position.move_to(rune_position, 10, method=move_to_method), timeout=10)
                except asyncio.TimeoutError:
                    print('Move to rune timed out')
                except Exception as e:
                    util.warning(f'rune solver: {str(e)}')

                print(f'Rune solver running, iteration {iters}')
                await util.hold_key('space', press_time=.1, randomize=False)
                
                time.sleep(2)

                try:
                    arrows = rs.solve_rune(method='color')
                
                    if arrows is None or len(arrows) != 4:
                        print('color solve failed, falling back to contour solve')
                        arrows = rs.solve_rune(method='contour')

                except Exception as e:
                    util.warning(f'Rune solver exception: {e}')
                    iters += 1
                    continue

                time.sleep(1)

                iters += 1

            print(f'Rune solver: {arrows}')

            if arrows is not None:
                for arrow in arrows:
                    await util.hold_key(arrow, press_time=.1, randomize=False)
                    time.sleep(.5)

            # done
            rune_position = None
            solving_rune_in_progress = False

            # couldn't solve it, maybe i have a rune cooldown
            # try again in 90 seconds
            if arrows is None:
                await asyncio.sleep(90)
        else:
            await asyncio.sleep(5)

async def process_commands(queue, cooldown=3):

    global current_move

    while True:

        if should_run_normally():
            (priority, next_command) = await queue.get()
            print(f'Executing {str(next_command)}')
            if isinstance(next_command, commands.MoveCommand):
                current_move = next_command

            if next_command is not None:
                await next_command.execute()
        else:
            await asyncio.sleep(cooldown)

async def generate_attack(attack, cooldown, press_time=.25, wait_duration=.1, priority=5, variance=.1):

    while True:
        if should_run_normally():

            if isinstance(attack, str):
                attack_command = commands.AttackCommand(attack, press_time=press_time, wait_duration=wait_duration)
            elif isinstance(attack, commands.Command):
                attack_command = attack.clone()
            else:
                util.warning(f'generate_attack: dunno what {str(attack)} is')
                continue

            await queue_attack(attack_command, priority)

            # wait for the attack to execute
            try:
                await asyncio.wait_for(attack_command.end.wait(), timeout=15)
            except asyncio.TimeoutError:
                print(str(attack_command), 'timed out')
            except Exception as e:
                util.err(f'{str(attack_command)} broke: {str(e)}')

            r = np.random.uniform(0, cooldown * variance)
            await asyncio.sleep(cooldown + r)
        else:
            await asyncio.sleep(3)

async def generate_auto_attack(lower=1, upper=5, cooldown=.3):
    while True:
        if should_run_normally():
            if attack_queue.empty():
                await queue_attack(commands.AttackCommand('auto', np.random.uniform(lower, upper)))
            await asyncio.sleep(cooldown)
        else:
            await asyncio.sleep(3)

async def generate_buffs():
    while True:
        if should_run_normally():
            wait_for = commands.WaitCommand(5)
            await queue_move(wait_for, 0)

            await queue_attack(commands.AttackCommand('haku', press_time=.1, wait_for=wait_for.start), 0)
            await queue_attack(commands.WaitCommand(.5), 0)
            await queue_attack(commands.AttackCommand('buff', press_time=.2, wait_for=wait_for.start), 0) 
            await queue_attack(commands.WaitCommand(1), 0)
            
            await asyncio.sleep(150)
        else:
            await asyncio.sleep(3)

async def generate_domain():

    # for domain, we put it at the waypoint 
    y_mean = 0
    for wp in waypoints:
        y_mean += wp[1]
    y_mean /= len(waypoints)
    
    lower_wp = [ wp for wp in waypoints if wp[1] >= y_mean]
    lower_wp.sort()
    (x, y) = lower_wp[int(len(lower_wp) // 2)]

    while True:
        if should_run_normally():
            move_command = commands.MoveCommand(x, y, 'tp')
            wait_command = commands.WaitCommand(3)
            await queue_move(move_command, 1)
            await queue_move(wait_command, 1)

            try:
                print('MOVING TO DOMAIN SPOT')
                await asyncio.wait_for(move_command.end.wait(), timeout=20)
                print('ACTIVATING DOMAIN')
                await queue_attack(commands.AttackCommand('domain', wait_for=wait_command.start), 1)
            except asyncio.TimeoutError:
                print(str(move_command), 'timed out (move tso domain target)')

            await asyncio.sleep(220)

async def generate_pet_food(cooldown):
    while True:
        if should_run_normally():
            cmds = [commands.AttackCommand('pet food', wait_duration=1) for i in range(3)]
            cmd = commands.CompoundCommand(cmds)

            await queue_attack(cmd)
            await asyncio.sleep(cooldown)
        else:
            await asyncio.sleep(3)

async def generate_moves(method='tp', cooldown=1, threshold=20):

    if waypoints is None:
        raise RuntimeError('Waypoints is none!!!')
        exit()

    i = 0
    while True:
        if should_run_normally():
            idx = i % len(waypoints)

            wp = waypoints[idx]
            move_command = commands.MoveCommand(wp[0], wp[1], method=method, threshold=threshold)
            await queue_move(move_command)
            
            try:
                await asyncio.wait_for(move_command.end.wait(), timeout=10)
            except asyncio.TimeoutError:
                print(str(move_command), 'timed out')
            i+=1
            await asyncio.sleep(cooldown)
        else:
            await asyncio.sleep(3)

async def drink_pots(hp_thresh=.5, mp_thresh=.3):

    while True:

        try:
            if hp is not None:
                if hp < hp_thresh:
                    await queue_attack(commands.KeyCommand(commands.hotkeys['hp pot']), 1)
            
            if mp is not None:
                if mp < mp_thresh:
                    await queue_attack(commands.KeyCommand(commands.hotkeys['mp pot']), 1)
            
            await asyncio.sleep(1)
        except Exception as e:
            util.warning(f'Drink pots exception (did you bind hp/mp pots?): {e}')

async def queue_command(command, priority=10):
    await command_queue.put((priority, command))

async def queue_attack(attack, priority=10):
    await attack_queue.put((priority, attack))

async def queue_move(move, priority=10):
    await move_queue.put((priority, move))

def stop_bot(_):
    global program_running

    print('Bot stopped, no new commands executed')
    program_running = False

def resume_bot(_):
    global program_running

    print('Bot resumed')
    program_running = True

if __name__ == '__main__':

    loop = asyncio.get_event_loop()
    args = sys.argv

    keyboard.on_press_key('f1', stop_bot)
    keyboard.on_press_key('f2', resume_bot)

    if '--create-config' in args:
        screenshot.setup()
        config_filename = args[args.index('--create-config') + 1]
        position.create_config(config_filename)

    elif '--config' in args:
        config_filename = args[args.index('--config') + 1]
        waypoints = position.load_config(config_filename)

        if '--hotkeys' in args:
            hotkey_config_filename = args[args.index('--hotkeys') + 1]
            commands.load_hotkey_config(hotkey_config_filename)
        else:
            util.warning('No keybinds provided. Using default ones found in commands.py')

        position.setup()
        status.setup()
        screenshot.setup()

        print('bot starting in 2 seconds, make sure ms is focused!')
        time.sleep(2)

        loop.create_task(update_position())
        

        if '--hayato' in args:

            loop.create_task(solve_rune('fj'))
            loop.create_task(update_status(True, True))
            loop.create_task(drink_pots())

            loop.create_task(process_commands(move_queue, cooldown=0))
            loop.create_task(process_commands(attack_queue, cooldown=0))

            loop.create_task(generate_moves(method='fj', cooldown=0, threshold=90))



            loop.create_task(generate_attack('instant slice', 10, variance=2))

            # loop.create_task(generate_attack('god of blades', 125))

            loop.create_task(generate_attack('zankou', 91, priority=1, wait_duration=4))
            loop.create_task(generate_attack('hitokiri', 90 / 2, priority=2, wait_duration=2))
            loop.create_task(generate_attack('falcons honor', 8, variance=3, priority=2, wait_duration=1.5))

            jmp = commands.KeyCommand('alt', press_time=.1)
            atk = commands.AttackCommand('phantom blade', press_time=.1, wait_duration=1)
            ccmd = commands.CompoundCommand([jmp, atk])
            loop.create_task(generate_attack(ccmd, 5, variance=2, priority=1))
            # loop.create_task(generate_attack('phantom blade', 1, variance=2, priority=0, wait_duration=1))

            # lmao this dc's you
            # loop.create_task(generate_attack('summer rain', 120, priority=3, wait_duration=4))

            # buffs
            loop.create_task(generate_attack('dse', 180, priority=1, wait_duration=1.5))
            loop.create_task(generate_attack('princess vow', 120, priority=1, wait_duration=1.5))
            loop.create_task(generate_attack('god of blades buff', 90, priority=1, wait_duration=1.5))
            loop.create_task(generate_attack('buff', 200, priority=1, wait_duration=1.5))
            loop.create_task(generate_attack('weapon aura', 180, priority=1, wait_duration=1.5))
            loop.create_task(generate_attack('hs', 180, priority=1, wait_duration=1.5))
            loop.create_task(generate_attack('sengoku summon', 120, variance=10, priority=2))
            
            loop.create_task(generate_auto_attack(.1, 1, 5))

            loop.create_task(generate_pet_food(150))

        elif '--debug' not in args:
            # loop.create_task(update_status(True, False))
            loop.create_task(process_commands(move_queue, cooldown=1))
            loop.create_task(process_commands(attack_queue, cooldown=2))
            loop.create_task(drink_pots())

            loop.create_task(generate_moves(method='tp', cooldown=0))
            loop.create_task(generate_buffs())

            # # set attacks
            loop.create_task(generate_auto_attack(.2, 2, 2))

            loop.create_task(generate_attack('kishin', 60 / 2, wait_duration=.2, priority=0))
            # loop.create_task(generate_attack('orochi', 90, wait_duration=1, priority=2))
            loop.create_task(generate_attack('foot', 120, wait_duration=3, priority=2))
            loop.create_task(generate_attack('tengu', 10, wait_duration=.1, priority=2))
            loop.create_task(generate_attack('fox', 120, wait_duration=4, priority=2))
            
            loop.create_task(generate_attack('yaksha', 10, variance=5, wait_duration=1, priority=3))
            loop.create_task(generate_attack('lord', 180, press_time=.1, priority=2))
            loop.create_task(generate_attack('yuki', 90, priority=2))
            loop.create_task(generate_attack('exorcist', 5, priority=3))
            loop.create_task(generate_attack('hs', 180, priority=1))

            loop.create_task(generate_attack('boost', 30, variance=120, priority=3))
            loop.create_task(generate_attack('princess vow', 120, variance=120, priority=1))

            loop.create_task(generate_attack('sengoku summon', 120, variance=10, priority=2))

            loop.create_task(generate_domain())

            loop.create_task(solve_rune())

            loop.create_task(generate_pet_food(150))


        loop.run_forever()
