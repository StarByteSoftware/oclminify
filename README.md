oclminify
=========

**oclminify** is an [OpenCL™](https://www.khronos.org/opencl/) source minifier. It takes OpenCL source code and makes it as small as possible by stripping comments, removing unnecessary space, renaming symbols, rewriting vector indices, etc. The minified source can be optionally compressed and then saved as is or as a C header. The latter makes it very easy to embed into a compiled application. The original source and the minified source are functionally identical and should compile into the exact same byte code.

If you're targeting platforms with OpenCL 2.0 or later support, you should consider using [SPIR™](https://www.khronos.org/spir) instead.

oclminify was originally developed by the [Phoduit](https://phoduit.com) team.

Prerequisites
-------------

- [Python®](https://www.python.org/) >= 2.7 (Python 3 is also supported)
- [pycparser](https://github.com/eliben/pycparser) >= 2.14 (github version is recommended if you need #pragma support)
- [pycparserext](https://github.com/inducer/pycparserext) >= 2016.1
- [pyopencl](https://mathema.tician.de/software/pyopencl/) >= 2016.1 (optional, checks if source can be compiled before minifying)
- [GCC](https://gcc.gnu.org/), [cpp](https://gcc.gnu.org/), [MSVC](https://www.visualstudio.com/) or another C preprocessor

Install
-------

From the command line:

    pip install oclminify

If you want oclminify to support a compile check before minification, with an actual OpenCL driver, install pyopencl with:

    pip install pyopencl

Usage
-----

    oclminify [-h] [--preprocessor-command PREPROCESSOR_COMMAND]
              [--preprocessor-no-stdin] [--no-preprocess] [--no-minify]
			  [--compress] [--strip-zlib-header] [--header]
			  [--header-function-args] [--minify-kernel-names]
			  [--global-postfix GLOBAL_POSTFIX] [--try-build]
			  [--output-file OUTPUT_FILE]
			  input

oclminify takes a single input file. If the input file is - (a single hyphen), input will be read from STDIN. If the --output-file option is omitted, the output is written to STDOUT.

The available options are:
```
  -h, --help            show this help message and exit
  --preprocessor-command PREPROCESSOR_COMMAND
                        Command to preprocess input source before
                        minification. Defaults to "gcc -E -undef -P -std=c99
                        -"
  --preprocessor-no-stdin
                        Pass input to preprocessor using a temporary file
                        instead of stdin.
  --no-preprocess       Skip preprocessing step. Implies --no-minify.
  --no-minify           Skip minification step. Useful when debugging.
  --compress            Compress output using zlib.
  --strip-zlib-header   Strips the two byte zlib header from the compressed
                        output when --compress is used.
  --header              Embed output in a C header file.
  --header-function-args
                        Include function argument mappings in C header file.
  --minify-kernel-names
                        Replace kernel function names with shorter names.
  --global-postfix GLOBAL_POSTFIX
                        Postfix appended to each symbol name in the global
                        scope. Used for preventing name collisions when
                        minifying multiple source files separately. Implies
                        --minify-kernel-names.
  --try-build           Try to build the input using an OpenCL compiler before
                        minifying. The compiled output is discarded. Requires
                        pyopencl.
  --output-file OUTPUT_FILE
                        File path where output should be saved. Omit to write
                        to stdout.

```

Examples
--------

To simply minify an OpenCL source file and write the result to file, run:

    oclminify --output-file output.minified.cl input.cl

The examples directory contains more examples:

- `examples/minimal` — shows how to create a minimal project that minifies an OpenCL source file and builds a C based project using a shell script.

- `examples/cmake` — shows how to integrate oclminify with a [CMake](https://cmake.org/) based C++ project.

- `examples/compress` — shows how to use oclminify in a CMake project to compress an OpenCL source file at compile time and then decompress it at run time.

Legal
-----

- OpenCL is a trademark of Apple Inc., under license by Khronos.
- SPIR is a trademark of the Khronos Group Inc.
- Python is a registered trademark of the Python Software Foundation.
- Copyright (c) 2016 StarByte Software, Inc. All rights reserved.
