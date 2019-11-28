"""LV2 Python interface via ctypes"""

from ctypes import (CFUNCTYPE, POINTER, Structure, Union, c_char_p, c_double, c_float, c_int32,
                    c_int64, c_uint, c_uint32, c_void_p)


# lv2/core/lv2.h

LV2_Handle = c_void_p


class LV2_Feature(Structure):
    __slots__ = ["URI", "data"]
    _fields_ = [
        ("URI", c_char_p),
        ("data", c_void_p)
    ]


class LV2_Descriptor(Structure):
    __slots__ = [
        "URI",
        "instantiate",
        "connect_port",
        "activate",
        "run",
        "deactivate",
        "cleanup",
        "extension_data",
    ]


LV2_Descriptor._fields_ = [
        ("URI", c_char_p),
        (
            "instantiate",
            CFUNCTYPE(
                LV2_Handle,
                POINTER(LV2_Descriptor),
                c_double,
                c_char_p,
                POINTER(POINTER(LV2_Feature)),
            ),
        ),
        ("connect_port", CFUNCTYPE(None, LV2_Handle, c_uint32, POINTER(None))),
        ("activate", CFUNCTYPE(None, LV2_Handle)),
        ("run", CFUNCTYPE(None, LV2_Handle, c_uint32)),
        ("deactivate", CFUNCTYPE(None, LV2_Handle)),
        ("cleanup", CFUNCTYPE(None, LV2_Handle)),
        ("extension_data", CFUNCTYPE(c_void_p, c_char_p)),
    ]


# lv2/urid/urid.h

LV2_URID_Map_Handle = POINTER(None)
LV2_URID_Unmap_Handle = POINTER(None)
LV2_URID = c_uint32

map_func_t = CFUNCTYPE(LV2_URID, LV2_URID_Map_Handle, c_char_p)
unmap_func_t = CFUNCTYPE(c_char_p, LV2_URID_Unmap_Handle, LV2_URID)


class LV2_URID_Map(Structure):
    __slots__ = ['handle', 'map']
    _fields_ = [
        ('handle', LV2_URID_Map_Handle),
        ('map', map_func_t),
    ]


class LV2_URID_Unmap(Structure):
    __slots__ = ['handle', 'unmap']
    _fields_ = [
        ('handle', LV2_URID_Unmap_Handle),
        ('unmap', unmap_func_t),
    ]


# lv2/options/options.h

LV2_OPTIONS_INSTANCE = 0
LV2_OPTIONS_RESOURCE = 1
LV2_OPTIONS_BLANK = 2
LV2_OPTIONS_PORT = 3


class LV2_Options_Option(Structure):
    """An option."""

    __slots__ = [
        'context',
        'subject',
        'key',
        'size',
        'type',
        'value',
    ]
    _fields_ = [
        ('context', c_uint),
        ('subject', c_uint32),
        ('key', LV2_URID),
        ('size', c_uint32),
        ('type', LV2_URID),
        ('value', c_void_p),
    ]


# lv2/atom/atom.h

class LV2_Atom(Structure):
    """The header of an atom:Atom."""

    __slots__ = ['size', 'type']
    _fields_ = [
        ('size', c_uint32),  # Size in bytes, not including type and size.
        ('type', c_uint32),  # Type of this atom (mapped URI).
    ]


class LV2_Atom_Double(Structure):
    """An atom:Double"""

    __slots__ = ['atom', 'body']
    _fields_ = [
        ('atom', LV2_Atom),
        ('body', c_double)
    ]


class LV2_Atom_Event_time(Union):
    """Time stamp"""

    _fields_ = [
        ('frames', c_int64),
        ('beats', c_double)
    ]


class LV2_Atom_Event(Structure):
    """The header of an atom:Event"""

    __slots__ = ['atom', 'body']
    _fields_ = [
        ('time', LV2_Atom_Event_time),
        ('body', LV2_Atom)
    ]


class LV2_Atom_Float(Structure):
    """An atom:Float"""

    __slots__ = ['atom', 'body']
    _fields_ = [
        ('atom', LV2_Atom),
        ('body', c_float)
    ]


class LV2_Atom_Int(Structure):
    """An atom:Int or atom:Bool"""

    __slots__ = ['atom', 'body']
    _fields_ = [
        ('atom', LV2_Atom),
        ('body', c_int32)
    ]


