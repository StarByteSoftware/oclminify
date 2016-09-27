from __future__ import absolute_import
from __future__ import print_function
import os
import subprocess
import sys
import tempfile
from oclminify.generator import Generator
from oclminify.minifier import Minifier
from oclminify.parser import Parser


DEFAULT_PREPROCESSOR_COMMAND = "gcc -E -undef -P -std=c99 -"
DEFAULT_PREPROCESSOR_NO_STDIN = False
DEFAULT_MINIFY = True
DEFAULT_MINIFY_KERNEL_NAMES = True
DEFAULT_GLOBAL_POSTFIX = ""


def _do_minify(data,
               preprocessor_command=DEFAULT_PREPROCESSOR_COMMAND,
               preprocessor_no_stdin=DEFAULT_PREPROCESSOR_NO_STDIN,
               minify=DEFAULT_MINIFY,
               minify_kernel_names=DEFAULT_MINIFY_KERNEL_NAMES,
               global_postfix=DEFAULT_GLOBAL_POSTFIX):
    if isinstance(data, str) and sys.version_info.major >= 3:
        data = data.encode("utf-8", "ignore")

    # Optionally store data in a temporary file that is passed to the
    # preprocessor. This is mainly for MSVC which doesn't support passing the
    # source file using stdin.
    temp_input_file = None
    if preprocessor_no_stdin:
        temp_input_file = tempfile.NamedTemporaryFile(delete=False)
        temp_input_file.write(data)
        temp_input_file.close()
        temp_input_file = temp_input_file.name
        preprocessor_command += " " + temp_input_file

    # Use GCC to do the preprocessing.
    p = subprocess.Popen(preprocessor_command.split(" "),
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    data, err = p.communicate(data)
    err = err.decode("utf-8").replace("\r","")
    if err:
        print(err, file=sys.stderr)
    if temp_input_file:
        # Clean-up temporary file if one was used above.
        os.remove(temp_input_file)
    if p.returncode != 0:
        print("Failed to preprocess file", file=sys.stderr)
        sys.exit(-1)
    data = data.decode("utf-8")
    data = data.replace("\r", "")  # Strip Windows newline character added by GCC on Windows.
    preprocessed_data = data

    parser = Parser()
    ast = parser.parse(data)

    # Uncomment when debugging to show the parsed graph.
    # ast.show()

    # Walk source tree graph and apply minification. The minifier is run even
    # when not minifying so we can collect kernel names for header output.
    minifier = Minifier(minify_kernel_names, global_postfix)
    minifier.visit(ast)
    if minify:
        data = Generator().visit(ast)
    else:
        data = preprocessed_data
    return (minifier, data)


def minify(data,
           preprocessor_command=DEFAULT_PREPROCESSOR_COMMAND,
           preprocessor_no_stdin=DEFAULT_PREPROCESSOR_NO_STDIN,
           minify=DEFAULT_MINIFY,
           minify_kernel_names=DEFAULT_MINIFY_KERNEL_NAMES,
           global_postfix=DEFAULT_GLOBAL_POSTFIX):
    return _do_minify(data,
                      preprocessor_command=preprocessor_command,
                      preprocessor_no_stdin=preprocessor_no_stdin,
                      minify=minify,
                      minify_kernel_names=minify_kernel_names,
                      global_postfix=global_postfix)[1]
