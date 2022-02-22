class _DummyToken(object):
    __slots__ = ["type", "value", "lineno", "col_offset", "end_col_offset"]

    def __init__(self, initial_token=None):
        if initial_token:
            self.type = initial_token.type
            self.value = initial_token.value
            self.lineno = initial_token.lineno
            self.col_offset = initial_token.col_offset
            self.end_col_offset = initial_token.end_col_offset
    
    def __sub__(self, preceding_token):
        token_difference =_DummyToken()
        token_difference.type = self.type
        preceding_token_length = preceding_token.end_col_offset - preceding_token.col_offset
        token_difference.value = self.value[preceding_token_length + 1 :]
        token_difference.lineno = self.lineno
        token_difference.col_offset = preceding_token.end_col_offset + 1
        token_difference.end_col_offset = self.end_col_offset
        return token_difference

def extract_gherkin_token_from_keyword(initial_token):
    gherkin_token = None
    import re
    result = re.match("^(Given|When|Then|And|But)", initial_token.value, flags=re.IGNORECASE)
    if result:
        gherkin_token = _DummyToken()
        gherkin_token.type = "control"
        gherkin_token.value = initial_token.value[:result.end()]
        gherkin_token.lineno = initial_token.lineno
        gherkin_token.col_offset = initial_token.col_offset
        gherkin_token.end_col_offset = initial_token.col_offset + len(gherkin_token.value)
    return gherkin_token

def extract_library_token_from_keyword(initial_token):
    library_token = None
    dot_pos = initial_token.value.rfind(".")
    if dot_pos > 0:
        library_token = _DummyToken()
        library_token.type = "name"
        library_token.value = initial_token.value[:dot_pos]
        library_token.lineno = initial_token.lineno
        library_token.col_offset = initial_token.col_offset
        library_token.end_col_offset = initial_token.col_offset + len(library_token.value)
    return library_token