"""ctypes bindings for audio.cpp's C ABI (include/audiocpp.h)."""

from .core import *  # noqa: F403
from .core import __all__ as _core_all
from .wav import read_wav, write_wav

__version__ = "0.1.0"

__all__ = [*_core_all, "read_wav", "write_wav"]
