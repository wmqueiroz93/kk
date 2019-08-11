import os
import sys
import time

from .bot import Bot, BOOTSTRAP_AIML_PATH
from .utilities import split_sentences
from .word_substitutions import WordSub


SELF_TEST_AIML_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'self-test.aiml'))


def test_split_sentences():
    # sentences
    results = split_sentences("First.  Second, still?  Third and Final!  Well, not really")
    assert results == ['First.', 'Second, still?', 'Third and Final!', 'Well, not really'], results


def test_word_sub():
    subber = WordSub()
    subber["apple"] = "banana"
    subber["orange"] = "pear"
    subber["banana"] = "apple"
    subber["he"] = "she"
    subber["I'd"] = "I would"

    # test case insensitivity
    text = "I'd like one apple, one Orange and one BANANA."
    result = "I would like one banana, one Pear and one APPLE."
    if subber.sub(text) == result:
        print("Test #1 PASSED")
    else:
        print("Test #1 FAILED: '%s'" % subber.sub(text))

    text = "He said he'd like to go with me"
    result = "She said she'd like to go with me"
    if subber.sub(text) == result:
        print("Test #2 PASSED")
    else:
        print("Test #2 FAILED: '%s'" % subber.sub(text))


def test_bot():
    """Run some self-tests on the Bot."""
    k = Bot(learn=[BOOTSTRAP_AIML_PATH, SELF_TEST_AIML_PATH], commands="load std aiml")

    _num_tests = 0
    _num_passed = 0

    def _testTag(kern: Bot, tag: str, text: str, output_list: list):
        """Tests 'tag' by feeding the Bot 'input'.  If the result
        matches any of the strings in 'outputList', the test passes.
        """
        # noinspection PyGlobalUndefined
        nonlocal _num_tests, _num_passed
        _num_tests += 1
        print("Testing <" + tag + ">:", )
        response = kern.respond(text)
        if response in output_list:
            print("PASSED")
            _num_passed += 1
            return True
        else:
            print("FAILED (response: '%s')" % response)
            return False

    _testTag(k, 'bot', 'test bot', ["My name is Nameless"])

    k.set_predicate('gender', 'male')
    _testTag(k, 'condition test #1', 'test condition name value', ['You are handsome'])
    k.set_predicate('gender', 'female')
    _testTag(k, 'condition test #2', 'test condition name value', [''])
    _testTag(k, 'condition test #3', 'test condition name', ['You are beautiful'])
    k.set_predicate('gender', 'robot')
    _testTag(k, 'condition test #4', 'test condition name', ['You are genderless'])
    _testTag(k, 'condition test #5', 'test condition', ['You are genderless'])
    k.set_predicate('gender', 'male')
    _testTag(k, 'condition test #6', 'test condition', ['You are handsome'])

    # the date test will occasionally fail if the original and "test"
    # times cross a second boundary.  There's no good way to avoid
    # this problem and still do a meaningful test, so we simply
    # provide a friendly message to be printed if the test fails.
    date_warning = """
    NOTE: the <date> test will occasionally report failure even if it
    succeeds.  So long as the response looks like a date/time string,
    there's nothing to worry about.
    """
    if not _testTag(k, 'date', 'test date', ["The date is %s" % time.asctime()]):
        print(date_warning)

    _testTag(k, 'formal', 'test formal', ["Formal Test Passed"])
    _testTag(k, 'gender', 'test gender', ["He'd told her he heard that her hernia is history"])
    _testTag(k, 'get/set', 'test get and set', ["I like cheese. My favorite food is cheese"])
    _testTag(k, 'gossip', 'test gossip', ["Gossip is not yet implemented"])
    _testTag(k, 'id', 'test id', ["Your id is anonymous"])
    _testTag(k, 'input', 'test input', ['You just said: test input'])
    _testTag(k, 'javascript', 'test javascript', ["Javascript is not yet implemented"])
    _testTag(k, 'lowercase', 'test lowercase', ["The Last Word Should Be lowercase"])
    _testTag(k, 'person', 'test person', ['HE think i knows that my actions threaten him and his.'])
    _testTag(k, 'person2', 'test person2', ['YOU think me know that my actions threaten you and yours.'])
    _testTag(k, 'person2 (no contents)', 'test person2 I Love Lucy', ['YOU Love Lucy'])
    _testTag(k, 'random', 'test random', ["response #1", "response #2", "response #3"])
    _testTag(k, 'random empty', 'test random empty', ["Nothing here!"])
    _testTag(k, 'sentence', "test sentence", ["My first letter should be capitalized."])
    _testTag(k, 'size', "test size", ["I've learned %d categories" % k.category_count])
    _testTag(k, 'sr', "test sr test srai", ["srai results: srai test passed"])
    _testTag(k, 'sr nested', "test nested sr test srai", ["srai results: srai test passed"])
    _testTag(k, 'srai', "test srai", ["srai test passed"])
    _testTag(k, 'srai infinite', "test srai infinite", [""])
    _testTag(k, 'star test #1', 'intro scroll test star begin', ['Begin star matched: intro scroll'])
    _testTag(k, 'star test #2', 'test star creamy goodness middle', ['Middle star matched: creamy goodness'])
    _testTag(k, 'star test #3', 'test star end the credits roll', ['End star matched: the credits roll'])
    _testTag(k, 'star test #4', 'test star having multiple stars in a pattern makes me extremely happy',
             ['Multiple stars matched: having, stars in a pattern, extremely happy'])
    _testTag(k, 'system', "test system", ["The system says hello!"])
    _testTag(k, 'that test #1', "test that", ["I just said: The system says hello!"])
    _testTag(k, 'that test #2', "test that", ["I have already answered this question"])
    _testTag(k, 'thatstar test #1', "test thatstar", ["I say beans"])
    _testTag(k, 'thatstar test #2', "test thatstar", ["I just said \"beans\""])
    _testTag(k, 'thatstar test #3', "test thatstar multiple", ['I say beans and franks for everybody'])
    _testTag(k, 'thatstar test #4', "test thatstar multiple", ['Yes, beans and franks for all!'])
    _testTag(k, 'think', "test think", [""])
    k.set_predicate("topic", "fruit")
    _testTag(k, 'topic', "test topic", ["We were discussing apples and oranges"])
    k.set_predicate("topic", "Soylent Green")
    _testTag(k, 'topicstar test #1', 'test topicstar', ["Soylent Green is made of people!"])
    k.set_predicate("topic", "Soylent Ham and Cheese")
    _testTag(k, 'topicstar test #2', 'test topicstar multiple', ["Both Soylents Ham and Cheese are made of people!"])
    _testTag(k, 'unicode support', "ÔÇÉÏºÃ", ["Hey, you speak Chinese! ÔÇÉÏºÃ"])
    _testTag(k, 'uppercase', 'test uppercase', ["The Last Word Should Be UPPERCASE"])
    _testTag(k, 'version', 'test version', ["AIML Bot is version %s" % k.version])
    _testTag(k, 'whitespace preservation', 'test whitespace',
             ["Extra   Spaces\n   Rule!   (but not in here!)    But   Here   They   Do!"])

    # Report test results
    print("--------------------")
    if _num_tests == _num_passed:
        print("%d of %d tests passed!" % (_num_passed, _num_tests))
    else:
        print("%d of %d tests passed (see above for detailed errors)" % (_num_passed, _num_tests))

    # Run an interactive interpreter
    # print "\nEntering interactive mode (ctrl-c to exit)"
    # while True: print k.respond(raw_input("> "))


def stress_test(output_file: str = None):
    """
    This is the AIML Bot stress test. It creates two bots, and connects them in
    a cyclic loop.  A lot of output is generated; piping the results to a file
    is highly recommended.
    """

    if output_file is None:
        output_file = sys.stdout
        close_output = False
    elif isinstance(output_file, str):
        output_file = open(output_file, 'w')
        close_output = True
    else:
        close_output = False

    try:
        # Create the bots
        print("Initializing Bot #1", file=output_file)
        bot1 = Bot(commands='load std aiml', verbose=False)
        bot1.save_brain("stress.brn")
        print("\nInitializing Bot #2", file=output_file)
        bot2 = Bot(brain_file="stress.brn", verbose=False)
        os.remove("stress.brn")

        # Start the bots off with some basic input.
        response = "askquestion"

        # Off they go!
        while True:
            response = bot1.respond(response).strip()
            print("1:", response, file=output_file)
            response = bot2.respond(response).strip()
            print("2:", response, file=output_file)
            # If the robots have run out of things to say, force one of them
            # to break the ice.
            if response == "":
                response = "askquestion"
    finally:
        if close_output:
            output_file.close()
