AUDIOCPP_REPO   := https://github.com/0xShug0/audio.cpp
AUDIOCPP_COMMIT := e3e1bc7c767776baad9a1f2a07317a8dc26bc98d
AUDIOCPP_DIR    := thirdparty/audio.cpp
BUILD_DIR       := build/dev
JOBS            ?= $(shell nproc 2>/dev/null || sysctl -n hw.ncpu)
# Extra CMake flags, e.g. make lib CMAKE_ARGS=-DENGINE_ENABLE_CUDA=ON
CMAKE_ARGS      ?=

ifeq ($(shell uname -s),Darwin)
LIBNAME := libaudiocpp.dylib
else
LIBNAME := libaudiocpp.so
endif

.PHONY: all sync lib test models wheel repair clean reset

all: lib

$(AUDIOCPP_DIR)/CMakeLists.txt:
	git clone --filter=blob:none $(AUDIOCPP_REPO) $(AUDIOCPP_DIR)
	git -C $(AUDIOCPP_DIR) checkout --quiet $(AUDIOCPP_COMMIT)

sync: $(AUDIOCPP_DIR)/CMakeLists.txt

# Builds libaudiocpp and installs it next to the Python sources.
lib: sync
	cmake -S . -B $(BUILD_DIR) -DCMAKE_BUILD_TYPE=Release $(CMAKE_ARGS)
	cmake --build $(BUILD_DIR) --target audiocpp -j $(JOBS)
	cmake --install $(BUILD_DIR) --prefix src

test:
	uv run pytest -q

HF_GGUF := https://huggingface.co/audio-cpp/audio.cpp-gguf/resolve/main
TEST_MODELS := \
	Kokoro-82M-GGUF/kokoro-82m-q8_0.gguf \
	Citrinet-ASR-GGUF/citrinet-asr-q8_0.gguf \
	Moonshine-Streaming-GGUF/moonshine-streaming-tiny-q8_0.gguf \
	Sortformer-Diar-4spk-v1-GGUF/sortformer-diar-4spk-v1-q8_0.gguf \
	HTDemucs-GGUF/htdemucs-q8_0.gguf

# About 530 MB; tests/test_models.py skips whatever is missing.
models: $(addprefix models/,$(TEST_MODELS))

models/%.gguf:
	@mkdir -p $(dir $@)
	curl -fL --retry 3 -o $@.part $(HF_GGUF)/$*.gguf && mv $@.part $@

wheel: sync
	uv build --wheel

# Vendor non-system libraries (libgomp) and retag for the host glibc. A
# manylinux_2_28 wheel for PyPI must be built in a manylinux image (cibuildwheel).
repair:
	uvx auditwheel repair -w dist/repaired dist/pyaudiocpp-*-linux_*.whl

clean:
	rm -rf build dist src/pyaudiocpp/$(LIBNAME) src/pyaudiocpp/audiocpp.dll

reset: clean
	rm -rf $(AUDIOCPP_DIR)
