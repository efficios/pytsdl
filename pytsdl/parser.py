import enum
import re
import copy
import uuid
import pypeg2
import pytsdl.tsdl


class _List:
    def __init__(self, elements):
        self._elements = elements

    @property
    def elements(self):
        return self._elements

    def __iter__(self):
        for elem in self._elements:
            yield elem

    def __getitem__(self, i):
        return self._elements[i]

    def __str__(self):
        # this is normally never exposed
        raise RuntimeError()


class _SingleValue:
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value

    def __str__(self):
        # this is normally never exposed
        raise RuntimeError()


class Node:
    def accept(self, visitor):
        method = 'visit_{}'.format(self.__class__.__name__)

        if hasattr(visitor, method):
            return getattr(visitor, method)(self)

        return visitor.visit(self)

    def is_scope(self):
        return isinstance(self, Scope)


# examples:
#
#   "hello"
#   "he\tll\x3b;o\n"
class LiteralString(_SingleValue, Node):
    grammar = '"', re.compile(r'(\\.|[^"])*'), '"'

    def __init__(self, string):
        string = bytes(string, 'utf-8').decode('unicode_escape')
        super().__init__(string)

    def __str__(self):
        return '<literal-string>{}</literal-string>'.format(self.value)


# examples:
#
#   12
#   934
class ConstDecInteger(_SingleValue):
    grammar = re.compile(r'[0-9]+')

    def __init__(self, dec_str):
        super().__init__(int(dec_str))


# examples:
#
#   023
#   0177
class ConstOctInteger(_SingleValue):
    grammar = '0', re.compile(r'[0-9]+')

    def __init__(self, oct_str):
        super().__init__(int(oct_str, 8))


# examples:
#
#   0x3b
#   0xCAFE
#   0XbAbE1
class ConstHexInteger(_SingleValue):
    grammar = pypeg2.contiguous(['0x', '0X'], re.compile(r'[0-9a-fA-F]+'))

    def __init__(self, hex_str):
        super().__init__(int(hex_str, 16))


# examples:
#
#   12
#   934
#   023
#   0177
#   0x3b
#   0xCAFE
#   0XbAbE1
class ConstInteger(_SingleValue):
    grammar = [ConstHexInteger, ConstOctInteger, ConstDecInteger]

    def __init__(self, integer):
        super().__init__(integer.value)

    def __str__(self):
        return '<const-int>{}</const-int>'.format(self.value)


# examples:
#
#   12
#   -934
#   023
#   -0177
#   +0x3b
#   -0xCAFE
#   0XbAbE1
class ConstNumber(_SingleValue, Node):
    grammar = pypeg2.optional(re.compile(r'[+-]')), ConstInteger

    def __init__(self, args):
        mul = 1;

        if len(args) == 2:
            if args[0] == '-':
                mul = -1

            args.pop(0)

        super().__init__(args[0].value * mul)

    def __str__(self):
        return '<const-number>{}</const-number>'.format(self.value)


# examples:
#
#   hello
#   _field_name
#   Bob42
class Identifier(_SingleValue, Node):
    grammar = re.compile(r'^(?!(?:struct|variant|enum|integer|floating_point|string|typealias))[A-Za-z_][A-Za-z_0-9]*')

    def __init__(self, name):
        super().__init__(name)

    def __str__(self):
        return '<id>{}</id>'.format(self.value)


class PostfixExpr(_List, Node):
    def __init__(self, elements):
        super().__init__(elements)

    def __str__(self):
        postfix_expr = '<postfix-expr>'

        for elem in self:
            postfix_expr += str(elem)

        postfix_expr += '</postfix-expr>'

        return postfix_expr


class UnaryExpr(Node):
    def __init__(self, expr):
        if type(expr) is PrimaryExpr:
            self._expr = expr.expr
        else:
            self._expr = expr

    @property
    def expr(self):
        return self._expr

    def __str__(self):
        return '<unary-expr>{}</unary-expr>'.format(str(self._expr))


class PrimaryExpr(Node):
    def __init__(self, expr):
        self._expr = expr

    @property
    def expr(self):
        return self._expr

    def __str__(self):
        return '<primary-expr>{}</primary-expr>'.format(str(self._expr))


class UnaryExprSubscript(Node):
    grammar = '[', UnaryExpr, ']'

    def __init__(self, expr):
        self._expr = expr.expr

    @property
    def expr(self):
        return self._expr

    def __str__(self):
        return '<subscript-expr>{}</subscript-expr>'.format(str(self._expr))


