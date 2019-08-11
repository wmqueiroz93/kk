import os
import sys
import traceback


# The Bot class is the only class most implementations should need.
from .bot import Bot

__all__ = [
    'Bot',
    'main',
    'USAGE'
]

__author__ = 'Cort Stratton'
__maintainer__ = 'Aaron Hosford'
__license__ = 'https://opensource.org/licenses/BSD-2-Clause'
__version__ = '0.0.3'

USAGE = """
Usage:
    python -m aiml [BRAIN_PATH] [OPTIONS]
    
BRAIN_PATH  
    The path to the .brn "brain file" where the compiled AIML is stored.

-r 
--reset
    Reset the "brain file".
    
-n
--no-std
    Do not automatically load the standard AIML rules.

""".strip()


def main():
    """
    This script demonstrates how to create a bare-bones, fully functional
    chatbot using AIML Bot.
    """

    # When loading an AIML set, you have two options: load the original
    # AIML files, or load a precompiled "brain" that was created from a
    # previous run. If no brain file is available, we force a reload of
    # the AIML files.

    brain_path = None
    reset = False
    no_std = False
    for arg in sys.argv[1:]:
        if arg in ('-r', '--reset'):
            reset = True
        elif arg in ('-n', '--no-std'):
            no_std = True
        elif brain_path is None:
            brain_path = arg
            if not brain_path.endswith('.brn'):
                brain_path += '.brn'
        else:
            print("Unexpected argument: %s" % arg)
            print(USAGE)
            return 1

    if brain_path is None:
        brain_path = os.path.expanduser('~/.aiml/default.brn')

    if not os.path.isfile(brain_path):
        reset = True

    robot = None

    if not reset:
        # Attempt to load the brain file.  If it fails, fall back on the
        # Reload method.
        # noinspection PyBroadException
        try:
            # The optional branFile argument specifies a brain file to load.
            robot = Bot(brain_file=brain_path)
        except Exception:
            print("Error loading saved brain file:")
            traceback.print_exc()
            reset = True

    if reset:
        print("Resetting.")
        # Use the Bot's bootstrap() method to initialize the Bot. The
        # optional learnFiles argument is a file (or list of files) to load.
        # The optional commands argument is a command (or list of commands)
        # to run after the files are loaded.
        if no_std:
            robot = Bot()
        else:
            robot = Bot(commands="load std aiml")
        # Now that we've loaded the brain, save it to speed things up for
        # next time.
        robot.save_brain(brain_path)

    assert robot is not None, "Bot initialization failed!"

    # Enter the main input/output loop.
    print("\nINTERACTIVE MODE (ctrl-c to exit)")
    while True:
        try:
            print(robot.respond(input("> ")))
        except KeyboardInterrupt:
            break

    robot.save_brain(brain_path)

    return 0
