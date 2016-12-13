#!/bin/python
from __future__ import absolute_import
from __future__ import print_function
import argparse
from io import open
import os
import sys
import zlib
from oclminify.minify import DEFAULT_PREPROCESSOR_COMMAND, _do_minify
from oclminify.build import try_build


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="Version 0.8.0\nMinify OpenCL source files.",
                                     epilog="OpenCL is a trademark of Apple Inc., used under license by Khronos.\nCopyright (c) 2016 StarByte Software, Inc. All rights reserved.")
    parser.add_argument("--preprocessor-command", type=str, default=DEFAULT_PREPROCESSOR_COMMAND, help="Command to preprocess input source before minification. Defaults to \"%s\"" % DEFAULT_PREPROCESSOR_COMMAND)
    parser.add_argument("--preprocessor-no-stdin", action="store_true", default=False, help="Pass input to preprocessor using a temporary file instead of stdin.")
    parser.add_argument("--no-preprocess", action="store_true", default=False, help="Skip preprocessing step. Implies --no-minify.")
    parser.add_argument("--no-minify", action="store_true", default=False, help="Skip minification step. Useful when debugging.")
    parser.add_argument("--compress", action="store_true", default=False, help="Compress output using zlib.")
    parser.add_argument("--strip-zlib-header", action="store_true", default=False, help="Strips the two byte zlib header from the compressed output when --compress is used.")
    parser.add_argument("--header", action="store_true", default=False, help="Embed output in a C header file.")
    parser.add_argument("--header-function-args", action="store_true", default=False, help="Include function argument mappings in C header file.")
    parser.add_argument("--minify-kernel-names", action="store_true", default=False, help="Replace kernel function names with shorter names.")
    parser.add_argument("--global-postfix", type=str, default="", help="Postfix appended to each symbol name in the global scope. Used for preventing name collisions when minifying multiple source files separately. Implies --minify-kernel-names.")
    parser.add_argument("--try-build", action="store_true", default=False, help="Try to build the input using an OpenCL compiler before minifying. The compiled output is discarded. Requires pyopencl.")
    parser.add_argument("--output-file", type=str, default="", help="File path where output should be saved. Omit to write to stdout.")
    parser.add_argument("input", help="File path to OpenCL file that should be minified. A \"-\" indicates that input should be read from stdin.")
    args = parser.parse_args()

    # Read input from the specified file. If the specified file is "-", just
    # read from stdin so text can be piped in from a shell or whatever.
    if args.input == "-":
        data = ""
        while True:
            c = sys.stdin.read(1)
            if len(c) == 0:
                break
            data += c
    else:
        # Read entire file into memory.
        fd = open(args.input, "rb")
        if not fd:
            print("Could not open input file.", file=sys.stderr)
            sys.exit(-1)
        data = fd.read()
        fd.close()

    if args.try_build:
        if not try_build(data):
            sys.exit(-1)

    # Perform preprocessing and minification.
    original_size = len(data)
    original_data = data
    minifier, data = _do_minify(data,
                                preprocessor_command=args.preprocessor_command,
                                preprocessor_no_stdin=args.preprocessor_no_stdin,
                                minify=not args.no_minify,
                                minify_kernel_names=(args.minify_kernel_names or len(args.global_postfix) > 0) and not args.no_minify,
                                global_postfix=args.global_postfix)
    if args.no_preprocess:
        data = original_data
    minified_size = len(data)

    # Perform zlib compression.
    if not isinstance(data, bytes):
        data = data.encode("utf-8", "ignore")
    if args.compress:
        compressed_data = zlib.compress(data, 9)
        if args.strip_zlib_header:
            # Strip header: 0x78 0xDA
            data = compressed_data[2:]
        else:
            data = compressed_data

    # Print sizes of output after each stage. This is a minifier, might as well
    # see how well we did.
    compressed_size = len(data)
    result_message = "Original Size: %i, Minified Size: %i" % (original_size, minified_size)
    if args.compress:
        result_message += ", Compressed Size: %i" % compressed_size
    print(result_message, file=sys.stderr)

    # Transform minified output into a C header file if run with --header.
    if args.header:
        guard_name = os.path.split(args.input)[-1].upper().replace(".", "_") + "_DATA_H"
        var_base_name = os.path.split(args.input)[-1].lower()
        var_base_name = var_base_name[:var_base_name.find(".")].capitalize()
        header_text = "#ifndef %s\n#define %s\n\n" % (guard_name, guard_name)
        header_text += "static const size_t %s_SIZE = %i;\n" % (var_base_name.upper(), len(data))
        header_text += "static const unsigned char %s_DATA[] = {" % var_base_name.upper()
        for (i, byte) in enumerate(data):
            if isinstance(byte, str):
                byte = ord(byte)
            header_text += str(hex(byte))
            if i != (len(data) - 1):
                header_text += ","
        header_text += "};\n\n"
        for (old_name, func) in minifier.functions.items():
            if old_name not in minifier.kernel_functions:
                continue  # Not a kernel, no need to make available.
            header_text += "#define %s_FUNCTION_%s \"%s\"\n" % (var_base_name.upper(), old_name.upper(), func.name)
            if args.header_function_args:
                for (old_arg, new_arg) in minifier.functions_args[old_name].items():
                    header_text += "#define %s_FUNCTION_%s_ARG_%s = \"%s\"\n" % (var_base_name.upper(), old_name.upper(), old_arg.upper(), new_arg)
                header_text += "\n"
        if not args.header_function_args:
            header_text += "\n"
        header_text += "#endif"
        data = header_text

    # Save output to file if run with --output-file, otherwise just print to
    # stdout so it can be processed further in a shell or whatever.
    if args.output_file == "":
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        print(data)
    else:
        fd = open(args.output_file, "wb")
        if not fd:
            print("Could not open output file", file=sys.stderr)
            sys.exit(-1)
        if not isinstance(data, bytes):
            data = data.encode("utf-8", "ignore")
        fd.write(data)
        fd.close()

if __name__ == "__main__":
    main()
