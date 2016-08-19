VECTOR_SIZES = ["", "2", "3", "4", "8", "16"]
ROUNDING_MODES = ["", "_rte", "_rtz", "_rtp", "_rtn"]


# Internal only helper functions
def _join_dicts(*dicts):
    joined_dicts = {}
    for dict in dicts:
        joined_dicts.update(dict)
    return joined_dicts


def _vector_size(arg_type):
    return "".join([char for char in arg_type if char.isdigit()])


def _vector_type(arg_type):
    return "".join([char for char in arg_type if char.isalpha()])


def _strip_vector_size_from_first_arg(func_name, args):
    assert(len(args) >= 1)
    return _vector_type(args[0])


def _abs_function_return_type(func_name, args):
    assert(len(args) >= 1)
    vector_type = args[0]
    if not vector_type.startswith("u"):
        vector_type = "u" + vector_type
    return vector_type


def _upsample_function_return_type(func_name, args):
    assert(len(args) >= 1)
    vector_size = _vector_size(args[0])
    vector_type = _vector_type(args[0])
    unsigned = "u" if vector_type.startswith("u") else ""
    if unsigned:
        vector_type = vector_type[1:]

    return unsigned + {
        "char": "short",
        "short": "int",
        "int": "long",
    }[vector_type] + vector_size


def _relational_function_return_type(func_name, args):
    assert(len(args) >= 1)
    arg0 = args[0]
    vector_size = _vector_size(arg0)
    if arg0.startswith("float"):
        return "int" + vector_size
    else:
        return "long" + vector_size


def _shuffle_function_return_type(func_name, args):
    assert(len(args) >= 2)
    return _vector_type(args[0]) + _vector_size(args[-1])


