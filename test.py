import sys
from pytsdl import Parser


parser = Parser()

with open(sys.argv[1]) as f:
    doc = parser.parse(f.read())

