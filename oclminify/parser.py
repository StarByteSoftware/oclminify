from __future__ import absolute_import
from pycparser import CParser
from pycparserext import ext_c_parser


class Parser(ext_c_parser.OpenCLCParser):
    # Allow extension specific types to be parsed. Even those in newer versions
    # of OpenCL that we don't really support should parse when possible.
    initial_type_symbols = ext_c_parser.OpenCLCParser.initial_type_symbols | \
                           set(["void",  # OpenCL >= 1.0
                                "counter32_t",  # cl_ext_atomic_counters_32
                                "counter64_t",  # cl_ext_atomic_counters_64
                                "atomic_int", ])  # TODO: Find out which standard introduced this. OpenCL 2.0, I think.

    # Use our patched lexer instead. See lexer.py for details.
    from oclminify.lexer import OpenCLCLexer as lexer_class

    # Add support for __const type qualifier. It's not in any of the specs but
    # it is commonly used in red's OpenCL examples.
    def p_type_qualifier_cl(self, p):
        """ type_qualifier  : __GLOBAL
                            | GLOBAL
                            | __LOCAL
                            | LOCAL
                            | __CONSTANT
                            | __CONST
                            | CONSTANT
                            | __PRIVATE
                            | PRIVATE
                            | __READ_ONLY
                            | READ_ONLY
                            | __WRITE_ONLY
                            | WRITE_ONLY
                            | __READ_WRITE
                            | READ_WRITE
        """
        p[0] = p[1]

# Override pycparserext's implementation because it fails to parse pointers in
# type declarations. Once again, the original implementation works just fine
# for our minification-related usage.
Parser.p_declarator_2 = CParser.p_declarator_2
