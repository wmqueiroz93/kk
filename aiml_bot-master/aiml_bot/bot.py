# -*- coding: latin-1 -*-

"""This file contains the public interface to the aiml module."""

import copy
import glob
import os
import random
import re
import string
import sys
import threading
import time
import xml.sax
from configparser import ConfigParser

from .aiml_parser import create_parser
from .default_substitutions import default_gender, default_person, default_person2, default_normal
from .pattern_manager import PatternManager
from .utilities import split_sentences
from .word_substitutions import WordSub

AIML_INSTALL_PATH = os.path.expanduser('~/.aiml')
try:
    import aiml_sets
except ImportError:
    aiml_sets = None
else:
    for set_name in aiml_sets.list_aiml_sets():
        if not aiml_sets.is_installed(set_name, destination_path=AIML_INSTALL_PATH):
            aiml_sets.install(set_name, destination_path=AIML_INSTALL_PATH)


__version__ = '0.0'


DEFAULT_ENCODING = 'utf-8'
DEFAULT_SESSION_ID = "anonymous"

# special predicate keys
INPUT_HISTORY = "<INPUT HISTORY>"  # keys to a queue (list) of recent user input
OUTPUT_HISTORY = "<OUTPUT HISTORY>"  # keys to a queue (list) of recent responses.
INPUT_STACK = "<INPUT STACK>"  # Should always be empty in between calls to respond()


BOOTSTRAP_AIML_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'bootstrap.aiml'))


