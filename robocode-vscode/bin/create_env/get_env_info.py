if __name__ == "__main__":
    import sys
    import json

    try:
        import robot

        robot_version = robot.__version__
    except:
        robot_version = "N/A"

    info = {
        "python_executable": sys.executable,
        "python_version": tuple(sys.version_info),
        "robot_version": robot_version,
    }
    sys.stdout.write(json.dumps(info, indent=4))
    sys.stdout.flush()
