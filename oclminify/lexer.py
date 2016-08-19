from __future__ import absolute_import
from pycparser.c_lexer import CLexer
from pycparserext import ext_c_lexer


class OpenCLCLexer(ext_c_lexer.OpenCLCLexer):
    pass

# Override pycparserext's implementation because it fails to parse
# some pragmas like #pragma unroll. The original implementation works
# just fine for our minification-related usage.
OpenCLCLexer.t_PPHASH = CLexer.t_PPHASH

# Add support for __const type qualifier. It's not in any of the specs but it
# is commonly used in red's OpenCL examples.
ext_c_lexer.add_lexer_keywords(OpenCLCLexer, ["__const"])