class Bot:
    """
    The AIML bot.
    """

    _max_history_size = 10  # maximum length of the _inputs and _responses lists
    _max_recursion_depth = 100  # maximum number of recursive <srai>/<sr> tags before the response is aborted.

    def __init__(self, brain_file: str = None, learn=None, commands=None, verbose: bool = True) -> None:
        self._verbose_mode = verbose
        self._brain = PatternManager()
        self._respond_lock = threading.RLock()
        self._text_encoding = DEFAULT_ENCODING

        # set up the sessions        
        self._sessions = {}
        self.add_session(DEFAULT_SESSION_ID)

        # Set up the bot predicates
        self._bot_predicates = {}
        self.set_bot_predicate("name", "Nameless")

        # set up the word substitutors (subbers):
        self._subbers = {
            'gender': WordSub(default_gender),
            'person': WordSub(default_person),
            'person2': WordSub(default_person2),
            'normal': WordSub(default_normal)
        }

        self.bootstrap(brain_file, learn, commands)

    def bootstrap(self, brain_file: str = None, learn=None, commands=None) -> None:
        """Prepare a Bot object for use.

        If a brainFile argument is provided, the Bot attempts to
        load the brain at the specified filename.

        If learnFiles is provided, the Bot attempts to load the
        specified AIML files.

        Finally, each of the input strings in the commands list is
        passed to respond().
        """
        loaded_brain = False

        start = time.clock()
        if brain_file and os.path.isfile(brain_file):
            self.load_brain(brain_file)
            loaded_brain = True

        if learn is None:
            if loaded_brain:
                learn = []
            else:
                learn = [BOOTSTRAP_AIML_PATH]
        elif isinstance(learn, str):
            # learnFiles might be a string, in which case it should be
            # turned into a single-element list.
            learn = [learn]
        else:
            learn = learn
        for file in learn:
            file = os.path.abspath(os.path.expanduser(file))
            self.learn(file)

        if commands is None:
            commands = []
        elif isinstance(commands, str):
            # ditto for commands
            commands = [commands]
        for cmd in commands:
            print(self._respond(cmd, DEFAULT_SESSION_ID))
            
        if self._verbose_mode:
            print("Bot bootstrap completed in %.2f seconds" % (time.clock() - start))

    @property
    def name(self) -> str:
        """The name of the bot."""
        return self._brain.bot_name

    @name.setter
    def name(self, value: str) -> None:
        """The name of the bot."""
        self._bot_predicates['name'] = value
        self._brain.bot_name = value

    @property
    def verbose(self) -> bool:
        """Verbose output mode."""
        return self._verbose_mode

    @verbose.setter
    def verbose(self, value: bool) -> None:
        """Verbose output mode."""
        self._verbose_mode = value

    @property
    def version(self) -> str:
        """Return the Bot's version string."""
        return 'AIML Bot ' + __version__

    @property
    def text_encoding(self) -> str:
        """Set the text encoding used when loading AIML files (Latin-1, UTF-8, etc.)."""
        return self._text_encoding

    @text_encoding.setter
    def text_encoding(self, value: str) -> None:
        """Set the text encoding used when loading AIML files (Latin-1, UTF-8, etc.)."""
        self._text_encoding = value

    @property
    def category_count(self) -> int:
        """Return the number of categories the Bot has learned."""
        # there's a one-to-one mapping between templates and categories
        return self._brain.template_count

    def reset_brain(self) -> None:
        """Reset the brain to its initial state."""
        self._brain = PatternManager()

    def load_brain(self, filename: str) -> None:
        """Attempt to load a previously-saved 'brain' from the
        specified filename.

        NOTE: the current contents of the 'brain' will be discarded!
        """
        if self._verbose_mode:
            print("Loading brain from %s..." % filename,)
        start = time.clock()
        self._brain.restore(filename)
        if self._verbose_mode:
            end = time.clock() - start
            print("done (%d categories in %.2f seconds)" % (self._brain.template_count, end))

    def save_brain(self, filename: str) -> None:
        """Dump the contents of the bot's brain to a file on disk."""
        if self._verbose_mode:
            print("Saving brain to %s..." % filename,)
        start = time.clock()
        self._brain.save(filename)
        if self._verbose_mode:
            print("done (%.2f seconds)" % (time.clock() - start))

    def get_predicate(self, name: str, session_id: str = None) -> str:
        """Retrieve the current value of the predicate 'name' from the
        specified session.

        If name is not a valid predicate in the session, the empty
        string is returned.
        """
        assert name not in (INPUT_STACK, INPUT_HISTORY, OUTPUT_HISTORY)
        if session_id is None:
            session_id = DEFAULT_SESSION_ID
        return self._sessions[session_id].get(name, '')

    def set_predicate(self, name: str, value: object, session_id: str = None) -> None:
        """Set the value of the predicate 'name' in the specified
        session.

        If sessionID is not a valid session, it will be created. If
        name is not a valid predicate in the session, it will be
        created.
        """
        assert name not in (INPUT_STACK, INPUT_HISTORY, OUTPUT_HISTORY)
        if session_id is None:
            session_id = DEFAULT_SESSION_ID
        self.add_session(session_id)  # add the session, if it doesn't already exist.
        self._sessions[session_id][name] = value

    def get_input_history(self, session_id: str = None) -> list:
        """Get the input history for the given session."""
        if session_id is None:
            session_id = DEFAULT_SESSION_ID
        self.add_session(session_id)
        return self._sessions[session_id][INPUT_HISTORY]

    def set_input_history(self, history: list, session_id: str = None) -> None:
        """Set the input history for the given session."""
        if session_id is None:
            session_id = DEFAULT_SESSION_ID
        self.add_session(session_id)
        self._sessions[session_id][INPUT_HISTORY] = history

    def get_output_history(self, session_id: str = None) -> list:
        """Get the output history for the given session."""
        if session_id is None:
            session_id = DEFAULT_SESSION_ID
        self.add_session(session_id)
        return self._sessions[session_id][OUTPUT_HISTORY]

    def set_output_history(self, history: list, session_id: str = None) -> None:
        """Set the output history for the given session."""
        if session_id is None:
            session_id = DEFAULT_SESSION_ID
        self.add_session(session_id)
        self._sessions[session_id][OUTPUT_HISTORY] = history

    def get_input_stack(self, session_id: str = None) -> list:
        """Get the input stack for the given session."""
        if session_id is None:
            session_id = DEFAULT_SESSION_ID
        self.add_session(session_id)
        return self._sessions[session_id][INPUT_STACK]

    def set_input_stack(self, stack: list, session_id: str = None) -> None:
        """Set the input stack for the given session."""
        if session_id is None:
            session_id = DEFAULT_SESSION_ID
        self.add_session(session_id)
        self._sessions[session_id][INPUT_STACK] = stack

    def get_bot_predicate(self, name: str) -> str:
        """Retrieve the value of the specified bot predicate."""
        return self._bot_predicates.get(name, '')

    def set_bot_predicate(self, name: str, value: str) -> None:
        """Set the value of the specified bot predicate.

        If name is not a valid bot predicate, it will be created.
        """
        self._bot_predicates[name] = value
        # Clumsy hack: if updating the bot name, we must update the
        # name in the brain as well
        if name == "name":
            self._brain.bot_name = value

    def load_substitutions(self, filename: str) -> None:
        """
        Load a substitutions file.

        The file must be in the Windows-style INI format (see the
        standard ConfigParser module docs for information on this
        format).  Each section of the file is loaded into its own
        substitutor.
        """
        parser = ConfigParser()
        parser.read(filename)
        for s in parser.sections():
            # Add a new WordSub instance for this section.  If one already
            # exists, delete it.
            if s in self._subbers:
                del(self._subbers[s])
            self._subbers[s] = WordSub()
            # iterate over the key,value pairs and add them to the subber
            for key, v in parser.items(s):
                self._subbers[s][key] = v

    def add_session(self, session_id: str) -> None:
        """Create a new session with the specified ID string."""
        # Create the session.
        if session_id in self._sessions:
            session_data = self._sessions[session_id]
        else:
            session_data = self._sessions[session_id] = {}
        # Initialize the special reserved predicates
        for key in INPUT_HISTORY, OUTPUT_HISTORY, INPUT_STACK:
            if key not in session_data:
                session_data[key] = []

    def delete_session(self, session_id: str):
        """Delete the specified session."""
        if session_id in self._sessions:
            self._sessions.pop(session_id)

    def get_session_data(self, session_id: str = None) -> dict:
        """Return a copy of the session data dictionary for the
        specified session.
        """
        if session_id is None:
            session_id = DEFAULT_SESSION_ID
        self.add_session(session_id)
        return copy.deepcopy(self._sessions[session_id])

    def set_session_data(self, data: dict, session_id: str = None) -> None:
        """
        Set the session data dictionary for the specified session.
        """
        if session_id is None:
            session_id = DEFAULT_SESSION_ID
        self._sessions[session_id] = data

    def learn(self, filename: str) -> None:
        """Load and learn the contents of the specified AIML file.

        If filename includes wildcard characters, all matching files
        will be loaded and learned.
        """

        filenames = [filename]
        if filename != os.path.join(AIML_INSTALL_PATH, filename):
            filenames.append(os.path.join(AIML_INSTALL_PATH, filename))
        filenames += [filename.lower() for filename in filenames]

        for filename in filenames:
            for f in glob.glob(filename):
                if not os.path.isfile(f):
                    continue  # Skip folders.
                if self._verbose_mode:
                    print("Loading %s..." % f,)
                start = time.clock()
                # Load and parse the AIML file.
                parser = create_parser()
                handler = parser.getContentHandler()
                handler.setEncoding(self._text_encoding)
                try:
                    parser.parse(f)
                except xml.sax.SAXParseException as msg:
                    err = "\nFATAL PARSE ERROR in file %s:\n%s\n" % (f, msg)
                    sys.stderr.write(err)
                    continue
                # store the pattern/template pairs in the PatternManager.
                for key, tem in handler.categories.items():
                    self._brain.add(*key, tem)
                # Parsing was successful.
                if self._verbose_mode:
                    print("done (%.2f seconds)" % (time.clock() - start))

    def respond(self, text: str, session_id: str = None) -> str:
        """Return the Bot's response to the input string."""
        if not text:
            return ""

        if session_id is None:
            session_id = DEFAULT_SESSION_ID

        # prevent other threads from stomping all over us.
        self._respond_lock.acquire()

        # Add the session, if it doesn't already exist
        self.add_session(session_id)

        # split the input into discrete sentences
        sentences = split_sentences(text)
        final_response = ""
        for s in sentences:
            # Add the input to the history list before fetching the
            # response, so that <input/> tags work properly.
            input_history = self.get_input_history(session_id)
            if not isinstance(input_history, list):
                input_history = []
            input_history.append(s)
            while len(input_history) > self._max_history_size:
                input_history.pop(0)
            self.set_input_history(input_history, session_id)
            
            # Fetch the response
            response = self._respond(s, session_id)

            # add the data from this exchange to the history lists
            output_history = self.get_output_history(session_id)
            if not isinstance(output_history, list):
                output_history = []
            output_history.append(response)
            while len(output_history) > self._max_history_size:
                output_history.pop(0)
            self.set_output_history(output_history, session_id)

            # append this response to the final response.
            final_response += (response + "  ")
        final_response = final_response.strip()

        assert not self.get_input_stack(session_id)

        # release the lock and return
        self._respond_lock.release()
        return final_response

    # This version of _respond() just fetches the response for some input.
    # It does not mess with the input and output histories.  Recursive calls
    # to respond() spawned from tags like <srai> should call this function
    # instead of respond().
    def _respond(self, text: str, session_id: str) -> str:
        """Private version of respond(), does the real work."""
        if not text:
            return ""

        # guard against infinite recursion
        input_stack = self.get_input_stack(session_id)
        if len(input_stack) > self._max_recursion_depth:
            if self._verbose_mode:
                err = "WARNING: maximum recursion depth exceeded (input='%s')" % text
                sys.stderr.write(err)
            return ""

        # push the input onto the input stack
        input_stack.append(text)
        self.set_input_stack(input_stack, session_id)

        # run the input through the 'normal' subber
        subbed_input = self._subbers['normal'].sub(text)

        # fetch the bot's previous response, to pass to the match()
        # function as 'that'.
        output_history = self.get_output_history(session_id)
        if output_history:
            that = output_history[-1]
        else:
            that = ""
        subbed_that = self._subbers['normal'].sub(that)

        # fetch the current topic
        topic = self.get_predicate("topic", session_id)
        subbed_topic = self._subbers['normal'].sub(topic)

        # Determine the final response.
        response = ""
        elem = self._brain.match(subbed_input, subbed_that, subbed_topic)
        if elem is None:
            if self._verbose_mode:
                err = "WARNING: No match found for input: %s\n" % text
                sys.stderr.write(err)
        else:
            # Process the element into a response string.
            response += self._process_element(elem, session_id).strip()
            response += " "
        response = response.strip()

        # pop the top entry off the input stack.
        input_stack = self.get_input_stack(session_id)
        input_stack.pop()
        self.set_input_stack(input_stack, session_id)
        
        return response

    def _process_element(self, element: list, session_id: str) -> str:
        """Process an AIML element.

        The first item of the elem list is the name of the element's
        XML tag.  The second item is a dictionary containing any
        attributes passed to that tag, and their values.  Any further
        items in the list are the elements enclosed by the current
        element's begin and end tags; they are handled by each
        element's handler function.
        """
        element_name = element[0]
        handler_name = '_process_' + element_name
        handler = getattr(self, handler_name, None)
        if handler is None:
            # Oops -- there's no handler function for this element type!
            if self._verbose_mode:
                err = "WARNING: No handler found for <%s> element\n" % element[0]
                sys.stderr.write(err)
            return ""
        return handler(element, session_id)

    ##################################################
    # Individual element-processing functions follow #
    ##################################################

    # <bot>
    # noinspection PyUnusedLocal
    def _process_bot(self, element: list, session_id: str) -> str:
        """Process a <bot> AIML element.

        Required element attributes:
            name: The name of the bot predicate to retrieve.

        <bot> elements are used to fetch the value of global,
        read-only "bot predicates."  These predicates cannot be set
        from within AIML; you must use the setBotPredicate() function.
        """
        return self.get_bot_predicate(element[1]['name'])
        
    # <condition>
    def _process_condition(self, element: list, session_id: str) -> str:
        """Process a <condition> AIML element.

        Optional element attributes:
            name: The name of a predicate to test.
            value: The value to test the predicate for.

        <condition> elements come in three flavors.  Each has different
        attributes, and each handles their contents differently.

        The simplest case is when the <condition> tag has both a 'name'
        and a 'value' attribute.  In this case, if the predicate
        'name' has the value 'value', then the contents of the element
        are processed and returned.
        
        If the <condition> element has only a 'name' attribute, then
        its contents are a series of <li> elements, each of which has
        a 'value' attribute.  The list is scanned from top to bottom
        until a match is found.  Optionally, the last <li> element can
        have no 'value' attribute, in which case it is processed and
        returned if no other match is found.

        If the <condition> element has neither a 'name' nor a 'value'
        attribute, then it behaves almost exactly like the previous
        case, except that each <li> subelement (except the optional
        last entry) must now include both 'name' and 'value'
        attributes.
        """        
        response = ""
        attributes = element[1]
        name = attributes.get('name', None)
        value = attributes.get('value', None)
        
        # Case #1: test the value of a specific predicate for a
        # specific value.
        if name is not None and value is not None:
            if self.get_predicate(name, session_id) == value:
                for e in element[2:]:
                    response += self._process_element(e, session_id)
                return response
        else:
            # Case #2 and #3: Cycle through <li> contents, testing a
            # name and value pair for each one.
            try:
                # Get the list of <li> elements
                list_items = []
                for e in element[2:]:
                    if e[0] == 'li':
                        list_items.append(e)
                # if list_items is empty, return the empty string
                if not list_items:
                    return ""
                # iterate through the list looking for a condition that
                # matches.
                found_match = False
                for index, li in enumerate(list_items):
                    try:
                        li_attributes = li[1]
                        # if this is the last list item, it's allowed
                        # to have no attributes.  We just skip it for now.
                        if not li_attributes and index + 1 == len(list_items):
                            break
                        # get the name of the predicate to test
                        li_name = name
                        if li_name is None:
                            li_name = li_attributes['name']
                        # get the value to check against
                        li_value = li_attributes['value']
                        # do the test
                        if self.get_predicate(li_name, session_id) == li_value:
                            found_match = True
                            response += self._process_element(li, session_id)
                            break
                    except:
                        # No attributes, no name/value attributes, no
                        # such predicate/session, or processing error.
                        if self._verbose_mode:
                            print("Something amiss -- skipping list item", li)
                        raise
                if not found_match:
                    # Check the last element of list_items.  If it has
                    # no 'name' or 'value' attribute, process it.
                    try:
                        li = list_items[-1]
                        li_attributes = li[1]
                        if not ('name' in li_attributes or 'value' in li_attributes):
                            response += self._process_element(li, session_id)
                    except:
                        # list_items was empty, no attributes, missing
                        # name/value attributes, or processing error.
                        if self._verbose_mode:
                            print("error in default list item")
                        raise
            except Exception:
                # Some other catastrophic cataclysm
                if self._verbose_mode:
                    print("catastrophic condition failure")
                raise
        return response
        
    # <date>
    # noinspection PyUnusedLocal
    @staticmethod
    def _process_date(element: list, session_id: str) -> str:
        """Process a <date> AIML element.

        <date> elements resolve to the current date and time.  The
        AIML specification doesn't require any particular format for
        this information, so I go with whatever's simplest.
        """        
        return time.asctime()

    # <formal>
    def _process_formal(self, element: list, session_id: str) -> str:
        """Process a <formal> AIML element.

        <formal> elements process their contents recursively, and then
        capitalize the first letter of each word of the result.
        """                
        response = ""
        for e in element[2:]:
            response += self._process_element(e, session_id)
        return string.capwords(response)

    # <gender>
    def _process_gender(self, element: list, session_id: str) -> str:
        """Process a <gender> AIML element.

        <gender> elements process their contents, and then swap the
        gender of any third-person singular pronouns in the result.
        This substitution is handled by the aiml.WordSub module.
        """
        response = ""
        for e in element[2:]:
            response += self._process_element(e, session_id)
        return self._subbers['gender'].sub(response)

    # <get>
    def _process_get(self, element: list, session_id: str) -> str:
        """Process a <get> AIML element.

        Required element attributes:
            name: The name of the predicate whose value should be
            retrieved from the specified session and returned.  If the
            predicate doesn't exist, the empty string is returned.

        <get> elements return the value of a predicate from the
        specified session.
        """
        return self.get_predicate(element[1]['name'], session_id)

    # <gossip>
    def _process_gossip(self, element: list, session_id: str) -> str:
        """Process a <gossip> AIML element.

        <gossip> elements are used to capture and store user input in
        an implementation-defined manner, theoretically allowing the
        bot to learn from the people it chats with.  I haven't
        decided how to define my implementation, so right now
        <gossip> behaves identically to <think>.
        """        
        return self._process_think(element, session_id)

    # <id>
    # noinspection PyUnusedLocal
    @staticmethod
    def _process_id(element: list, session_id: str) -> str:
        """ Process an <id> AIML element.

        <id> elements return a unique "user id" for a specific
        conversation. In AIML Bot, the user id is the name of the
        current session.
        """
        return session_id

    # <input>
    def _process_input(self, element: list, session_id: str) -> str:
        """Process an <input> AIML element.

        Optional attribute elements:
            index: The index of the element from the history list to
            return. 1 means the most recent item, 2 means the one
            before that, and so on.

        <input> elements return an entry from the input history for
        the current session.
        """        
        index = int(element[1].get('index', 1))
        input_history = self.get_input_history(session_id)
        if len(input_history) >= index:
            return input_history[-index]
        else:
            if self._verbose_mode:
                err = "No such index %d while processing <input> element.\n" % index
                sys.stderr.write(err)
            return ""

    # <javascript>
    def _process_javascript(self, element: list, session_id: str) -> str:
        """Process a <javascript> AIML element.

        <javascript> elements process their contents recursively, and
        then run the results through a server-side Javascript
        interpreter to compute the final response.  Implementations
        are not required to provide an actual Javascript interpreter,
        and right now AIML Bot doesn't; <javascript> elements are behave
        exactly like <think> elements.
        """        
        return self._process_think(element, session_id)
    
    # <learn>
    def _process_learn(self, element: list, session_id: str) -> str:
        """Process a <learn> AIML element.

        <learn> elements process their contents recursively, and then
        treat the result as an AIML file to open and learn.
        """
        filename = ""
        for e in element[2:]:
            filename += self._process_element(e, session_id)
        self.learn(filename)
        return ""

    # <li>
    def _process_li(self, element: list, session_id: str) -> str:
        """Process an <li> AIML element.

        Optional attribute elements:
            name: the name of a predicate to query.
            value: the value to check that predicate for.

        <li> elements process their contents recursively and return
        the results. They can only appear inside <condition> and
        <random> elements.  See _processCondition() and
        _processRandom() for details of their usage.
        """
        response = ""
        for e in element[2:]:
            response += self._process_element(e, session_id)
        return response

    # <lowercase>
    def _process_lowercase(self, element: list, session_id: str) -> str:
        """Process a <lowercase> AIML element.

        <lowercase> elements process their contents recursively, and
        then convert the results to all-lowercase.
        """
        response = ""
        for e in element[2:]:
            response += self._process_element(e, session_id)
        return response.lower()

    # <person>
    def _process_person(self, element: list, session_id: str) -> str:
        """Process a <person> AIML element.

        <person> elements process their contents recursively, and then
        convert all pronouns in the results from 1st person to 2nd
        person, and vice versa.  This substitution is handled by the
        aiml.WordSub module.

        If the <person> tag is used atomically (e.g. <person/>), it is
        a shortcut for <person><star/></person>.
        """
        response = ""
        for e in element[2:]:
            response += self._process_element(e, session_id)
        if len(element) <= 2:  # atomic <person/> = <person><star/></person>
            response = self._process_element(['star', {}], session_id)
        return self._subbers['person'].sub(response)

    # <person2>
    def _process_person2(self, element: list, session_id: str) -> str:
        """Process a <person2> AIML element.

        <person2> elements process their contents recursively, and then
        convert all pronouns in the results from 1st person to 3rd
        person, and vice versa.  This substitution is handled by the
        aiml.WordSub module.

        If the <person2> tag is used atomically (e.g. <person2/>), it is
        a shortcut for <person2><star/></person2>.
        """
        response = ""
        for e in element[2:]:
            response += self._process_element(e, session_id)
        if len(element) <= 2:  # atomic <person2/> = <person2><star/></person2>
            response = self._process_element(['star', {}], session_id)
        return self._subbers['person2'].sub(response)
        
    # <random>
    def _process_random(self, element: list, session_id: str) -> str:
        """Process a <random> AIML element.

        <random> elements contain zero or more <li> elements.  If
        none, the empty string is returned.  If one or more <li>
        elements are present, one of them is selected randomly to be
        processed recursively and have its results returned.  Only the
        chosen <li> element's contents are processed.  Any non-<li> contents are
        ignored.
        """
        list_items = []
        for e in element[2:]:
            if e[0] == 'li':
                list_items.append(e)
        if not list_items:
            return ""

        # select and process a random list item.
        item = random.choice(list_items)
        return self._process_element(item, session_id)
        
    # <sentence>
    def _process_sentence(self, element: list, session_id: str) -> str:
        """Process a <sentence> AIML element.

        <sentence> elements process their contents recursively, and
        then capitalize the first letter of the results.
        """
        response = ""
        for e in element[2:]:
            response += self._process_element(e, session_id)
        response = response.strip()
        return response[:1].upper() + response[1:]

    # <set>
    def _process_set(self, element: list, session_id: str) -> str:
        """Process a <set> AIML element.

        Required element attributes:
            name: The name of the predicate to set.

        <set> elements process their contents recursively, and assign the results to a predicate
        (given by their 'name' attribute) in the current session.  The contents of the element
        are also returned.
        """
        value = ""
        for e in element[2:]:
            value += self._process_element(e, session_id)
        self.set_predicate(element[1]['name'], value, session_id)
        return value

    # <size>
    # noinspection PyUnusedLocal
    def _process_size(self, element: list, session_id: str) -> str:
        """Process a <size> AIML element.

        <size> elements return the number of AIML categories currently
        in the bot's brain.
        """        
        return str(self.category_count)

    # <sr>
    # noinspection PyUnusedLocal
    def _process_sr(self, element: list, session_id: str) -> str:
        """Process an <sr> AIML element.

        <sr> elements are shortcuts for <srai><star/></srai>.
        """
        star = self._process_element(['star', {}], session_id)
        return self._respond(star, session_id)

    # <srai>
    def _process_srai(self, element: list, session_id: str) -> str:
        """Process a <srai> AIML element.

        <srai> elements recursively process their contents, and then
        pass the results right back into the AIML interpreter as a new
        piece of input.  The results of this new input string are
        returned.
        """
        new_input = ""
        for e in element[2:]:
            new_input += self._process_element(e, session_id)
        return self._respond(new_input, session_id)

    # <star>
    def _process_star(self, element: list, session_id: str) -> str:
        """Process a <star> AIML element.

        Optional attribute elements:
            index: Which "*" character in the current pattern should
            be matched?

        <star> elements return the text fragment matched by the "*"
        character in the current input pattern.  For example, if the
        input "Hello Tom Smith, how are you?" matched the pattern
        "HELLO * HOW ARE YOU", then a <star> element in the template
        would evaluate to "Tom Smith".
        """
        index = int(element[1].get('index', 1))
        # fetch the user's last input
        input_stack = self.get_input_stack(session_id)
        text_input = self._subbers['normal'].sub(input_stack[-1])
        # fetch the Bot's last response (for 'that' context)
        output_history = self.get_output_history(session_id)
        if output_history:
            that = self._subbers['normal'].sub(output_history[-1])
        else:
            that = ''  # there might not be any output yet
        topic = self.get_predicate("topic", session_id)
        return self._brain.star("star", text_input, that, topic, index)

    # <system>
    def _process_system(self, element: list, session_id: str) -> str:
        """Process a <system> AIML element.

        <system> elements process their contents recursively, and then
        attempt to execute the results as a shell command on the
        server.  The AIML interpreter blocks until the command is
        complete, and then returns the command's output.

        For cross-platform compatibility, any file paths inside
        <system> tags should use Unix-style forward slashes ("/") as a
        directory separator.
        """
        # build up the command string
        command = ""
        for e in element[2:]:
            command += self._process_element(e, session_id)

        # normalize the path to the command.  Under Windows, this
        # switches forward-slashes to back-slashes; all system
        # elements should use unix-style paths for cross-platform
        # compatibility.
        #executable,args = command.split(" ", 1)
        #executable = os.path.normpath(executable)
        #command = executable + " " + args
        command = os.path.normpath(command)

        # execute the command.
        response = ""
        try:
            out = os.popen(command)            
        except RuntimeError as msg:
            if self._verbose_mode:
                err = "WARNING: RuntimeError while processing \"system\" element:\n%s\n" % str(msg)
                sys.stderr.write(err)
            return "There was an error while computing my response.  Please inform my botmaster."
        time.sleep(0.01)  # I'm told this works around a potential IOError exception.
        for line in out:
            response += line + "\n"
        response = ' '.join(response.splitlines()).strip()
        return response

    # <template>
    def _process_template(self, element: list, session_id: str) -> str:
        """Process a <template> AIML element.

        <template> elements recursively process their contents, and
        return the results.  <template> is the root node of any AIML
        response tree.
        """
        response = ""
        for e in element[2:]:
            response += self._process_element(e, session_id)
        return response

    # text
    # noinspection PyUnusedLocal
    @staticmethod
    def _process_text(element: list, session_id: str) -> str:
        """Process a raw text element.

        Raw text elements aren't really AIML tags. Text elements cannot contain
        other elements; instead, the third item of the 'elem' list is a text
        string, which is immediately returned. They have a single attribute,
        automatically inserted by the parser, which indicates whether whitespace
        in the text should be preserved or not.
        """
        if not isinstance(element[2], str):
            raise TypeError("Text element contents are not text")

        # If the the whitespace behavior for this element is "default",
        # we reduce all stretches of >1 whitespace characters to a single
        # space.  To improve performance, we do this only once for each
        # text element encountered, and save the results for the future.
        if element[1]["xml:space"] == "default":
            # We can't just split and join because we need to preserve the
            # leading and trailing spaces.
            element[2] = re.sub('\s+', ' ', element[2])
            element[1]["xml:space"] = "preserve"
        return element[2]

    # <that>
    def _process_that(self, element: list, session_id: str) -> str:
        """Process a <that> AIML element.

        Optional element attributes:
            index: Specifies which element from the output history to
            return.  1 is the most recent response, 2 is the next most
            recent, and so on.

        <that> elements (when they appear inside <template> elements)
        are the output equivalent of <input> elements; they return one
        of the Bot's previous responses.
        """
        output_history = self.get_output_history(session_id)

        index = element[1].get('index', '1')
        if ',' in index:
            index, sentence_index = index.split(',')
            sentence_index = int(sentence_index)
        else:
            sentence_index = None
        index = int(index)

        if len(output_history) >= index:
            previous_output = output_history[-index]
        else:
            if self._verbose_mode:
                err = "No such history index %d while processing <that> element.\n" % index
                sys.stderr.write(err)
            return ''

        if sentence_index is None:
            return previous_output

        sentences = split_sentences(previous_output)
        if 0 < sentence_index <= len(sentences):
            return split_sentences(previous_output)[sentence_index - 1]
        else:
            if self._verbose_mode:
                err = "No such sentence index %d while processing <that> element.\n" % sentence_index
                sys.stderr.write(err)
            return ''

    # <thatstar>
    def _process_thatstar(self, element: list, session_id: str) -> str:
        """Process a <thatstar> AIML element.

        Optional element attributes:
            index: Specifies which "*" in the <that> pattern to match.

        <thatstar> elements are similar to <star> elements, except
        that where <star/> returns the portion of the input string
        matched by a "*" character in the pattern, <thatstar/> returns
        the portion of the previous input string that was matched by a
        "*" in the current category's <that> pattern.
        """
        index = int(element[1].get('index', 1))
        # fetch the user's last input
        input_stack = self.get_input_stack(session_id)
        text_input = self._subbers['normal'].sub(input_stack[-1])
        # fetch the Bot's last response (for 'that' context)
        output_history = self.get_output_history(session_id)
        if output_history:
            that = self._subbers['normal'].sub(output_history[-1])
        else:
            that = ''  # there might not be any output yet
        topic = self.get_predicate("topic", session_id)
        return self._brain.star("thatstar", text_input, that, topic, index)

    # <think>
    def _process_think(self, element: list, session_id: str) -> str:
        """Process a <think> AIML element.

        <think> elements process their contents recursively, and then
        discard the results and return the empty string.  They're
        useful for setting predicates and learning AIML files without
        generating any output.
        """
        for e in element[2:]:
            self._process_element(e, session_id)
        return ""

    # <topicstar>
    def _process_topicstar(self, element: list, session_id: str) -> str:
        """Process a <topicstar> AIML element.

        Optional element attributes:
            index: Specifies which "*" in the <topic> pattern to match.

        <topicstar> elements are similar to <star> elements, except
        that where <star/> returns the portion of the input string
        matched by a "*" character in the pattern, <topicstar/>
        returns the portion of current topic string that was matched
        by a "*" in the current category's <topic> pattern.
        """
        index = int(element[1].get('index', 1))
        # fetch the user's last input
        input_stack = self.get_input_stack(session_id)
        text_input = self._subbers['normal'].sub(input_stack[-1])
        # fetch the Bot's last response (for 'that' context)
        output_history = self.get_output_history(session_id)
        if output_history:
            that = self._subbers['normal'].sub(output_history[-1])
        else:
            that = ''  # there might not be any output yet
        topic = self.get_predicate("topic", session_id)
        return self._brain.star("topicstar", text_input, that, topic, index)

    # <uppercase>
    def _process_uppercase(self, element: list, session_id: str) -> str:
        """Process an <uppercase> AIML element.

        <uppercase> elements process their contents recursively, and
        return the results with all lower-case characters converted to
        upper-case.
        """
        response = ""
        for e in element[2:]:
            response += self._process_element(e, session_id)
        return response.upper()

    # <version>
    # noinspection PyUnusedLocal
    def _process_version(self, element: list, session_id: str) -> str:
        """Process a <version> AIML element.

        <version> elements return the version number of the AIML
        interpreter.
        """
        return self.version
