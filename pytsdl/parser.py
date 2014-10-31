import re
import pypeg2


class List:
    def __init__(self, elements):
        self._elements = elements

    def __iter__(self):
        for elem in self._elements:
            yield elem

    def __getitem__(self, i):
        return self._elements[i]


class SimpleValue:
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value

    def __str__(self):
        return str(self._value)


class LiteralString(SimpleValue):
    grammar = '"', re.compile(r'(\\.|[^"])*'), '"'

    def __init__(self, string):
        string = bytes(string, 'utf-8').decode('unicode_escape')
        super().__init__(string)


class ConstDecInteger(SimpleValue):
    grammar = re.compile(r'[0-9]+')

    def __init__(self, dec_str):
        super().__init__(int(dec_str))


class ConstOctInteger(SimpleValue):
    grammar = '0', re.compile(r'[0-9]+')

    def __init__(self, oct_str):
        super().__init__(int(oct_str, 8))


class ConstHexInteger(SimpleValue):
    grammar = pypeg2.contiguous(['0x', '0X'], re.compile(r'[0-9a-fA-F]+'))

    def __init__(self, hex_str):
        super().__init__(int(hex_str, 16))


class ConstInteger(SimpleValue):
    grammar = [ConstHexInteger, ConstOctInteger, ConstDecInteger]

    def __init__(self, integer):
        super().__init__(integer.value)


class ConstNumber(SimpleValue):
    grammar = ConstInteger

    def __init__(self, number):
        super().__init__(number.value)


class Identifier:
    grammar = re.compile(r'^(?!(?:struct|variant|enum|integer|floating_point|string))[A-Za-z_][A-Za-z_0-9]*')

    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

    def __str__(self):
        return '<id>{}</id>'.format(self._name)


class AlignAssignment(SimpleValue):
    grammar = 'align', '=', ConstInteger, ';'

    def __init__(self, integer):
        super().__init__(integer.value)


class SizeAssignment(SimpleValue):
    grammar = 'size', '=', ConstInteger, ';'

    def __init__(self, integer):
        super().__init__(integer.value)


class ByteOrder:
    NATIVE = 'native'
    BE = 'be'
    LE = 'le'


class ByteOrderAssignment(SimpleValue):
    grammar = 'byte_order', '=', re.compile(r'native|network|be|le'), ';'

    _byteOrderMap = {
        'native': ByteOrder.NATIVE,
        'be': ByteOrder.BE,
        'network': ByteOrder.BE,
        'le': ByteOrder.LE,
    }

    def __init__(self, align):
        super().__init__(ByteOrderAssignment._byteOrderMap[align])


class SignedAssignment(SimpleValue):
    grammar = 'signed', '=', re.compile(r'true|false'), ';'

    def __init__(self, signed):
        super().__init__(signed == 'true')


class BaseAssignment(SimpleValue):
    grammar = 'base', '=', [
        ConstInteger,
        re.compile(r'decimal|dec|d|i|u|hexadecimal|hex|x|X|p|octal|oct|o|binary|bin|b')
    ], ';'

    _baseMap = {
        'decimal': 10,
        'dec': 10,
        'd': 10,
        'i': 10,
        'u': 10,
        'hexadecimal': 16,
        'hex': 16,
        'x': 16,
        'X': 16,
        'p': 16,
        'octal': 8,
        'oct': 8,
        'o': 8,
        'binary': 2,
        'bin': 2,
        'b': 2,
    }

    def __init__(self, base):
        if type(base) is ConstInteger:
            value = base.value
        else:
            value = BaseAssignment._baseMap[base]

        super().__init__(value)


class Encoding:
    NONE = 'none'
    UTF8 = 'utf-8'
    ASCII = 'ascii'


class EncodingAssignment(SimpleValue):
    grammar = 'encoding', '=', re.compile(r'none|UTF8|ASCII'), ';'

    _encodingMap = {
        'none': Encoding.NONE,
        'UTF8': Encoding.UTF8,
        'ASCII': Encoding.ASCII,
    }

    def __init__(self, encoding):
        super().__init__(EncodingAssignment._encodingMap[encoding])


