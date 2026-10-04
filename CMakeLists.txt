cmake_minimum_required(VERSION 3.20)
project(pyaudiocpp LANGUAGES C CXX)

# Backends are selected with audio.cpp's own options, e.g.
#   CMAKE_ARGS="-DENGINE_ENABLE_CUDA=ON" uv build --wheel
set(AUDIOCPP_DIR "${CMAKE_CURRENT_SOURCE_DIR}/thirdparty/audio.cpp" CACHE PATH "audio.cpp source tree")
execute_process(
    COMMAND git rev-parse --short HEAD
    WORKING_DIRECTORY "${AUDIOCPP_DIR}"
    OUTPUT_VARIABLE _audiocpp_rev OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
if(_audiocpp_rev)
    set(AUDIOCPP_VERSION "git-${_audiocpp_rev}")
endif()
set(AUDIOCPP_BUILD_C_API ON CACHE BOOL "" FORCE)
# Compile model_specs/*.json into the library so a wheel needs no spec directory.
set(AUDIOCPP_DEPLOYMENT_BUILD ON CACHE BOOL "" FORCE)

# Portable: no -march=native. ggml then enables SSE4.2..AVX2/FMA/F16C/BMI2 by
# default (x86-64-v3), a single library rather than audio.cpp's
# ENGINE_ENABLE_CPU_ALL_VARIANTS, which needs dlopen'd per-ISA backends.
option(PYAUDIOCPP_PORTABLE "Target a portable ISA baseline instead of the build host" OFF)
if(PYAUDIOCPP_PORTABLE)
    set(ENGINE_ENABLE_NATIVE_CPU OFF CACHE BOOL "" FORCE)
endif()

add_subdirectory("${AUDIOCPP_DIR}" audiocpp EXCLUDE_FROM_ALL)

# A single unversioned file: wheels cannot carry the .so -> .so.0 symlink chain,
# and ctypes loads the library by path, so no SONAME is needed.
set_property(TARGET audiocpp PROPERTY VERSION)
set_property(TARGET audiocpp PROPERTY SOVERSION)

if(NOT DEFINED SKBUILD_PROJECT_NAME)
    set(SKBUILD_PROJECT_NAME pyaudiocpp)
endif()
install(TARGETS audiocpp
    LIBRARY DESTINATION ${SKBUILD_PROJECT_NAME}
    RUNTIME DESTINATION ${SKBUILD_PROJECT_NAME})
