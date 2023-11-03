if __name__ == "__main__":
    import json
    import os
    import sys

    try:
        import robot

        robot_version = robot.__version__
    except:
        robot_version = "N/A"

    info = {
        "python_executable": sys.executable,
        "python_version": tuple(sys.version_info),
        "robot_version": robot_version,
        "environment": dict(os.environ),
    }
    json_contents = json.dumps(info, indent=4)
    sys.stderr.write("JSON START>>")
    sys.stderr.write(json_contents)
    sys.stderr.write("<<JSON END")
    sys.stderr.flush()
