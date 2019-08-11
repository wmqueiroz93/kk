AIML Bot
========

-  Original Author: Cort Stratton
-  Maintainer: Aaron Hosford
-  Project Home: https://github.com/hosford42/aiml\_bot

AIML Bot is a fork of Cort Stratton's PyAIML, a pure-Python interpreter
for AIML (Artificial Intelligence Markup Language), refactored for Pep 8
conformance and ease of use. It strives for simple, austere, 100%
compliance with the AIML 1.0.1 standard. You can find Cort's original
implementation at https://github.com/cdwfs/pyaiml. Many thanks go to him
for laying the groundwork for this project.

For information on what's new in this version, see the CHANGES.md file.

For information on the state of development, including the current level
of AIML 1.0.1 compliance, see the SUPPORTED\_TAGS.txt file.

Quick & dirty example (assuming you've installed the aiml\_sets
package):

::

    import aiml_bot

    # The Bot class is the public interface to the AIML interpreter.
    bot = aiml_bot.Bot(command='load std aiml')

    # Loop forever, reading user input from the command line and printing
    # responses.
    while True:
        # Use the 'respond' method to compute the response to a user's input
        # string.  respond() returns the interpreter's response.
        print(bot.respond(input("> ")))
