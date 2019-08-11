"""
This module implements the WordSub class, modelled after a recipe
in "Python Cookbook" (Recipe 3.14, "Replacing Multiple Patterns in a
Single Pass" by Xavier Defrang).

Usage:
Use this class like a dictionary to add before/after pairs:
    > subber = TextSub()
    > subber["before"] = "after"
    > subber["begin"] = "end"
Use the sub() method to perform the substitution:
    > print subber.sub("before we begin")
    after we end
All matching is intelligently case-insensitive:
    > print subber.sub("Before we BEGIN")
    After we END
The 'before' words must be complete words -- no prefixes.
The following example illustrates this point:
    > subber["he"] = "she"
    > print subber.sub("he says he'd like to help her")
    she says she'd like to help her
Note that "he" and "he'd" were replaced, but "help" and "her" were
not.
"""

# 'dict' objects weren't available to subclass from until version 2.2.
# Get around this by importing UserDict.UserDict if the built-in dict
# object isn't available.

import re


class WordSub(dict):
    """All-in-one multiple-string-substitution class."""

    @staticmethod
    def _wordToRegex(word):
        """Convert a word to a regex object which matches the word."""
        return r"\b%s\b" % re.escape(word)
    
    def _update_regex(self):
        """Build re object based on the keys of the current
        dictionary.

        """
        self._regex = re.compile("|".join(map(self._wordToRegex, self.keys())))
        self._regexIsDirty = False

    def __init__(self, values=None):
        """Initialize the object, and populate it with the entries in
        the defaults dictionary.
        """
        super().__init__()
        if values:
            if isinstance(values, dict):
                values = values.items()
            for key, value in values:
                self[key] = value
        self._regex = None
        self._regexIsDirty = True

    def __call__(self, match):
        """Handler invoked for each regex match."""
        return self[match.group(0)]

    def __setitem__(self, i, y):
        self._regexIsDirty = True
        # for each entry the user adds, we actually add three entries:
        super().__setitem__(i.lower(), y.lower())  # key = value
        super().__setitem__(i[:1].upper() + i[1:], y[:1].upper() + y[1:])  # Key = Value
        super().__setitem__(i.upper(), y.upper())  # KEY = VALUE

    def sub(self, text):
        """Translate text, returns the modified text."""
        if self._regexIsDirty:
            self._update_regex()
        return self._regex.sub(self, text)
