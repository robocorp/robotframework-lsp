class RobotStringMatcher(object):
    def __init__(self, filter_text):
        self.filter_text = filter_text.lower().replace("_", " ")

    def accepts(self, word):
        if not self.filter_text:
            return True
        return self.filter_text in word.lower().replace("_", " ")

    def is_same_robot_name(self, word):
        return self.filter_text == word.lower().replace("_", " ")
