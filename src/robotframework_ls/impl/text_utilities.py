class TextUtilities(object):
    def __init__(self, text):
        self.text = text

    def strip_leading_chars(self, c):
        if len(c) != 1:
            raise AssertionError('Expected "%s" to have size == 1' % (c,))
        text = self.text
        if len(text) == 0 or text[0] != c:
            return False
        for i, text_c in enumerate(text):
            if text_c != c:
                self.text = self.text[i:]
                return True

        else:
            # Consumed all chars
            self.text = ""
            return True

    def strip(self):
        self.text = self.text.strip()


def normalize_robot_name(text):
    return text.lower().replace("_", " ")


def matches_robot_keyword(keyword_name_call_text, keyword_name, _re_cache={}):
    """
    Checks if a given text matches a given keyword. 
    
    Note: both should be already normalized.
    Note: should NOT be called if keyword does not have '{' in it.
    
    :param keyword_name_call_text:
        The call that has resolved variables.
        
    :param keyword_name:
        The keyword (which has variables -- i.e.: '{').
    """
    try:
        compiled = _re_cache[keyword_name]
    except KeyError:
        from robot.api import Token
        import re

        regexp = []
        for t in Token(Token.KEYWORD_NAME, keyword_name).tokenize_variables():
            if t.type == t.VARIABLE:
                regexp.append("(.*)")
            else:
                regexp.append(re.escape(t.value))

        regexp.append("$")

        regexp = "".join(regexp)
        _re_cache[keyword_name] = re.compile(regexp)
        compiled = _re_cache[keyword_name]

    return compiled.match(keyword_name_call_text)