# examples:
#
#   key = identifier
#   key = "string"
#   key = 0x17
#   key = -02131
class ValueAssignment(Node):
    grammar = Identifier, '=', UnaryExpr

    def __init__(self, args):
        self._key = args[0]
        self._value = args[1]

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        return self._value

    def __str__(self):
        return '<value-assign>{}{}</value-assign>'.format(str(self._key),
                                                          str(self._value))


# examples:
#
#   integer {
#       size = 8;
#       align = 8;
#       signed = true;
#       byte_order = native;
#       map = clock.monotonic.value;
#       encoding = ASCII;
#       base = oct;
#   }
#
#   integer {size = 13;}
class Integer(_List, Node):
    grammar = 'integer', '{', pypeg2.some((ValueAssignment, ';')), '}'

    def __init__(self, assignments):
        super().__init__(assignments)

    def __str__(self):
        integer = '<integer>'

        for a in self:
            integer += str(a)

        integer += '</integer>'

        return integer


# examples:
#
#   floating_point {
#       exp_dig = 3;
#       mant_dig = 0x1b;
#       byte_order = native;
#       align = 2;
#   }
#
#   floating_point {exp_dig = 2; mant_dig = 18;}
class FloatingPoint(_List, Node):
    grammar = 'floating_point', '{', pypeg2.some((ValueAssignment, ';')), '}'

    def __init__(self, assignments):
        super().__init__(assignments)

    def __str__(self):
        float = '<floating-point>'

        for a in self:
            float += str(a)

        float += '</floating-point>'

        return float


# examples:
#
#   string
#
#   string {
#       encoding = ASCII;
#   }
class String(_SingleValue, Node):
    grammar = (
        'string',
        pypeg2.optional((
            '{', ValueAssignment, ';', '}'
        ))
    )

    def __init__(self, encoding=None):
        super().__init__(encoding)

    def __str__(self):
        string = '<string>'

        if self.value is not None:
            string += str(self.value)

        string += '</string>'

        return string


class Type(_SingleValue, Node):
    def __init__(self, t):
        if type(t) is Struct:
            t = t.value
        elif type(t) is Variant:
            t = t.value

        super().__init__(t)


# examples:
#
#   typealias integer {
#       size = 64;
#       align = 8;
#       signed = false;
#   } := unsigned long;
#
#   typealias string := zok;
#
#   typealias enum bouh : unsigned long long {
#       ZERO,
#       ONE,
#       TWO,
#       TEN = 10,
#       ELEVEN,
#   } := the_great_enum;
class TypeAlias(Node):
    grammar = 'typealias', Type, ':=', pypeg2.some(Identifier)

    def __init__(self, args):
        self._type = args[0].value
        args.pop(0)

        # may contain spaces -> not really an identifier; still simpler
        self._name = Identifier(' '.join([id.value for id in args]))

    @property
    def type(self):
        return self._type

    @property
    def name(self):
        return self._name

    def __str__(self):
        return '<typealias>{}{}</typealias>'.format(str(self._type),
                                                    str(self._name))


# examples:
#
#   LABEL = 23
#   "some string" = 42
class EnumeratorValue(Node):
    grammar = [Identifier, LiteralString], '=', ConstInteger

    def __init__(self, args):
        self._key = args[0]
        self._value = args[1]

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        return self._value

    def __str__(self):
        return '<enum-value>{}{}</enum-value>'.format(str(self._key),
                                                      str(self._value))


# examples:
#
#   23 ... 102
#   1...7
#   -53 ... 747
class ConstNumberRange(Node):
    # eventually replace ConstNumber by ConstInteger here
    grammar = ConstNumber, '...', ConstNumber

    def __init__(self, args):
        self._low = args[0]
        self._high = args[1]

    @property
    def low(self):
        return self._low

    @property
    def high(self):
        return self._high

    def __str__(self):
        fmt = '<const-int-range>{}{}</const-int-range>'

        return fmt.format(str(self._low), str(self._high))


# examples:
#
#   LABEL = 23 ... 102
#   "some string" = -53...747
class EnumeratorRange(Node):
    grammar = [Identifier, LiteralString], '=', ConstNumberRange

    def __init__(self, args):
        self._key = args[0]
        self._range = args[1]

    @property
    def key(self):
        return self._key

    @property
    def range(self):
        return self._range

    def __str__(self):
        return '<enum-range>{}{}</enum-range>'.format(str(self._key),
                                                      str(self._range))