class BUILTIN:
    CONSTANTS = {
        "HUGE_VAL": "double",
        "HUGE_VALF": "float",
        "INFINITY": "float",
        "M_E": "double",
        "M_E_F": "float",
        "M_LOG2E": "double",
        "M_LOG2E_F": "float",
        "M_LOG10E": "double",
        "M_LOG10E_F": "float",
        "M_LN2": "double",
        "M_LN2_F": "float",
        "M_LN10": "double",
        "M_LN10_F": "float",
        "M_PI": "double",
        "M_PI_F": "float",
        "M_PI_2": "double",
        "M_PI_2_F": "float",
        "M_PI_4": "double",
        "M_PI_4_F": "float",
        "M_1_PI": "double",
        "M_1_PI_F": "float",
        "M_2_PI": "double",
        "M_2_PI_F": "float",
        "M_2_SQRTPI": "double",
        "M_2_SQRTPI_F": "float",
        "M_SQRT2": "double",
        "M_SQRT2_F": "float",
        "M_SQRT1_2": "double",
        "M_SQRT1_2_F": "float",
        "MAXFLOAT": "float",
        "NAN": "float",
    }

    # All convert_ and as_ functions that specify their return type as part of
    # their name.
    CAST_FUNCTIONS = ["convert_%s%s" % (type, size)
                        for type in ["char", "uchar", "short", "ushort", "int", "uint", "long", "ulong"]
                            for size in VECTOR_SIZES] + \
                     ["convert_%s%s%s%s" % (type, size, sat, rounding)
                        for type in ["float", "double"]
                            for size in VECTOR_SIZES
                                for sat in ["", "_sat"]
                                    for rounding in ROUNDING_MODES] + \
                     ["as_%s%s" % (type, size)
                        for type in ["char", "uchar", "short", "ushort", "int", "uint", "long", "ulong", "float", "double"]
                            for size in VECTOR_SIZES]

    # Functions who's return type is the same as their first argument's type.
    GEN1_FUNCTIONS = [
        # Math Functions (float/double)
        "acos",
        "acosh",
        "acospi"
        "asin",
        "asinh",
        "asinpi",
        "atan",
        "atan2",
        "atanh",
        "atanpi",
        "atan2pi",
        "cbrt",
        "ceil",
        "copysign",
        "cos",
        "cosh",
        "cospi",
        "erfc",
        "erf",
        "exp",
        "exp2",
        "exp10",
        "expm1",
        "fabs",
        "fdim",
        "floor",
        "fma",
        "fmax",
        "fmin",
        "fmod",
        "fract",
        "frexp",
        "hypot",
        "ldexp",
        "lgamma",
        "lgamma_r",
        "log",
        "log2",
        "log10",
        "log1p",
        "logb",
        "mad",
        "maxmag",
        "minmag",
        "modf",
        "nextafter",
        "pow"
        "pown",
        "powr",
        "remainder",
        "remquo",
        "rint",
        "rootn",
        "round",
        "rsqrt",
        "sin",
        "sincos",
        "sinh",
        "sinpi",
        "sqrt",
        "tan",
        "tanh",
        "tanpi",
        "tgamma",
        "trunc",
        "half_cos",
        "half_divide",
        "half_exp",
        "half_exp2",
        "half_exp10",
        "half_log",
        "half_log2",
        "half_log10",
        "half_powr",
        "half_recip",
        "half_rsqrt",
        "half_sin",
        "half_sqrt",
        "half_tan",
        "native_cos",
        "native_divide",
        "native_exp",
        "native_exp2",
        "native_exp10",
        "native_log",
        "native_log2",
        "native_log10",
        "native_powr",
        "native_recip",
        "native_rsqrt",
        "native_sin",
        "native_sqrt",
        "native_tan",
        # Math Functions (integer)
        "add_sat",
        "hadd",
        "rhadd",
        "clamp",
        "clz",
        "mad_hi",
        "mad_sat",
        "max",
        "min",
        "mul_hi",
        "rotate",
        "sub_sat",
        "popcount",
        "mad24",
        "mul24",
        # Common Functions
        # "clamp", # Already listed as an integer math function above.
        "degrees",
        # "max", # Already listed as an integer math function above.
        # "min", # Already listed as an integer math function above.
        "mix",
        "radians",
        "step",
        "smoothstep",
        "sign",
        # Geometric Functions
        "cross",
        "normalize"
        "fast_normalize",
        # Relational Functions
        "bitselect",
        "select",
        # Atomic Functions
        "atomic_inc",
        "atomic_dec",
    ]

    # Functions who's return type is the same as their second argument's type.
    GEN2_FUNCTIONS = [
        # Atomic Functions
        "atomic_add",
        "atomic_sub",
        "atomic_xchg",
        "atomic_cmpxchg",
        "atomic_min",
        "atomic_max",
        "atomic_and",
        "atomic_or",
        "atomic_xor",
    ]

    # Functions that always have the same return type. The return type is
    # specified as the value here.
    FIXED_FUNCTIONS_MAP = _join_dicts({
        # Work-Item Functions
        "get_work_dim": "uint",
        "get_global_size": "size_t",
        "get_global_id": "uint",
        "get_local_size": "size_t",
        "get_local_id": "size_t",
        "get_num_groups": "size_t",
        "get_group_id": "size_t",
        "get_global_offset": "size_t",
        # Relational Functions
        "any": "int",
        "all": "int", },
        # Vector Data Load and Store Functions
        dict([("vstore%s" % size, "void") for size in VECTOR_SIZES]),
        dict([("vload_half%s" % size, "float%s" % size) for size in VECTOR_SIZES]),
        dict([("vstore_half%s%s" % (size, rounding), "void") for size in VECTOR_SIZES for rounding in ROUNDING_MODES]),
        dict([("vstorea_half%s%s" % (size, rounding), "void") for size in VECTOR_SIZES[1:] for rounding in ROUNDING_MODES]),
        dict([("vloada_half%s" % size, "float%s" % size) for size in VECTOR_SIZES[1:]]), {
        # Synchronization Functions
        "barrier": "void",
        # Explicit Memory Fence Functions
        "mem_fence": "void",
        "read_mem_fence": "void",
        "write_mem_fence": "void",
        # Async Copies from Global to Local Memory, Local to Global Memory, and
        # Prefetch Functions
        "async_work_group_copy": "event_t",
        "async_work_group_strided_copy": "event_t",
        "wait_group_events": "void",
        "prefetch": "void",
        # Miscellaneous Vector Functions
        "vec_step": "int",
        # printf Function (It has its own section in the documentation...)
        "printf": "int",
        # Image Read and Write Functions
        "read_imagef": "float4",
        "read_imagei": "int4",
        "read_imageui": "uint4",
        "write_imagef": "void",
        "write_imagei": "void",
        "write_imageui": "void",
        # Built-in Image Query Functions
        "get_image_width": "int",
        "get_image_height": "int",
        "get_image_depth": "int",
        "get_image_channel_data_type": "int",
        "get_image_channel_order": "int",
        "get_image_array_size": "size_t",
    })

    # Functions that require different processing from the above choices to
    # determine the return type. The values in the map are functions that take
    # the function name and a list of function argument types.
    OTHER_FUNCTIONS_MAP = _join_dicts({
        # Math Functions (float/double)
        "ilogb": lambda func_name, args: "int" + _vector_size(args[0]),
        "nan": lambda func_name, args: ("float%s" if args[0][:4] == "uint" else "double%s") % args[0][4:],
        # Math Functions (integer)
        "abs": _abs_function_return_type,
        "abs_diff": _abs_function_return_type,
        "upsample": _upsample_function_return_type,
        # Geometric Functions
        "dot": _strip_vector_size_from_first_arg,
        "distance": _strip_vector_size_from_first_arg,
        "length": _strip_vector_size_from_first_arg,
        "fast_distance": _strip_vector_size_from_first_arg,
        "fast_length": _strip_vector_size_from_first_arg,
        # Relational Functions
        "isequal": _relational_function_return_type,
        "isnotequal": _relational_function_return_type,
        "isgreater": _relational_function_return_type,
        "isgreaterequal": _relational_function_return_type,
        "isless": _relational_function_return_type,
        "islessequal": _relational_function_return_type,
        "islessgreater": _relational_function_return_type,
        "isfinite": _relational_function_return_type,
        "isinf": _relational_function_return_type,
        "isnan": _relational_function_return_type,
        "isnormal": _relational_function_return_type,
        "isordered": _relational_function_return_type,
        "isunordered": _relational_function_return_type,
        "signbit": _relational_function_return_type, },
        # Vector Data Load and Store Functions
        dict([("vload%s" % (size), lambda func_name, args: _vector_type(args[1]) + _vector_size(func_name)) for size in VECTOR_SIZES]), {
        # Miscellaneous Vector Functions
        "shuffle": _shuffle_function_return_type,
        "shuffle2": _shuffle_function_return_type,
        # Built-in Image Query Functions
        "get_image_dim": lambda func_name, args: "int3" if args[0] == "image3d_t" else "int2",
    })

    @classmethod
    def get_func_return_type(cls, func_name, args):
        # Return type is in function name.
        if func_name in cls.CAST_FUNCTIONS:
            # Extract return type from name.
            return func_name.split("_")[1]

        # Return type matches first argument.
        if func_name in cls.GEN1_FUNCTIONS and len(args) >= 1:
            return args[0]

        # Return type matches second argument.
        if func_name in cls.GEN2_FUNCTIONS and len(args) >= 2:
            return args[1]

        # Return type never changes and can be determined solely by the
        # function name.
        if func_name in cls.FIXED_FUNCTIONS_MAP.keys():
            return cls.FIXED_FUNCTIONS_MAP[func_name]

        # Return type requires special handling to figure out.
        if func_name in cls.OTHER_FUNCTIONS_MAP .keys():
            return cls.OTHER_FUNCTIONS_MAP[func_name](func_name, args)

        # Unknown built-in function.
        return "void"
