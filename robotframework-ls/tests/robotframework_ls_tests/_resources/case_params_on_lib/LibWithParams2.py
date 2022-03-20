class LibWithParams2:
    def __init__(self, keyword_name):
        def method():
            return "method called"

        setattr(self, keyword_name, method)
