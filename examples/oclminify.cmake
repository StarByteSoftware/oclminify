INCLUDE(CMakeParseArguments)

# OCLMINIFY_MINIFY_SOURCES(
#                            [TARGET] target_name
#                            [SOURCES] source1 [source2 ...]
#                            [PYTHON_COMMAND] python_command
#                            [PYTHON_MODULE_PATHS] python_module_paths
#                            [PREPROCESSOR_COMMAND] preprocessor_command
#                            [OUTPUT_FILE_POSTFIX] output_file_postfix
#                            [OPTIONS] other_oclminify_options
#                            )
#
# This command adds a build step to a target to minify the specified OpenCL
# source files. Source files should be specified relative to
# ${CMAKE_CURRENT_SOURCE_DIR}. By default, C header files are outputted to the
# ${CMAKE_CURRENT_BINARY_DIR} with ".cl.h" appended to the base name of the
# source file. For example, "MatrixMul.cl" will have a minified output called
# "MatrixMul.cl.h". The output directory is automatically added as
# an include directory to the target.
# 
# Simple usage:
# INCLUDE(/path/to/oclminify.cmake) 
# OCLMINIFY_MINIFY_SOURCES(TARGET example_project SOURCES "kernel1.cl" "kernel2.cl")
#
FUNCTION(OCLMINIFY_MINIFY_SOURCES )
	SET(options)
	SET(one_value_args TARGET PYTHON_COMMAND PYTHON_MODULE_PATHS PREPROCESSOR_COMMAND OUTPUT_FILE_POSTFIX)
	SET(multi_value_args SOURCES OPTIONS)
	cmake_parse_arguments(OCLMINIFY_MINIFY_SOURCES "${options}" "${one_value_args}" "${multi_value_args}" ${ARGN})

	# Setup defaults for args that were not specified.
	IF("${OCLMINIFY_MINIFY_SOURCES_PREPROCESSOR_COMMAND}" STREQUAL "")
		IF("${CMAKE_C_COMPILER_ID}" STREQUAL "MSVC")
			SET(OCLMINIFY_MINIFY_SOURCES_PREPROCESSOR_COMMAND ${CMAKE_C_COMPILER} /EP /u /nologo)
		ELSE()
			SET(OCLMINIFY_MINIFY_SOURCES_PREPROCESSOR_COMMAND ${CMAKE_C_COMPILER} -E -undef -P -std=c99 -)
		ENDIF()
	ENDIF()
	IF("${OCLMINIFY_MINIFY_SOURCES_OUTPUT_FILE_PREFIX}" STREQUAL "")
		SET(OCLMINIFY_MINIFY_SOURCES_OUTPUT_FILE_POSTFIX ".cl.h")
	ENDIF()
	IF("${OCLMINIFY_MINIFY_SOURCES_OPTIONS}" STREQUAL "")
		SET(OCLMINIFY_MINIFY_SOURCES_OPTIONS "--header" "--try-build")
	ENDIF()

	# Setup oclminify command to be run. Neither PYTHON_COMMAND nor
	# PYTHON_MODULE_PATHS should need to be specified if oclminify is
	# installed with pip.
	SET(OCLMINIFY_COMMAND "oclminify")
	IF(NOT "${OCLMINIFY_MINIFY_SOURCES_PYTHON_COMMAND}" STREQUAL "")
		SET(OCLMINIFY_COMMAND ${OCLMINIFY_MINIFY_SOURCES_PYTHON_COMMAND} "-m" ${OCLMINIFY_COMMAND})
	ENDIF()

	# Make oclminify run the preprocessor by passing in a temp file instead
	# of using stdin when using MSVC. This is required because MSVC does
	# not support passing source files using stdin.
	SET(OCLMINIFY_MINIFY_SOURCES_PREPROCESSOR_NO_STDIN "")
	IF("${CMAKE_C_COMPILER_ID}" STREQUAL "MSVC")
		SET(OCLMINIFY_MINIFY_SOURCES_PREPROCESSOR_NO_STDIN "--preprocessor-no-stdin")
	ENDIF()

	# Setup each source file to be minified. Each is given a unique global
	# postfix so all kernels can be built and run together without their names
	# colliding.
	SET(SOURCE_INDEX 0)
	SET(OUTPUT_FILE_LIST "")
	FOREACH(_file ${OCLMINIFY_MINIFY_SOURCES_SOURCES})
		GET_FILENAME_COMPONENT(_file_name "${_file}" NAME_WE)
		SET(file_output "${_file_name}${OCLMINIFY_MINIFY_SOURCES_OUTPUT_FILE_POSTFIX}")
		ADD_CUSTOM_COMMAND(
			OUTPUT ${file_output}
			COMMAND ${CMAKE_COMMAND} -E env \"PYTHONPATH=${OCLMINIFY_MINIFY_SOURCES_PYTHON_MODULE_PATHS}\" ${OCLMINIFY_COMMAND} ${OCLMINIFY_MINIFY_SOURCES_OPTIONS} --preprocessor-command="${OCLMINIFY_MINIFY_SOURCES_PREPROCESSOR_COMMAND}" ${OCLMINIFY_MINIFY_SOURCES_PREPROCESSOR_NO_STDIN} --global-postfix="${SOURCE_INDEX}" --output-file="${CMAKE_CURRENT_BINARY_DIR}/${file_output}" "${CMAKE_CURRENT_SOURCE_DIR}/${_file}" 
			DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/${_file}"
		)
		LIST(APPEND OUTPUT_FILE_LIST ${file_output})
		MATH(EXPR SOURCE_INDEX "${SOURCE_INDEX}+1")
	ENDFOREACH()

	# Attach minification to target.
	ADD_CUSTOM_TARGET("oclminify_minify_sources" DEPENDS ${OUTPUT_FILE_LIST})
	ADD_DEPENDENCIES(${OCLMINIFY_MINIFY_SOURCES_TARGET} "oclminify_minify_sources")

	# Setup include path so #include directives can find the minified output
	# header files.
	TARGET_INCLUDE_DIRECTORIES(${OCLMINIFY_MINIFY_SOURCES_TARGET} PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
ENDFUNCTION()
