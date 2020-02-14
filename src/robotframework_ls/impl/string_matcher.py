class StringMatcher(object):
    def __init__(self, filter_text):
        self.filter_text = filter_text.lower()

    def accepts(self, word):
        if not self.filter_text:
            return True
        return self.filter_text in word.lower()