# examples:
#
#   LABEL
#   "some string"
#   LABEL = 23
#   "some string" = 42
#   LABEL = 23 ... 102
#   "some string" = -53...747
class Enumerator(_SingleValue, Node):
    grammar = [
        EnumeratorRange,
        EnumeratorValue,
        Identifier,
        LiteralString,
    ]

    def __init__(self, enumerator):
        super().__init__(enumerator)

    def __str__(self):
        return '<enumerator>{}{}</enumerator>'.format(str(self.value))


# examples:
#
#   LABEL, LABEL2 = 23, "some label" = 1...18,
class Enumerators(_List, Node):
    grammar = pypeg2.csl(Enumerator), pypeg2.optional(',')

    def __init__(self, items):
        super().__init__([i.value for i in items])

    def __str__(self):
        s = '<enumerators>'

        for e in self:
            s += str(e)

        s += '</enumerators>'

        return s


class EnumName(_SingleValue):
    grammar = Identifier

    def __init__(self, name):
        super().__init__(name)

    def __str__(self):
        # this is normally never exposed
        raise RuntimeError()

# examples:
#
#   enum my_enum : my_int {
#       ONE,
#       TWO,
#       THREE,
#       FOUR,
#       TEN = 10,
#       ELEVEN,
#       RANGE = 67 ... 85,
#       EIGHTY_SIX,
#       HUNDRED = 100,
#   }
#
#   enum : my_int {
#       STATE1,
#       STATE2
#   }
class Enum(Node):
    grammar = (
        'enum',
        pypeg2.optional(EnumName),
        ':',
        pypeg2.some(Identifier),
        '{',
        Enumerators,
        '}'
    )

    def __init__(self, args):
        self._name = None

        if type(args[0]) is EnumName:
            self._name = args[0].value
            args.pop(0)

        self._int_type = Identifier(' '.join([i.value for i in args[0:-1]]))
        self._enumerators = args[-1]

    @property
    def name(self):
        return self._name

    @property
    def int_type(self):
        return self._int_type

    @int_type.setter
    def int_type(self, int_type):
        self._int_type = int_type

    @property
    def enumerators(self):
        return self._enumerators

    def __str__(self):
        enum = '<enum>'

        if self._name is not None:
            enum += str(self._name)

        enum += str(self._int_type)
        enum += str(self._enumerators)
        enum += '</enum>'

        return enum


class Dot(Node):
    grammar = '.'

    def __init__(self):
        pass

    def __str__(self):
        return '<dot />'


class Arrow(Node):
    grammar = '->'

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


class Declarator(Node):
    def __init__(self, name, subscripts):
        self._name = name
        self._subscripts = subscripts

    @property
    def name(self):
        return self._name

    @property
    def subscripts(self):
        return self._subscripts

    def __str__(self):
        decl = '<decl>{}'.format(str(self._name))

        for s in self._subscripts:
            decl += str(s)

        decl += '</decl>'

        return decl


# examples:
#
#   integer {size = 23;} my_field
#
#   string my_field[101]
#
#   struct hello {
#       int a;
#       unsigned long b;
#   } my_field[ref][42]
#
#   variant some_variant_ref <tag_ref> my_field
class TypeField(Node):
    grammar = Type, Identifier, pypeg2.maybe_some(UnaryExprSubscript)

    def __init__(self, args):
        self._type = args[0].value
        args.pop(0)
        decl_name = args[0]
        args.pop(0)
        self._decl = Declarator(decl_name, args)

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, type):
        self._type = type

    @property
    def decl(self):
        return self._decl

    def __str__(self):
        return '<type-field>{}{}</type-field>'.format(str(self._type),
                                                      str(self._decl))


