from __future__ import absolute_import
from __future__ import print_function
import os
import sys


def try_build(data):
    """Try to build OpenCL script to test for errors instead of having to wait
    until after the minified version is used during run time which is much
    harder to debug.
    """

    if isinstance(data, str) and sys.version_info.major >= 3:
        data = data.encode("utf-8", "ignore")

    try:
        # PyOpenCL is required.
        import pyopencl as cl
        import pyopencl.cffi_cl as _cl

        # Use the default context and the first device because it's
        # convenient. We could add a command line flag later if necessary.
        ctx = cl.create_some_context(interactive=False)
        device = ctx.devices[0]

        # Just build and check for errors. Some drivers output whitespace in
        # the log, so  we strip for consistency to prevent printing a blank
        # line to stdout.
        prg = None
        try:
            os.environ["PYOPENCL_NO_CACHE"] = "true"
            prg = cl.Program(ctx, data).build(devices=[device, ])
        except _cl.RuntimeError as e:
            # Print error log but strip off the parts PyOpenCL adds since we
            # don't need them.
            print("\n".join(e.what.split("\n")[0:-2]), file=sys.stderr)
            print("Could not build program.", file=sys.stderr)
            return False
        log = prg.get_build_info(device, cl.program_build_info.LOG).strip()
        if len(log) > 0:
            print(log, file=sys.stderr)
        if prg.get_build_info(device, cl.program_build_info.STATUS) != 0:
            print("Error while building program.", file=sys.stderr)
            return False
    except ImportError:
        print("PyOpenCL not found. Skipping test program build.", file=sys.stderr)
    except IndexError:
        print("No OpenCL devices detected. Skipping test program build.", file=sys.stderr)
    return True
