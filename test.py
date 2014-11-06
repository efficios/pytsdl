import sys
import pytsdl.parser


if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        tsdl = f.read()

    parser = pytsdl.parser.Parser()
    doc = parser.parse(tsdl)

    print(doc.streams[1].event_header['id'].integer)
    print(doc.streams[1].packet_context['events_discarded'])
