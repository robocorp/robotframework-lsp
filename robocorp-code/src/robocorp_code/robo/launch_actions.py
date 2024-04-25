import sys


def main():
    cli = None
    try:
        from sema4ai.actions import cli  # noqa #type: ignore
    except ImportError:
        try:
            # Backward compatibility
            from robocorp.actions import cli  # noqa #type: ignore
        except ImportError:
            pass

        if cli is None:
            raise  # Raise the sema4ai.actions error

    return cli.main(sys.argv[1:], exit=True)


if __name__ == "__main__":
    main()
