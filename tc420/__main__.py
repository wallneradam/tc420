"""
TC420 CLI

This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import sys
import os
from random import random, randint
from datetime import datetime
from typing import Callable, Tuple

import click
import usb.core
from .tc420 import TC420, NoDeviceFoundError


class CtxObj:
    """ This is the class used in context object to pass through all commands """
    dev: TC420 = None
    bank = -1
    mode_stop_neded = False


class Context(click.Context):
    """ This is just an interface for intellisense """
    obj: CtxObj


def check_result(res):
    """ Utility function to check if lib function result is good. Exit with error if not. """
    if res:
        print("OK.")
    else:
        print("ERROR!", file=sys.stderr)
        sys.exit(2)


def multiline_devider_replacer(f: Callable):
    """ Decorator to modify command line deviders in doc string according to OS """
    divider = '\\' if os.name != 'nt' else '^'
    f.__doc__ = f.__doc__.replace('{MULTILINE_DIVIDER}', divider)
    return f


@click.group(chain=True)
@click.pass_context
@multiline_devider_replacer
def cmd_group(ctx: Context):
    """
    TC420 LED Controller CLI Utility

    You can chain multiple commands (see below) together like this:

    \b
    tc420-cli {MULTILINE_DIVIDER}
        time-sync {MULTILINE_DIVIDER}
        mode -n test1 -s 00:00 0 0 0 0 0 -s 12:00 100 100 100 100 100 {MULTILINE_DIVIDER}
        mode -n test2 -s 05:00 10 10 30 0 0 -s 15:05 100 50 50 0 100

    If you need further help of a command, you can use --help option after the command name:

    \b
    tc420-cli mode --help
    """
    # Initialize context
    ctx.ensure_object(CtxObj)
    try:
        ctx.obj.dev = TC420()
    except usb.core.NoBackendError:
        print("No USB backend is available. Please install \"libusb\" for your platform!")
        sys.exit(1)
    except NoDeviceFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


@cmd_group.command()
@click.pass_context
def time_sync(ctx: Context):
    """
    Synchronize device time to this computer.
    """
    print("Syncing time...", end=" ", flush=True)
    check_result(ctx.obj.dev.time_sync())


@cmd_group.command(short_help="Create mode(s) (program).")
@click.pass_context
@click.option("--name", "-n", type=str, help="The name of the mode.", required=True,
              metavar="<MODE NAME>")
@click.option("--bank", "-b", type=click.IntRange(-1, 64),
              help="The program bank number mode will use. It is indexed from 0."
              "If it is not specified or it is -1 then automatic bank numbering is used.",
              metavar="<BANK NUMBER>", default=-1)
@click.option("--step", "-s", "steps", multiple=True, required=True,
              type=(
                  click.DateTime(formats=('%H:%M', '%H.%M', '%H%M')),
                  click.IntRange(-101, 100),
                  click.IntRange(-101, 100),
                  click.IntRange(-101, 100),
                  click.IntRange(-101, 100),
                  click.IntRange(-101, 100),
              ),
              metavar="<TIME> <CH1 %> <CH2 %> <CH3 %> <CH4 %> <CH5 %>",
              help="Step data: e.g.: 13:00 100 99 50 0 -70"
              "\n\nNegative channel values are \"jump\" (immediate) values, but because -0 is not "
              "interpretable, jump values are shifted by one. So -1 will be 0, -2 will be 1 ... and "
              "-101 will be 100.")
def mode(ctx: Context, name: str, bank: int, steps: Tuple[Tuple[datetime, int, int, int, int, int]]):
    """
    Create (or modify) mode(s) (program).

    If you want to create multiple modes, you may add multiple mode commands.

    You can specify program bank number, that way you can overwrite a specific mode.
    If no bank number is specified, the last mode's bank number plus one is used. If the 1st
    mode has no bank number, bank 0 is used. You can also mix auto and manual bank numbering.
    Please noted that if you leave gaps in banks, device will not skip them in LCD menu, there will be
    empty programs.
    """
    def step_ready_cb(step_num):
        print(f"{step_num}", end=" ", flush=True)

    # Automatic bank assignment
    if bank == -1:
        bank = ctx.obj.bank + 1
    ctx.obj.bank = bank

    print(f"Setting mode '{name}' in bank {bank}...", end=" ", flush=True)
    check_result(ctx.obj.dev.mode(name=name, bank=bank, steps=steps, step_ready_cb=step_ready_cb))
    ctx.obj.mode_stop_neded = True


@cmd_group.command()
@click.pass_context
def clear_all_modes(ctx: Context):
    """
    Clear all modes (programs) from the device.
    """
    print("Clearing all modes from device...", end=" ", flush=True)
    check_result(ctx.obj.dev.mode_clear_all())


@cmd_group.command(short_help='Fast Play a custom program without saving it to the device.')
@click.option("--name", "-n", type=str, help="The name of the play mode. "
              "(It will be written on the device screen)", required=True,
              metavar="<MODE NAME>")
@click.option("--steps", "-s", "steps", multiple=True, required=True,
              type=(
                  float,
                  click.IntRange(-101, 100),
                  click.IntRange(-101, 100),
                  click.IntRange(-101, 100),
                  click.IntRange(-101, 100),
                  click.IntRange(-101, 100),
              ),
              metavar="<DURATION sec> <CH1 %> <CH2 %> <CH3 %> <CH4 %> <CH5 %>",
              help="Step data: e.g.: 1.5 100 99 50 0 -70"
              "\n\nNegative channel values are \"jump\" (immediate) values, but because -0 is not "
              "interpretable, jump values are shifted by one. So -1 will be 0, -2 will be 1 ... and "
              "-101 will be 100.")
@click.pass_context
def play(ctx: Context, name: str, steps: Tuple[Tuple[float, int, int, int, int, int]]):
    """
    "Fast" Play a custom program without saving it to the device.
    In play mode you specify the time for fading into the new channel values instead of wall clock time.

    It is useful for e.g. Test your imagined program without waiting a whole day or testing effects, colors...

    You can place multiple --steps option to create a complete scene.
    """
    print(f"Initialize playing '{name}'...", end=" ", flush=True)

    ctx.obj.mode_stop_neded = True

    def adapter(step_idx: int):
        """ Callback to give the next step """
        try:
            try:
                return steps[step_idx]
            except IndexError:
                return None  # Stop iteration

        except KeyboardInterrupt:
            print("Cancelled.")
            return None  # Stop iteration

    def onchange_callback(idx: int, elapsed_time: float, channels: Tuple[int, int, int, int, int]):
        print(f"\rPlaying (CTRL+C to exit)... Idx: {idx:2}, time: {elapsed_time:4.1f}, "
              f"CH1: {channels[0]:3}, CH2: {channels[1]:3}, CH3: {channels[2]:3}, "
              f"CH4: {channels[3]:3}, CH5: {channels[4]:3}\r", end="", flush=True)

    try:
        ctx.obj.dev.play(name=name, adapter=adapter, onchange_callback=onchange_callback)
        print("")
    except KeyboardInterrupt:
        print("\rCancelled." + " " * 87)


@cmd_group.command()
@click.option("--channels", "-c", "channel_mask", default=(1, 1, 1, 1, 1),
              type=(
                  click.IntRange(0, 1),
                  click.IntRange(0, 1),
                  click.IntRange(0, 1),
                  click.IntRange(0, 1),
                  click.IntRange(0, 1),
),
    metavar="<<CH1> <CH2> <CH3> <CH4> <CH5>",
    help="Channel mask, 1 where you want the channel to be used, 0 where no use.")
@click.pass_context
def demo(ctx: Context, channel_mask: Tuple[int, int, int, int, int]):
    """
    "Fast" play a demo scene. You can stop it by pressing CTRL+C.

    This fades in-out channels randomly. Doesn't touch programs already on device.
    """
    print(f"Initialize playing 'Demo'...", end=" ", flush=True)

    ctx.obj.mode_stop_neded = True

    def rand_sleep(): return 0.0005 + (random() * 0.01)

    channels = [randint(0, 100) for _ in range(5)]  # Initial channel values
    directions = [randint(0, 1) for _ in range(5)]  # Channel directions
    sleeps = [rand_sleep() for _ in range(5)]  # Initial sleeps
    timers = [0.0] * 5
    started = False

    def adapter(_):
        """ Callback to give the next step """
        nonlocal started

        if not started:
            started = True
            print("OK.")

        changed = False

        while not changed:
            for i in range(5):
                timers[i] -= 0.0001   # Decrease timer

                if timers[i] <= 0:  # If a channel timer is elapsed
                    changed = True
                    # If a channel reached its end value
                    channels[i] += 1 if directions[i] == 1 else -1
                    if channel_mask[i] == 0:  # Channel masking support
                        channels[i] = 0
                    if channels[i] <= 0:
                        channels[i] = 0
                        directions[i] = 1  # Change direction
                        sleeps[i] = rand_sleep()  # Change speed
                    elif channels[i] >= 100:
                        channels[i] = 100
                        directions[i] = 0  # Change direction
                        sleeps[i] = rand_sleep()  # Change speed

                    timers[i] = sleeps[i]  # Restart timer

        return [0.0001, ] + channels

    def onchange(_, __, channels):
        print(f"\rPlaying (CTRL+C to exit)... CH1: {channels[0]:3}, CH2: {channels[1]:3}, CH3: {channels[2]:3}, "
              f"CH4: {channels[3]:3}, CH5: {channels[4]:3}\r", end="", flush=True)

    try:
        ctx.obj.dev.play(name="Demo", adapter=adapter, onchange_callback=onchange)
        print("")
    except KeyboardInterrupt:
        print("\rCancelled." + " " * 66)
        return None  # Stop iteration


@cmd_group.result_callback()
@click.pass_context
def finalize(ctx: Context, _):
    """
    Finalize command chain
    """
    if ctx.obj.mode_stop_neded:
        # Close mode commands
        print("Finalizing modes...", end=" ", flush=True)
        check_result(ctx.obj.dev.mode_stop())


def main():
    # Start command group
    cmd_group()


if __name__ == '__main__':
    main()