class LV2_Atom_Literal_Body(Structure):
    """The body of an atom:Literal"""

    __slots__ = ['datatype', 'lang']
    _fields_ = [
        ('datatype', c_uint32),  # Datatype URID.
        ('lang', c_uint32)       # Language URID
        # Contents (a null-terminated UTF-8 string) follow here.
    ]


class LV2_Atom_Literal(Structure):
    """An atom:Literal"""

    __slots__ = ['atom', 'body']
    _fields_ = [
        ('atom', LV2_Atom),
        ('body', LV2_Atom_Literal_Body)
    ]


class LV2_Atom_Long(Structure):
    """An atom:Long"""

    __slots__ = ['atom', 'body']
    _fields_ = [
        ('atom', LV2_Atom),
        ('body', c_int64)
    ]


class LV2_Atom_Object_Body(Structure):
    """The body of an atom:Object"""

    __slots__ = ['id', 'otype']
    _fields_ = [
        ('id', c_uint32),     # URID, or 0 for blank.
        ('otype', c_uint32),  # Type URID (same as rdf:type, for fast dispatch).
    ]


class LV2_Atom_Object(Structure):
    """An atom:Object"""

    __slots__ = ['atom', 'body']
    _fields_ = [
        ('atom', LV2_Atom),
        ('body', LV2_Atom_Object_Body)
    ]


class LV2_Atom_Property_Body(Structure):
    """The body of an atom:Property (e.g. in an atom:Object)."""

    __slots__ = ['key', 'context', 'value']
    _fields_ = [
        ('key', c_uint32),      # Key (predicate) (mapped URI).
        ('context', c_uint32),  # Context URID (may be, and generally is, 0).
        ('value', LV2_Atom)     # Value atom header.
    ]


class LV2_Atom_Property(Structure):
    """An atom:Property """

    __slots__ = ['atom', 'body']
    _fields_ = [
        ('atom', LV2_Atom),
        ('body', LV2_Atom_Property_Body)
    ]


class LV2_Atom_Sequence_Body(Structure):
    """The body of an atom:Sequence (a sequence of events)

    The unit field is either a URID that described an appropriate time stamp
    type, or may be 0 where a default stamp type is known. For
    LV2_Descriptor::run(), the default stamp type is audio frames.

    The contents of a sequence is a series of LV2_Atom_Event, each aligned to
    64-bits, e.g.:

    | Event 1 (size 6)                              | Event 2
    |       |       |       |       |       |       |       |       |
    | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |
    |FRAMES |SUBFRMS|TYPE   |SIZE   |DATADATADATAPAD|FRAMES |SUBFRMS|...

    """
    __slots__ = ['unit', 'pad']
    _fields_ = [
        ('unit', c_uint32),     # URID of unit of event time stamps.
        ('pad', c_uint32),      # Currently unused.
    ]


class LV2_Atom_Sequence(Structure):
    """An atom:Sequence"""

    __slots__ = ['atom', 'body']
    _fields_ = [
        ('atom', LV2_Atom),
        ('body', LV2_Atom_Sequence_Body)
    ]


class LV2_Atom_String(Structure):
    """An atom:String"""

    __slots__ = ['atom']
    _fields_ = [
        ('atom', LV2_Atom),
        # Contents (a null-terminated UTF-8 string) follow here.
    ]


class LV2_Atom_Tuple(Structure):
    """An atom:Tuple"""

    __slots__ = ['atom']
    _fields_ = [
        ('atom', LV2_Atom),
        # Contents (a null-terminated UTF-8 string) follow here.
    ]


class LV2_Atom_URID(Structure):
    """An atom:URID"""

    __slots__ = ['atom', 'body']
    _fields_ = [
        ('atom', LV2_Atom),
        ('body', LV2_URID)
    ]


class LV2_Atom_Vector_Body(Structure):
    """The body of an atom:Vector"""

    __slots__ = ['child_size', 'child_type']
    _fields_ = [
        ('child_size', c_uint32),  # The size of each element in the vector.
        ('child_type', c_uint32),  # The type of each element in the vector.
        # Contents (a series of packed atom bodies) follow here.
    ]


class LV2_Atom_Vector(Structure):
    """An atom:Vector"""

    __slots__ = ['atom', 'body']
    _fields_ = [
        ('atom', LV2_Atom),
        ('body', LV2_Atom_Vector_Body)
    ]