class Integer:
    grammar = 'integer', '{', pypeg2.some([
        SignedAssignment,
        ByteOrderAssignment,
        SizeAssignment,
        AlignAssignment,
        BaseAssignment,
        EncodingAssignment,
    ]), '}'

    def __init__(self, assignments):
        self._signed = False
        self._byte_order = ByteOrder.NATIVE
        self._base = 10
        self._encoding = Encoding.NONE
        self._align = None

        for a in assignments:
            if type(a) is SignedAssignment:
                self._signed = a.value
            elif type(a) is ByteOrderAssignment:
                self._byte_order = a.value
            elif type(a) is SizeAssignment:
                self._size = a.value
            elif type(a) is AlignAssignment:
                self._align = a.value
            elif type(a) is BaseAssignment:
                self._base = a.value
            elif type(a) is EncodingAssignment:
                self._encoding = a.value

        if self._align is None:
            if self._size % 8 == 0:
                self._align = 8
            else:
                self._align = 1

    @property
    def signed(self):
        return self._signed

    @property
    def byte_order(self):
        return self._byte_order

    @property
    def base(self):
        return self._base

    @property
    def encoding(self):
        return self._encoding

    @property
    def align(self):
        return self._align

    @property
    def size(self):
        return self._size

    def __str__(self):
        signed = 'signed="{}"'.format('true' if self._signed else 'false')
        byte_order = 'byte-order="{}"'.format(self._byte_order)
        base = 'base="{}"'.format(self._base)
        encoding = 'encoding="{}"'.format(self._encoding)
        align = 'align="{}"'.format(self._align)
        integer = '<integer {} {} {} {} {} />'.format(signed, byte_order, base,
                                                      encoding, align)

        return integer


class ExpDigAssignment(SimpleValue):
    grammar = 'exp_dig', '=', ConstInteger, ';'

    def __init__(self, exp_dig):
        super().__init__(exp_dig.value)


class MantDigAssignment(SimpleValue):
    grammar = 'mant_dig', '=', ConstInteger, ';'

    def __init__(self, mant_dig):
        super().__init__(mant_dig.value)


class FloatingPoint:
    grammar = 'floating_point', '{', pypeg2.some([
        ExpDigAssignment,
        MantDigAssignment,
        ByteOrderAssignment,
        AlignAssignment,
    ]), '}'

    def __init__(self, assignments):
        self._align = 1
        self._byte_order = ByteOrder.NATIVE

        for a in assignments:
            if type(a) is ExpDigAssignment:
                self._exp_dig = a.value
            elif type(a) is MantDigAssignment:
                self._mant_dig = a.value
            elif type(a) is ByteOrderAssignment:
                self._byte_order = a.value
            elif type(a) is AlignAssignment:
                self._align = a.value

    @property
    def exp_dig(self):
        return self._exp_dig

    @property
    def mant_dig(self):
        return self._mant_dig

    @property
    def byte_order(self):
        return self._byte_order

    @property
    def align(self):
        return self._align

    def __str__(self):
        exp_dig = 'exp-dig="{}"'.format(self._exp_dig)
        mant_dig = 'mant-dig="{}"'.format(self._mant_dig)
        byte_order = 'byte-order="{}"'.format(self._byte_order)
        align = 'align="{}"'.format(self._align)
        float = '<floating_point {} {} {} {} />'.format(exp_dig, mant_dig,
                                                        byte_order, align)

        return float


class String:
    grammar = (
        'string',
        pypeg2.optional((
            '{', EncodingAssignment, '}'
        ))
    )

    def __init__(self, encoding=None):
        self._encoding = Encoding.UTF8;

        if encoding is not None:
            self._encoding = encoding.value

    @property
    def encoding(self):
        return self._encoding

    def __str__(self):
        string = '<string encoding="{}" />'.format(self._encoding)

        return string


class Type:
    def __init__(self, t):
        if type(t) is Struct:
            self._type = t.struct
        elif type(t) is Variant:
            self._type = t.variant
        else:
            self._type = t

    @property
    def type(self):
        return self._type

    def __str__(self):
        return str(self._type)


class TypeAlias:
    grammar = 'typealias', Type, ':=', Identifier, ';'

    def __init__(self, args):
        self._type = args[0].type
        self._name = args[1].name

    @property
    def type(self):
        return self._type

    @property
    def name(self):
        return self._name

    def __str__(self):
        type = str(self._type)
        name = 'name="{}"'.format(self._name)

        return '<typealias {}>{}</typealias>'.format(name, type)


class EnumeratorValue:
    grammar = [Identifier, LiteralString], '=', ConstInteger

    def __init__(self, args):
        if type(args[0]) is Identifier:
            self._key = args[0].name
        else:
            self._key = args[0].value

        self._value = args[1].value

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        return self._value


