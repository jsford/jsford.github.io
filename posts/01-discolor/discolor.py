#!/usr/bin/env python3
import sys

def usage():
    print('discolor.py')
    print('Examples:')
    print('   discolor.py "FF00FF"')
    print('   discolor.py 255 0 255')
    print('   discolor.py 0.1 0.0 1.0')

if __name__=='__main__':
    r = 0.0; g = 0.0; b = 0.0;

    if len(sys.argv) == 2:
        hexcolor = sys.argv[1].strip('#')
        hexval = int(hexcolor, 16)
        r = int((hexval>>16) & 0xFF) / 255.0
        g = int((hexval>> 8) & 0xFF) / 255.0
        b = int((hexval>> 0) & 0xFF) / 255.0
    elif len(sys.argv) == 4:
        r = float(sys.argv[1])
        g = float(sys.argv[2])
        b = float(sys.argv[3])

        if r>1 or g>1 or b>1:
            r = r/255.0; g = g/255.0; b = b/255.0;
    else:
        usage()
        exit(0)

    R = int(255*r)
    G = int(255*g)
    B = int(255*b)

    print()
    print("\x1b[38;2;{};{};{}m\u2588\u2588\u2588\u2588\u2588\u2588\x1b[0m #{:02x}{:02x}{:02x}".format(R,G,B, R,G,B))
    print("\x1b[38;2;{};{};{}m\u2588\u2588\u2588\u2588\u2588\u2588\x1b[0m ({}, {}, {})".format(R,G,B, R,G,B))
    print("\x1b[38;2;{};{};{}m\u2588\u2588\u2588\u2588\u2588\u2588\x1b[0m ({:f}, {:f}, {:f})".format(R,G,B, r,g,b))
    print()
