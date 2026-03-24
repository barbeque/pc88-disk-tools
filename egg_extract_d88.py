#!/usr/bin/env python3

import os, sys


def egg_extract_d88(*, dmpname):
    """
    extract every piece of a process memory dump file that looks like a reasonable-sized d88 formatted floppy disk image. the results will be written to disk_0.d88, disk_1.d88, etc. - deleting and replacing any existing files with those names
    """
    dmp = open(dmpname, "rb").read()
    i = 0
    n = 0
    while i < len(dmp):
        j = sorted(
            [
                dmp[i + 0x20 :].find((hsz).to_bytes(4, "little")) + i
                for hsz in (672, 688)
            ]
        )
        i = ([jj for jj in j if jj >= i] + [-1])[0]
        if i == -1:
            break
        d88 = dmp[i : i + 3 * 1024 * 1024]
        sz = int.from_bytes(d88[0x1C:0x20] + b"\0", "little")
        if (
            sz < len(d88)
            and sz > 672
            and d88[int.from_bytes(d88[0x20:0x24], "little") :][:3] == b"\0\0\1"
            and set(
                [
                    int.from_bytes(d88[i : i + 4], "little")
                    in {0, 0xFFFFFFFF, sz}
                    | set(range(int.from_bytes(d88[i : i + 4], "little"), sz))
                    for i in range(0x20, int.from_bytes(d88[0x20:0x24], "little"), 4)
                ]
            )
            == {True}
        ):
            d88 = d88[:sz]
            f = f"disk_{n}.d88"
            if os.path.exists(f):
                print(f"removing previous {f}")
                os.unlink(f)
            n += 1
            print(f"writing {f}")
            open(f, "wb").write(d88)
            i += sz
        else:
            i += 1


if __name__ == "__main__":
    _, dmpname = sys.argv  # usage: python3 egg_extract_d88.py EXENAME.DMP
    egg_extract_d88(dmpname=dmpname)
