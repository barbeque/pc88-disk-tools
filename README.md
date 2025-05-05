# pc88-disk-tools
This repository contains some tools for working with NEC PC-8801 disk images, and more specifically the D88 image format that is used extensively by emulators.

## The D88 image format
Everything I know about this format comes from [the D88STRUC.TXT document](https://illusioncity.net/PC88/D88STRUC.txt). I am grateful for your hard work documenting this format.

## d88.py
This is the "Swiss army knife" script for dealing with common problems surrounding d88 disk images. It is likely to be lacking features and support for certain oddball kinds of disk images – I add features to it when I need them.

The script provides help with the `--help` option, but here is a short list of available modes:

| Mode | Does what? | Example usage |
|------|------------|---------------|
| `info` | Attempts to analyze a disk image and print out the contents of common D88 headers. Can sometimes detect when a disk image is _not_ a D88, too. | `python3 d88.py --info foobar.d88` |
| `boot-dump` | Dumps the initial sector of the disk, assuming it is a PC-8801 disk image. You can easily feed the resulting dumped sector through z80dasm using `pc88-dasm.sh` | `python3 d88.py --dump foobar.d88 --output foobar.bin` |
| `rename` | Rename the "friendly" label of the D88. This does not rename the actual disk label of any partition on the disk. | `python3 d88.py --rename=barfoo foobar.d88 --output=barfoo.d88` |
| `flatten` | Attempts to convert a D88 into a flat image, which is sometimes helpful for use with a Gotek. It will almost never work with an emulator, or with the HxC utility without doing "load raw image" with appropriate options. | `python3 d88.py --flatten foobar.d88 --output foobar.img` |
| `1d` | Attempts to change the D88's "type" byte to one for a low-density 1-sided disk image. Does not modify any of the data of the disk image. | `python3 d88.py --1d foobar.d88 --output foobar-1d.d88` |
| `1dd` | Attempts to change the D88's "type" byte to one for a double-density 1-sided disk image. Does not modify any of the data of the disk image. | `python3 d88.py --1dd foobar.d88 --output foobar-1dd.d88` |