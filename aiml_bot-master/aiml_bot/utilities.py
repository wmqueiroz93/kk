"""
This file contains assorted general utility functions used by other
modules in the aiml_bot package.
"""


# TODO: Correctly handle abbreviations.
def split_sentences(text: str) -> list:
    """Split the string s into a list of sentences."""
    if not isinstance(text, str):
        raise TypeError(text)
    position = 0
    results = []
    length = len(text)
    while position < length:
        try:
            period = text.index('.', position)
        except ValueError:
            period = length + 1
        try:
            question = text.index('?', position)
        except ValueError:
            question = length + 1
        try:
            exclamation = text.index('!', position)
        except ValueError:
            exclamation = length + 1
        end = min(period, question, exclamation)
        sentence = text[position:end].strip()
        if sentence:
            results.append(sentence)
        position = end + 1
    # If no sentences were found, return a one-item list containing
    # the entire input string.
    if not results:
        results.append(text.strip())
    # print(results)
    return results