class EnumeratorRange:
    grammar = [Identifier, LiteralString], '=', ConstInteger, '...', ConstInteger

    def __init__(self, args):
        if type(args[0]) is Identifier:
            self._key = args[0].name
        else:
            self._key = args[0].value

        self._low = args[1].value
        self._high = args[2].value

    @property
    def key(self):
        return self._key

    @property
    def low(self):
        return self._low

    @property
    def high(self):
        return self._high


class Enumerator:
    grammar = [
        EnumeratorRange,
        EnumeratorValue,
        Identifier,
        LiteralString,
    ]

    def __init__(self, assignment):
        if type(assignment) is Identifier:
            self._assignment = assignment.name
        elif type(assignment) is LiteralString:
            self._assignment = assignment.value
        else:
            self._assignment = assignment

    @property
    def assignment(self):
        return self._assignment


class Enumerators(List):
    grammar = pypeg2.csl(Enumerator), pypeg2.optional(',')

    def __init__(self, items):
        super().__init__([i.assignment for i in items])


class Enum:
    grammar = (
        'enum',
        pypeg2.optional(Identifier),
        ':',
        Identifier,
        '{',
        Enumerators,
        '}'
    )

    def __init__(self, args):
        self._name = None

        if len(args) == 3:
            self._name = args[0].name
            args.pop(0)

        self._int_type = args[0].name
        self._init_enum_labels(args[1])

    def _init_enum_labels(self, assignment_list):
        self._labels = {}
        cur = 0

        for a in assignment_list:
            if type(a) is str:
                self._labels[a] = (cur, cur)
                cur += 1
            elif type(a) is EnumeratorValue:
                self._labels[a.key] = (a.value, a.value)
                cur = a.value + 1
            elif type(a) is EnumeratorRange:
                self._labels[a.key] = (a.low, a.high)
                cur = a.high + 1

    @property
    def name(self):
        return self._name

    @property
    def int_type(self):
        return self._int_type

    @property
    def labels(self):
        return self._labels

    def __str__(self):
        name = ''

        if self._name is not None:
            name = 'name="{}"'.format(self._name)

        int_type = 'int-type="{}"'.format(self._int_type)
        labels = ''

        for key, value in self._labels.items():
            label_fmt = '<label name="{}" low="{}" high="{}" />'
            label = label_fmt.format(key, value[0], value[1])
            labels += label

        labels = '<labels>{}</labels>'.format(labels)

        return '<enum {} {}>{}</enum>'.format(name, int_type, labels)


class PostfixExpr(List):
    def __init__(self, elements):
        super().__init__(elements)

    def __str__(self):
        postfix_expr = '<postfix-expr>'

        for elem in self:
            postfix_expr += str(elem)

        postfix_expr += '</postfix-expr>'

        return postfix_expr


class UnaryExpr:
    def __init__(self, expr):
        if type(expr) is PrimaryExpr:
            self._expr = expr.expr
        else:
            self._expr = expr

    @property
    def expr(self):
        return self._expr

    def __str__(self):
        return str(self._expr)


class PrimaryExpr:
    def __init__(self, expr):
        if type(expr) is ConstNumber or type(expr) is LiteralString:
            self._expr = expr.value
        else:
            self._expr = expr

    @property
    def expr(self):
        return self._expr

    def __str__(self):
        return str(self._expr)


class UnaryExprSubscript:
    grammar = '[', UnaryExpr, ']'

    def __init__(self, expr):
        self._expr = expr.expr

    @property
    def expr(self):
        return self._expr

    def __str__(self):
        return '<subscript-expr>{}</subscript-expr>'.format(str(self._expr))


class Dot:
    grammar = re.compile(r'\.')

    def __init__(self, args):
        pass

    def __str__(self):
        return '<dot />'


class Arrow:
    grammar = re.compile(r'->')

    def __init__(self, args):
        pass

    def __str__(self):
        return '<arrow />'


PrimaryExpr.grammar = [
    Identifier,
    ConstNumber,
    LiteralString,
    ('(', UnaryExpr, ')'),
]


PostfixExpr.grammar = (
    Identifier,
    pypeg2.maybe_some(
        [
            (Arrow, Identifier),
            (Dot, Identifier),
            UnaryExprSubscript
        ]
    )
)


UnaryExpr.grammar = [
    PostfixExpr,
    PrimaryExpr,
]


class Declarator:
    grammar = (
        Identifier,
        pypeg2.maybe_some(UnaryExprSubscript)
    )

    def __init__(self, args):
        self._name = args[0].name
        self._subscripts = args[1:]

    @property
    def name(self):
        return self._name

    @property
    def subscripts(self):
        return self._subscripts

    def __str__(self):
        name = 'name="{}"'.format(self._name)
        decl = '<declarator {}><subscripts>'.format(name)

        for sub in self._subscripts:
            decl += str(sub)

        decl += '</subscripts></declarator>'

        return decl


