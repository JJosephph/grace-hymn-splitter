from __future__ import annotations

import sys


def main() -> int:
    arguments = sys.argv[1:]
    if arguments and arguments[0] == "--cli":
        from hymn_splitter.cli import main as cli_main

        return cli_main(arguments[1:])
    if arguments and arguments[0] in {"build", "list", "inspect", "auto"}:
        from hymn_splitter.cli import main as cli_main

        return cli_main(arguments)

    from hymn_splitter.gui import main as gui_main

    gui_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
