import sys
import pytsdl.parser


if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        tsdl = f.read()

    parser = pytsdl.parser.Parser()
    doc = parser.parse(tsdl)

    print(doc.trace.major)
    print(doc.clocks)
