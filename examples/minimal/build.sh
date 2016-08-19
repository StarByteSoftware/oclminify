# Create a directory to put compiled results.
mkdir -p ./build

# Minify the kernel.cl file and create a C header containing the minified
# result. An attempt will be made to build the kernel with an OpenCL driver
# first so you don't have to wait until run-time to check for compile errors.
oclminify --header --minify-kernel-names --try-build --output-file=./build/opencl.cl.h kernel.cl

# Compile the C code and output the program 'minimal' into the build directory.
gcc -Ibuild main.c -o ./build/minimal -lOpenCL -g