# examples:
#
#   my_alias my_field
#   int my_field[3]
#   unsigned long my_field[other_field]
#   int a[1][2][a][b][c]
class IdentifierField(Node):
    # Here's the hackish way to parse fields like:
    #
    #   int a
    #   int a[23]
    #   unsigned long b
    #   unsigned long b[23]
    #
    # We scan for identifiers and assume the last one is the declarator
    # name, not part of the type alias. Then come subscripts.
    grammar = pypeg2.some(Identifier), pypeg2.maybe_some(UnaryExprSubscript)

    def __init__(self, args):
        self._type = []
        subscripts = []

        for a in args:
            if type(a) is Identifier:
                self._type.append(a.value)
            elif type(a) is UnaryExprSubscript:
                subscripts.append(a)

        decl_name = self._type.pop()
        self._decl = Declarator(Identifier(decl_name), subscripts)

        # may contain spaces -> not really an identifier; still simpler
        self._type = Identifier(' '.join(self._type))

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, type):
        self._type = type

    @property
    def decl(self):
        return self._decl

    def __str__(self):
        return '<id-field>{}{}</id-field>'.format(str(self._type),
                                                  str(self._decl))


class Field(_SingleValue, Node):
    grammar = [TypeField, IdentifierField]

    def __init__(self, field):
        super().__init__(field)

    def __str__(self):
        # this is normally never exposed
        raise RuntimeError()


class StructVariantEntries(_List):
    def __init__(self, fields=[]):
        for i in range(len(fields)):
            if type(fields[i]) is Field:
                fields[i] = fields[i].value

        super().__init__(fields)

    def __str__(self):
        # this is normally never exposed
        raise RuntimeError()


# examples:
#
#   struct hello
#   struct sweet
class StructRef(_SingleValue, Node):
    grammar = 'struct', Identifier

    def __init__(self, name):
        super().__init__(name)

    def __str__(self):
        return '<struct-ref>{}</struct-ref>'.format(str(self.value))


# examples:
#
#   align(8)
#   align(0x20)
class StructAlign(_SingleValue, Node):
    grammar = 'align', '(', ConstInteger, ')'

    def __init__(self, align):
        super().__init__(align)

    def __str__(self):
        return '<struct-align>{}</struct-align>'.format(str(self.value))


class Scope(Node):
    def __init__(self, entries):
        self._entries = entries

    @property
    def entries(self):
        return self._entries


# examples:
#
#   struct named {
#       int a;
#       int b[23];
#   }
#
#   struct {
#       int a;
#       int b[23];
#   } align(8)
#
#   struct yeah {
#       float a[c];
#       int z;
#   } align(0x10)
class StructFull(Scope):
    grammar = (
        'struct',
        pypeg2.optional(Identifier),
        '{', StructVariantEntries, '}',
        pypeg2.optional(StructAlign)
    )

    def __init__(self, args):
        self._name = None
        self._align = None

        if type(args[0]) is Identifier:
            self._name = args[0]
            args.pop(0)

        super().__init__(args[0].elements)
        args.pop(0)

        if args:
            self._align = args[0]

    @property
    def name(self):
        return self._name

    @property
    def align(self):
        return self._align

    def __str__(self):
        struct = '<struct-full>'

        if self._name is not None:
            struct += str(self._name)

        for e in self.entries:
            struct += str(e)

        if self._align is not None:
            struct += str(self._align)

        struct += '</struct-full>'

        return struct


class Struct(_SingleValue):
    grammar = [StructFull, StructRef]

    def __init__(self, struct):
        super().__init__(struct)

    def __str__(self):
        # this is normally never exposed
        raise RuntimeError()


# examples:
#
#   <field>
#   <packet.context.some_field>
class VariantTag(_SingleValue, Node):
    grammar = '<', UnaryExpr, '>'

    def __init__(self, expr):
        super().__init__(expr)

    def __str__(self):
        return '<tag>{}</tag>'.format(str(self.value))


# examples:
#
#   variant name <field>
#   variant name <packet.context.some_field>
class VariantRef(Node):
    grammar = 'variant', Identifier, VariantTag

    def __init__(self, args):
        self._name = args[0]
        self._tag = args[1]

    @property
    def name(self):
        return self._name

    @property
    def tag(self):
        return self._tag

    def __str__(self):
        return '<variant-ref>{}{}</variant-ref>'.format(str(self._name),
                                                        str(self._tag))


