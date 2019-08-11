Laundry list of future tasks, in no particular order:

 - AIML 1.0.1 compliance (highest priority):
   - Unknown yet well-defined elements (e.g. HTML) inside templates
     (see sections 3.2, 3.6).
   - `AimlParser._validateElemStart()` needs to test the well-formedness of
     attribute values (for example, making sure that the "index" attribute
     has an integer value, and not a string).  UPDATE: this works for 
     `<star>`, `<thatstar>` and `<topicstar>`.  Still needs to be written 
     for `<input>` and `<that>`, which take either an integer or an integer 
     pair.
 - Support the Program D startup file syntax, or something similar?  It
   seems to be a good way to initialize bot settings and substitutions.
 - Documentation/tutorials.
 - Compare pattern manager to [pygtree](https://github.com/google/pygtrie) and 
   look for opportunities to improve (or replace) it.
 - Add reinforcement learning mechanisms wherever arbitrary choices are made,
   e.g. the `<random>` tag.
