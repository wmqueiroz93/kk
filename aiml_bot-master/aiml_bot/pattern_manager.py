"""
An implementation of the AIML pattern-matching algorithm described
by Dr. Richard Wallace at the following site:
http://www.alicebot.org/documentation/matching.html
"""

import marshal
import pprint
import re


PUNCTUATION = "\"`~!@#$%^&*()-_=+[{]}\|;:',<.>/?"


class PatternManager:
    """
    This class implements the AIML pattern-matching algorithm described
    by Dr. Richard Wallace at the following site:
    http://www.alicebot.org/documentation/matching.html
    """

    # special dictionary keys
    _UNDERSCORE = 0
    _STAR = 1
    _TEMPLATE = 2
    _THAT = 3
    _TOPIC = 4
    _BOT_NAME = 5

    def __init__(self):
        self._root = {}
        self._template_count = 0
        self._bot_name = "Nameless"
        self._punctuation_re = re.compile("[" + re.escape(PUNCTUATION) + "]")
        self._whitespace_re = re.compile("\s+")

    @property
    def template_count(self) -> int:
        """Return the number of templates currently stored."""
        return self._template_count

    @property
    def bot_name(self) -> str:
        return self._bot_name

    @bot_name.setter
    def bot_name(self, value: str) -> None:
        """Set the name of the bot, used to match <bot name="name"> tags in
        patterns.  The name must be a single word!"""
        # Collapse a multi-word name into a single word
        self._bot_name = ''.join(value.split())

    def dump(self) -> None:
        """Print all learned patterns, for debugging purposes."""
        pprint.pprint(self._root)

    def save(self, filename: str) -> None:
        """Dump the current patterns to the file specified by filename.  To
        restore later, use restore()."""
        try:
            with open(filename, "wb") as file:
                marshal.dump(self._template_count, file)
                marshal.dump(self._bot_name, file)
                marshal.dump(self._root, file)
        except:
            print("Error saving PatternManager to file %s:" % filename)
            raise

    def restore(self, filename: str) -> None:
        """Restore a previously saved collection of patterns."""
        try:
            with open(filename, "rb") as file:
                self._template_count = marshal.load(file)
                self._bot_name = marshal.load(file)
                self._root = marshal.load(file)
        except:
            print("Error restoring PatternManager from file %s:" % filename)
            raise

    def add(self, pattern: str, that: str, topic: str, template: list) -> None:
        """
        Add a [pattern/that/topic] tuple and its corresponding template
        to the node tree.
        """

        # TODO: make sure words contains only legal characters
        # (alphanumerics,*,_)

        # Navigate through the node tree to the template's location, adding
        # nodes if necessary.
        node = self._root
        for word in pattern.split():
            key = word
            if key == "_":
                key = self._UNDERSCORE
            elif key == "*":
                key = self._STAR
            elif key == "BOT_NAME":
                key = self._BOT_NAME
            if key not in node:
                node[key] = {}
            node = node[key]

        # navigate further down, if a non-empty "that" pattern was included
        if len(that) > 0:
            if self._THAT not in node:
                node[self._THAT] = {}
            node = node[self._THAT]
            for word in that.split():
                key = word
                if key == "_":
                    key = self._UNDERSCORE
                elif key == "*":
                    key = self._STAR
                if key not in node:
                    node[key] = {}
                node = node[key]

        # navigate yet further down, if a non-empty "topic" string was included
        if len(topic) > 0:
            if self._TOPIC not in node:
                node[self._TOPIC] = {}
            node = node[self._TOPIC]
            for word in topic.split():
                key = word
                if key == "_":
                    key = self._UNDERSCORE
                elif key == "*":
                    key = self._STAR
                if key not in node:
                    node[key] = {}
                node = node[key]

        # add the template.
        if self._TEMPLATE not in node:
            self._template_count += 1
        node[self._TEMPLATE] = template

    def match(self, pattern, that, topic):
        """Return the template which is the closest match to pattern. The
        'that' parameter contains the bot's previous response. The 'topic'
        parameter contains the current topic of conversation.

        Returns None if no template is found.
        """
        if not pattern:
            return None
        # Mutilate the input.  Remove all punctuation and convert the text to all caps.
        text_input = pattern.upper()
        text_input = re.sub(self._punctuation_re, " ", text_input)
        if that.strip() == "":
            that = "ULTRABOGUSDUMMYTHAT"  # 'that' must never be empty
        thatInput = that.upper()
        thatInput = re.sub(self._punctuation_re, " ", thatInput)
        thatInput = re.sub(self._whitespace_re, " ", thatInput)
        if topic.strip() == "":
            topic = "ULTRABOGUSDUMMYTOPIC"  # 'topic' must never be empty
        topicInput = topic.upper()
        topicInput = re.sub(self._punctuation_re, " ", topicInput)

        # Pass the input off to the recursive call
        patMatch, template = self._match(text_input.split(), thatInput.split(), topicInput.split(), self._root)
        return template

    def star(self, starType, pattern, that, topic, index):
        """Returns a string, the portion of pattern that was matched by a *.

        The 'starType' parameter specifies which type of star to find.
        Legal values are:
         - 'star': matches a star in the main pattern.
         - 'thatstar': matches a star in the that pattern.
         - 'topicstar': matches a star in the topic pattern.

        """
        # Mutilate the input.  Remove all punctuation and convert the
        # text to all caps.
        text_input = pattern.upper()
        text_input = re.sub(self._punctuation_re, " ", text_input)
        text_input = re.sub(self._whitespace_re, " ", text_input)
        if that.strip() == "":
            that = "ULTRABOGUSDUMMYTHAT"  # 'that' must never be empty
        thatInput = that.upper()
        thatInput = re.sub(self._punctuation_re, " ", thatInput)
        thatInput = re.sub(self._whitespace_re, " ", thatInput)
        if topic.strip() == "":
            topic = "ULTRABOGUSDUMMYTOPIC"  # 'topic' must never be empty
        topicInput = topic.upper()
        topicInput = re.sub(self._punctuation_re, " ", topicInput)
        topicInput = re.sub(self._whitespace_re, " ", topicInput)

        # Pass the input off to the recursive pattern-matcher
        patMatch, template = self._match(text_input.split(), thatInput.split(), topicInput.split(), self._root)
        if template is None:
            return ""

        # Extract the appropriate portion of the pattern, based on the
        # starType argument.
        if starType == 'star':
            patMatch = patMatch[:patMatch.index(self._THAT)]
            words = text_input.split()
        elif starType == 'thatstar':
            patMatch = patMatch[patMatch.index(self._THAT)+1:patMatch.index(self._TOPIC)]
            words = thatInput.split()
        elif starType == 'topicstar':
            patMatch = patMatch[patMatch.index(self._TOPIC)+1:]
            words = topicInput.split()
        else:
            # unknown value
            raise ValueError("starType must be in ['star', 'thatstar', 'topicstar']")

        # compare the input string to the matched pattern, word by word.
        # At the end of this loop, if foundTheRightStar is true, start and
        # end will contain the start and end indices (in "words") of
        # the substring that the desired star matched.
        foundTheRightStar = False
        start = end = j = numStars = k = 0
        for i in range(len(words)):
            # This condition is true after processing a star
            # that ISN'T the one we're looking for.
            if i < k:
                continue
            # If we're reached the end of the pattern, we're done.
            if j == len(patMatch):
                break
            if not foundTheRightStar:
                if patMatch[j] in [self._STAR, self._UNDERSCORE]:  # we got a star
                    numStars += 1
                    if numStars == index:
                        # This is the star we care about.
                        foundTheRightStar = True
                    start = i
                    # Iterate through the rest of the string.
                    for k in range(i, len(words)):
                        # If the star is at the end of the pattern,
                        # we know exactly where it ends.
                        if j + 1 == len(patMatch):
                            end = len(words)
                            break
                        # If the words have started matching the
                        # pattern again, the star has ended.
                        if patMatch[j+1] == words[k]:
                            end = k - 1
                            # i = k
                            break
                # If we just finished processing the star we cared
                # about, we exit the loop early.
                if foundTheRightStar:
                    break
            # Move to the next element of the pattern.
            j += 1

        # extract the star words from the original, unmutilated input.
        if foundTheRightStar:
            #print string.join(pattern.split()[start:end+1])
            if starType == 'star':
                return ' '.join(pattern.split()[start:end+1])
            elif starType == 'thatstar':
                return ' '.join(that.split()[start:end+1])
            elif starType == 'topicstar':
                return ' '.join(topic.split()[start:end+1])
        else:
            return ""

    def _match(self, words, thatWords, topicWords, root):
        """Return a tuple (pat, tem) where pat is a list of nodes, starting
        at the root and leading to the matching pattern, and tem is the
        matched template.

        """
        # base-case: if the word list is empty, return the current node's
        # template.
        if len(words) == 0:
            # we're out of words.
            pattern = []
            template = None
            if len(thatWords) > 0:
                # If thatWords isn't empty, recursively
                # pattern-match on the _THAT node with thatWords as words.
                try:
                    pattern, template = self._match(thatWords, [], topicWords, root[self._THAT])
                    if pattern is not None:
                        pattern = [self._THAT] + pattern
                except KeyError:
                    pattern = []
                    template = None
            elif len(topicWords) > 0:
                # If thatWords is empty and topicWords isn't, recursively pattern
                # on the _TOPIC node with topicWords as words.
                try:
                    pattern, template = self._match(topicWords, [], [], root[self._TOPIC])
                    if pattern is not None:
                        pattern = [self._TOPIC] + pattern
                except KeyError:
                    pattern = []
                    template = None
            if template is None:
                # we're totally out of input.  Grab the template at this node.
                pattern = []
                try:
                    template = root[self._TEMPLATE]
                except KeyError:
                    template = None
            return pattern, template

        first = words[0]
        suffix = words[1:]

        # Check underscore.
        # Note: this is causing problems in the standard AIML set, and is
        # currently disabled.
        if self._UNDERSCORE in root:
            # Must include the case where suf is [] in order to handle the case
            # where a * or _ is at the end of the pattern.
            for j in range(len(suffix)+1):
                suf = suffix[j:]
                pattern, template = self._match(suf, thatWords, topicWords, root[self._UNDERSCORE])
                if template is not None:
                    newPattern = [self._UNDERSCORE] + pattern
                    return newPattern, template

        # Check first
        if first in root:
            pattern, template = self._match(suffix, thatWords, topicWords, root[first])
            if template is not None:
                newPattern = [first] + pattern
                return newPattern, template

        # check bot name
        if self._BOT_NAME in root and first == self._bot_name:
            pattern, template = self._match(suffix, thatWords, topicWords, root[self._BOT_NAME])
            if template is not None:
                newPattern = [first] + pattern
                return newPattern, template

        # check star
        if self._STAR in root:
            # Must include the case where suf is [] in order to handle the case
            # where a * or _ is at the end of the pattern.
            for j in range(len(suffix)+1):
                suf = suffix[j:]
                pattern, template = self._match(suf, thatWords, topicWords, root[self._STAR])
                if template is not None:
                    newPattern = [self._STAR] + pattern
                    return newPattern, template

        # No matches were found.
        return None, None
