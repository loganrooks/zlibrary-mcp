"""Stdlib-only launcher discriminator; never imported by product code.

The identification path and worker PID travel only over this synthetic child's
private stdout to the parent memory. The parent retains only fixed metadata.
Blocking command reads here are diagnostic-only, never the product pipe reader.
"""

import json
import os
import sys


def emit(value):
    print(json.dumps(value), flush=True)


def main():
    if sys.argv[1:] == ["identify"]:
        emit({"base": sys._base_executable})
        return
    if sys.argv[1:] != ["probe"]:
        raise ValueError()
    request = b'{"v":1,"type":"session_needed"}\n'
    written = os.write(4, request)
    os.close(4)
    emit(
        {
            "type": "ready",
            "version": list(sys.version_info[:3]),
            "pid": os.getpid(),
            "written": written,
            "closed": True,
        }
    )
    for _ in range(3):
        command = sys.stdin.readline(32)
        if command == "ping\n":
            emit({"type": "pong"})
        elif command == "finish\n":
            emit({"type": "finished"})
            return
        else:
            raise ValueError()
    raise ValueError()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never print exception text, repr, paths, arguments, handles or frames.
        emit({"type": "error"})
        sys.exit(1)
