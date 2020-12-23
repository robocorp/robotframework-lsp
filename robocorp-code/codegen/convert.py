def convert_case_to_constant(name):
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return (
        re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
        .replace(".", "_")
        .replace("-", "_")
        .upper()
    )


def convert_case_to_camel(name):
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return (
        re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
        .replace(".", "_")
        .replace("-", "_")
        .upper()
    )