# examples:
#
#   variant named <field> {
#       int a;
#       unsigned long b;
#       struct yeah c[17];
#   }
#
#   variant <packet.context.some_field> {
#       int a;
#       unsigned long b;
#       struct yeah c[17];
#   }
class VariantFull(Scope, Node):
    grammar = (
        'variant',
        pypeg2.optional(Identifier),
        pypeg2.optional(VariantTag),
        '{', StructVariantEntries, '}'
    )

    def __init__(self, args):
        self._name = None
        self._tag = None

        if type(args[0]) is Identifier:
            self._name = args[0]
            args.pop(0)

        if type(args[0]) is VariantTag:
            self._tag = args[0]
            args.pop(0)

        super().__init__(args[0])

    @property
    def name(self):
        return self._name

    @property
    def tag(self):
        return self._tag

    @tag.setter
    def tag(self, tag):
        self._tag = tag

    def __str__(self):
        variant = '<variant-full>'

        if self._name is not None:
            variant += str(self._name)

        if self._tag is not None:
            variant += str(self._tag)

        for e in self.entries:
            variant += str(e)

        variant += '</variant-full>'

        return variant


class Variant(_SingleValue):
    grammar = [VariantFull, VariantRef]

    def __init__(self, variant):
        super().__init__(variant)

    def __str__(self):
        # this is normally never exposed
        raise RuntimeError()


# examples:
#
#   key := struct yeah
#
#   key := some_alias
#
#   key := struct {
#       int a;
#       int b[17];
#   }
#
#   packet.header := struct {
#       uint32_t magic;
#       uint8_t  uuid[16];
#       uint32_t stream_id;
#   }
class TypeAssignment(Node):
    grammar = UnaryExpr, ':=', Type

    def __init__(self, args):
        self._key = args[0]
        self._type = args[1].value

    @property
    def key(self):
        return self._key

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, type):
        self._type = type

    def __str__(self):
        return '<type-assign>{}{}</type-assign>'.format(str(self._key),
                                                        str(self._type))


_common_scope_entries = [
    TypeAlias,
    StructFull,
    VariantFull,
]


_scope_entries = pypeg2.maybe_some((
    [ValueAssignment, TypeAssignment] + _common_scope_entries,
    ';'
))


StructVariantEntries.grammar = pypeg2.maybe_some((
    [Field] + _common_scope_entries,
    ';'
))


Type.grammar = [Struct, Variant, Enum, Integer, FloatingPoint, String]


class TopLevelScope(Scope):
    @staticmethod
    def _create_scope(clsname, scope_name):
        return type(clsname, (TopLevelScope, Node, object), {
            'grammar': (scope_name, '{', _scope_entries, '}'),
            '_scope_name': scope_name
        })

    def __init__(self, entries=[]):
        super().__init__(entries)

    def __str__(self):
        entries = ''
        for e in self.entries:
            entries += str(e)

        s = '<{sn}>{e}</{sn}>'.format(sn=self._scope_name, e=entries)

        return s


Env = TopLevelScope._create_scope('Env', 'env')
Trace = TopLevelScope._create_scope('Trace', 'trace')
Clock = TopLevelScope._create_scope('Clock', 'clock')
Stream = TopLevelScope._create_scope('Stream', 'stream')
Event = TopLevelScope._create_scope('Event', 'event')
Top = TopLevelScope._create_scope('Top', 'top')


Top.grammar = pypeg2.maybe_some((
    [Env, Trace, Clock, Stream, Event] + _common_scope_entries, ';'
))


class ParseError(RuntimeError):
    def __init__(self, str):
        super().__init__(str)