class Field:
    grammar = (
        [Identifier, Type],
        Declarator,
        ';'
    )

    def __init__(self, args):
        self._type = args[0]
        self._decl = args[1]

    @property
    def type(self):
        return self._type

    @property
    def decl(self):
        return self._decl

    def __str__(self):
        type = '<type>{}</type>'.format(str(self._type))
        decl = str(self._decl)

        return '<field>{}{}</field>'.format(type, decl)


class StructEntries(List):
    grammar = pypeg2.maybe_some([Field, TypeAlias])

    def __init__(self, fields=[]):
        super().__init__(fields)


class StructRef:
    grammar = 'struct', Identifier

    def __init__(self, name):
        self._name = name.name

    @property
    def name(self):
        return self._name

    def __str__(self):
        return '<struct name="{}" />'.format(self._name)


class TypeWithEntries:
    def _set_entries(self, entries):
        self._entries = entries

    @property
    def entries(self):
        return self._entries

    @property
    def fields(self):
        return [f for f in self._entries if type(f) is Field]

    @property
    def typealiases(self):
        return [f for f in self._entries if type(f) is TypeAlias]

    def _get_entries_str(self):
        s = '<entries>'

        for e in self._entries:
            s += str(e)

        s += '</entries>'

        return s


class StructFull(TypeWithEntries):
    grammar = (
        'struct',
        pypeg2.optional(Identifier),
        '{', StructEntries, '}',
        pypeg2.optional(('align', '(', ConstInteger, ')'))
    )

    def __init__(self, args):
        self._name = None
        self._align = None

        if type(args[0]) is Identifier:
            self._name = args[0].name
            args.pop(0)

        self._set_entries(args[0])
        args.pop(0)

        if args:
            self._align = args[0].value

    @property
    def name(self):
        return self._name

    @property
    def align(self):
        return self._align

    def __str__(self):
        name = ''
        align = ''

        if self._name is not None:
            name = 'name="{}"'.format(self._name)

        if self._align is not None:
            align = 'align="{}"'.format(self._align)

        entries = self._get_entries_str()
        struct = '<struct {} {}>{}</struct>'.format(name, align, entries)

        return struct


class Struct:
    grammar = [StructFull, StructRef]

    def __init__(self, struct):
        self._struct = struct

    @property
    def struct(self):
        return self._struct

    def __str__(self):
        return str(self._struct)


class VariantRef:
    grammar = 'variant', Identifier, '<', UnaryExpr, '>'

    def __init__(self, args):
        self._name = args[0].name
        self._tag = args[1]

    @property
    def name(self):
        return self._name

    @property
    def tag(self):
        return self._tag

    def __str__(self):
        name = 'name="{}"'.format(self._name)
        variant = '<variant {}><tag>{}</tag></variant>'.format(name,
                                                               str(self._tag))

        return variant


class VariantFull(TypeWithEntries):
    grammar = (
        'variant',
        pypeg2.optional(Identifier),
        '<', UnaryExpr, '>',
        '{', StructEntries, '}'
    )

    def __init__(self, args):
        self._name = None

        if type(args[0]) is Identifier:
            self._name = args[0].name
            args.pop(0)

        self._tag = args[0]
        self._set_entries(args[1])

    @property
    def name(self):
        return self._name

    @property
    def tag(self):
        return self._tag

    def __str__(self):
        name = ''

        if self._name is not None:
            name = 'name="{}"'.format(self._name)

        entries = self._get_entries_str()
        fmt = '<variant {}><tag>{}</tag>{}</variant>'
        variant = fmt.format(name, str(self._tag), entries)

        return variant

class Variant:
    grammar = [VariantFull, VariantRef]

    def __init__(self, variant):
        self._variant = variant

    @property
    def variant(self):
        return self._variant

    def __str__(self):
        return str(self._variant)


Type.grammar = [Struct, Variant, Enum, Integer, FloatingPoint, String]


class ParseError(RuntimeError):
    def __init__(self, str):
        super().__init__(str)


class Parser:
    def parse(self, tsdl):
        try:
            ast = pypeg2.parse(tsdl, Type,
                               comment=[pypeg2.comment_c, pypeg2.comment_cpp])
        except (SyntaxError, Exception) as e:
            raise ParseError(str(e))

        return ast
