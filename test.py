import sys
import pytsdl


if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        tsdl = f.read()

    parser = pytsdl.Parser()
    doc = parser.parse(tsdl)

    print(doc.trace)
    print(doc.env)

    for clock in doc.clocks:
        print(clock)

    for stream in doc.streams:
        print(stream)

    for event in doc.events:
        print(event)
