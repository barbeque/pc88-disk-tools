#!/bin/bash
# Shortcut script to wrap z80dasm to help disassemble PC88 boot sectors
z80dasm -lt --origin=0xc000 $1
