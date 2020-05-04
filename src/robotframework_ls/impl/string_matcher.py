from robotframework_ls.impl.text_utilities import (
    normalize_robot_name,
    matches_robot_keyword,
)


class RobotStringMatcher(object):
    def __init__(self, filter_text):
        self.filter_text = normalize_robot_name(filter_text)

    def accepts(self, word):
        if not self.filter_text:
            return True
        return self.filter_text in normalize_robot_name(word)

    def is_same_robot_name(self, word):
        return self.filter_text == normalize_robot_name(word)

    def is_keyword_name_match(self, keyword_name):
        normalized = normalize_robot_name(keyword_name)
        if self.filter_text == normalized:
            return True

        if "{" in normalized:
            return matches_robot_keyword(self.filter_text, normalized)

        return False
