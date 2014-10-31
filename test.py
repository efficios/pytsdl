import sys
import pytsdl


if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        tsdl = f.read()

    parser = pytsdl.Parser()
    ast = parser.parse(tsdl)

    print(ast)