class _TypeResolverVisitor:
    def __init__(self):
        self._reset_state()

    def _reset_state(self):
        self._scope_stores = []

    def _get_cur_scope_store(self):
        return self._scope_stores[-1]

    def _push_scope_store(self):
        self._scope_stores.append({})

    def _pop_scope_store(self):
        return self._scope_stores.pop()

    def _store(self, prefix, name, node):
        ss = self._get_cur_scope_store()
        ss[prefix + name] = node

    def _resolve(self, prefix, name):
        search = prefix + name

        for ss in reversed(self._scope_stores):
            if search in ss:
                return ss[search]

        reftype = {
            'a': 'alias',
            's': 'struct',
            'v': 'variant',
        }

        raise ParseError('cannot resolve {}: {}'.format(reftype[prefix], name))

    def _store_alias(self, name, node):
        self._store('a', name, node)

    def _resolve_alias(self, name):
        return self._resolve('a', name)

    def _store_struct(self, name, node):
        self._store('s', name, node)

    def _resolve_struct(self, name):
        return self._resolve('s', name)

    def _store_variant(self, name, node):
        self._store('v', name, node)

    def _resolve_variant(self, name):
        return self._resolve('v', name)

    def _visit_scope(self, node):
        self._push_scope_store()

        for entry in node.entries:
            entry.accept(self)

        self._pop_scope_store()

    def visit(self, node):
        if node.is_scope():
            self._visit_scope(node)

    def visit_Top(self, node):
        self._reset_state()

        self._visit_scope(node)

    def visit_TypeAlias(self, node):
        self._store_alias(node.name.value, node.type)

    def visit_StructFull(self, node):
        if node.name is not None:
            self._store_struct(node.name.value, node)

        self._visit_scope(node)

    def visit_VariantFull(self, node):
        if node.name is not None:
            self._store_variant(node.name.value, node)

        self._visit_scope(node)

    def _visit_field_typeassignment(self, node):
        field_type = node.type

        if field_type.is_scope():
            field_type.accept(self)
        else:
            if type(field_type) is StructRef:
                node.type = self._resolve_struct(field_type.value.value)
            elif type(field_type) is VariantRef:
                variant = self._resolve_variant(field_type.value.value)
                variant_copy = copy.deepcopy(variant)
                variant_copy.tag = field_type.tag
                node.type = variant_copy
            elif type(field_type) is Identifier:
                node.type = self._resolve_alias(field_type.value)
            elif type(field_type) is Enum:
                int_type = field_type.int_type
                field_type.int_type = self._resolve_alias(int_type.value)

    def visit_IdentifierField(self, node):
        self._visit_field_typeassignment(node)

    def visit_TypeField(self, node):
        self._visit_field_typeassignment(node)

    def visit_TypeAssignment(self, node):
        self._visit_field_typeassignment(node)


