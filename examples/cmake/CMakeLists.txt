# Typical CMake project setup.
CMAKE_MINIMUM_REQUIRED(VERSION 3.2)

PROJECT(example)
ADD_EXECUTABLE(example "main.cpp")
SET_TARGET_PROPERTIES(example PROPERTIES COMPILE_FLAGS "-std=c++14")
TARGET_LINK_LIBRARIES(example OpenCL)

# Include the provided .cmake file to easily minify a bunch of sources.
INCLUDE(${CMAKE_SOURCE_DIR}/../oclminify.cmake)

# Minify the OpenCL sources. You must specify at least the target name
# (project name above) and one or more .cl source files located relative to
# ${CMAKE_CURRENT_SOURCE_DIR}. If one of these files are modified, cmake will
# run the minifier on the next build. The minifier produces C header files
# called "${source_basename}.cl.h". For example, "MatrixMul.cl" will have a
# minified output called "MatrixMul.cl.h". See oclminify.cmake for a full list
# of options.
OCLMINIFY_MINIFY_SOURCES(TARGET example SOURCES "kernel1.cl" "kernel2.cl")
