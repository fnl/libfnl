#!/usr/bin/env python3
import fileinput

for line in fileinput.input():
    printed = set()

    for token in line.strip().split():
        if token not in printed:
            print(token)
            printed.add(token)