class _DocCreatorVisitor:
    _byte_order_map = {
        'le': pytsdl.tsdl.ByteOrder.LE,
        'be': pytsdl.tsdl.ByteOrder.BE,
        'network': pytsdl.tsdl.ByteOrder.BE,
        'native': pytsdl.tsdl.ByteOrder.NATIVE,
    }

    def __init__(self):
        self._value_assignment_map = {
            pytsdl.tsdl.Trace: self._value_assign_trace,
            pytsdl.tsdl.Env: self._value_assign_env,
            pytsdl.tsdl.Clock: self._value_assign_clock,
            pytsdl.tsdl.Stream: self._value_assign_stream,
            pytsdl.tsdl.Event: self._value_assign_event,
        }

        self._reset_state()

    @staticmethod
    def _to_bool(s):
        sl = s.lower()

        if not re.match(r'true|false|1|0', sl):
            raise ParseError('wrong boolean: {}'.format(sl))


        return sl == 'true' or sl == '1'

    def _reset_state(self):
        self._objs = []

    def _get_cur_obj(self):
        return self._objs[-1]

    def _push_obj(self, obj):
        self._objs.append(obj)

    def _pop_obj(self):
        return self._objs.pop()

    def _visit_scope(self, node, obj):
        self._push_obj(obj)

        for entry in node.entries:
            entry.accept(self)

        return self._pop_obj()

    def visit(self, node):
        pass

    def visit_Top(self, node):
        self._reset_state()
        self._doc = self._visit_scope(node, pytsdl.tsdl.Doc())

        if not self._doc.clocks:
            raise ParseError('no clocks defined')

        if not self._doc.streams:
            raise ParseError('no streams defined')

        cnames = set()

        for c in self._doc.clocks:
            if c.name in cnames:
                raise ParseError('duplicate clock: {}'.format(c.name))

            cnames.add(c.name)

        sids = set()

        for s in self._doc.streams:
            if s.id in sids:
                raise ParseError('duplicate stream: {}'.format(s.id))

            sids.add(s.id)

            enames = set()
            eids = set()

            for e in s.events:
                if e.name in enames:
                    raise ParseError('duplicate event: {}'.format(e.name))

                enames.add(e.name)

                if e.id in eids:
                    raise ParseError('duplicate event: {}'.format(e.id))

                eids.add(e.id)

            s.init_events_dict()

        self._doc.init_dicts()

    def visit_Trace(self, node):
        doc = self._get_cur_obj()
        trace = self._visit_scope(node, pytsdl.tsdl.Trace())

        if trace.major is None:
            raise ParseError('trace block is missing major version')

        if trace.minor is None:
            raise ParseError('trace block is missing minor version')

        doc.trace = trace

    def visit_Env(self, node):
        doc = self._get_cur_obj()
        doc.env = self._visit_scope(node, pytsdl.tsdl.Env())

    def visit_Clock(self, node):
        doc = self._get_cur_obj()
        clock = self._visit_scope(node, pytsdl.tsdl.Clock())

        if clock.name is None:
            raise ParseError('clock block is missing name')

        if clock.freq is None:
            raise ParseError('clock block is missing frequency')

        doc.clocks.append(clock)

    def visit_Stream(self, node):
        doc = self._get_cur_obj()
        stream = self._visit_scope(node, pytsdl.tsdl.Stream())
        doc.streams.append(stream)

    def visit_Event(self, node):
        doc = self._get_cur_obj()
        event = pytsdl.tsdl.Event()
        event.stream_id = None
        event = self._visit_scope(node, event)

        if event.id is None:
            raise ParseError('event is missing ID')

        if event.name is None:
            raise ParseError('event is missing name')

        sid = 0

        if event.stream_id is not None:
            sid = event.stream_id

        found_stream = False

        for s in doc.streams:
            if s.id == sid:
                s.events.append(event)
                found_stream = True

        if not found_stream:
            msg = 'stream {} not found for event {}'.format(sid, event.name)

            raise ParseError(msg)

    def _value_assign_trace(self, node):
        trace = self._get_cur_obj()
        key = node.key.value
        value = node.value.expr

        if key == 'major':
            trace.major = value.value
        elif key == 'minor':
            trace.minor = value.value
        elif key == 'uuid':
            try:
                trace.uuid = uuid.UUID('{{{}}}'.format(value.value))
            except:
                raise ParseError('wrong UUID: {}'.format(value.value))
        elif key == 'byte_order':
            bo = value[0].value

            if bo not in _DocCreatorVisitor._byte_order_map:
                raise ParseError('wrong byte order: {}'.format(bo))

            trace.byte_order = _DocCreatorVisitor._byte_order_map[bo]
        else:
            # TODO: unknown key?
            pass

    def _value_assign_env(self, node):
        env = self._get_cur_obj()
        key = node.key.value
        value = node.value.expr

        if type(value) not in [LiteralString, ConstNumber]:
            raise ParseError('wrong env value: {}'.format(node.value))

        env[key] = value.value

    def _value_assign_clock(self, node):
        clock = self._get_cur_obj()
        key = node.key.value
        value = node.value.expr

        if key == 'name':
            clock.name = value[0].value
        elif key == 'description':
            clock.description = value.value
        elif key == 'freq':
            clock.freq = value.value
        elif key == 'precision':
            clock.precision = value.value
        elif key == 'offset_s':
            clock.offset_s = value.value
        elif key == 'offset':
            clock.offset = value.value
        elif key == 'absolute':
            clock.absolute = _DocCreatorVisitor._to_bool(value[0].value)
        elif key == 'uuid':
            try:
                clock.uuid = uuid.UUID('{{{}}}'.format(value.value))
            except:
                raise ParseError('wrong UUID: {}'.format(value.value))
        else:
            # TODO: unknown key?
            pass

    def _value_assign_stream(self, node):
        stream = self._get_cur_obj()
        key = node.key.value
        value = node.value.expr

        if key == 'id':
            stream.id = value.value
        else:
            # TODO: unknown key?
            pass

    def _value_assign_event(self, node):
        event = self._get_cur_obj()
        key = node.key.value
        value = node.value.expr

        if key == 'id':
            event.id = value.value
        if key == 'name':
            event.name = value.value
        if key == 'stream_id':
            event.stream_id = value.value
        else:
            # TODO: unknown key?
            pass

    def visit_ValueAssignment(self, node):
        obj = self._get_cur_obj()
        self._value_assignment_map[type(obj)](node)

    def visit_TypeAssignment(self, node):
        obj = self._get_cur_obj()
        #print(node.type)

    @property
    def doc(self):
        return self._doc


class Parser:
    def get_ast(self, tsdl):
        try:
            ast = pypeg2.parse(tsdl, Top,
                               comment=[pypeg2.comment_c, pypeg2.comment_cpp])
        except (SyntaxError, Exception) as e:
            raise ParseError(str(e))

        return ast

    def parse(self, tsdl):
        ast = self.get_ast(tsdl)

        visitor = _TypeResolverVisitor()
        ast.accept(visitor)

        visitor = _DocCreatorVisitor()
        ast.accept(visitor)

        return visitor._doc
