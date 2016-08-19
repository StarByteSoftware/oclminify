# Typical CMake project setup.
CMAKE_MINIMUM_REQUIRED(VERSION 3.2)

PROJECT(compress)
ADD_EXECUTABLE(compress "main.cpp")
SET_TARGET_PROPERTIES(compress PROPERTIES COMPILE_FLAGS "-std=c++14")

# Find and link against zlib which is required to decompress the minified and
# compressed OpenCL source.
FIND_PACKAGE(ZLIB REQUIRED)
TARGET_LINK_LIBRARIES(compress ${ZLIB_LIBRARIES})

# Minify the OpenCL sources, compress using zlib, and then remove the two
# byte header. See the cmake example and oclminify.cmake for more about using
# OCLMINIFY_MINIFY_SOURCES().
INCLUDE(${CMAKE_SOURCE_DIR}/../oclminify.cmake)
OCLMINIFY_MINIFY_SOURCES(
	TARGET compress
	SOURCES "addone.cl"
	OPTIONS "--header" "--try-build" "--compress" "--strip-zlib-header"
)
