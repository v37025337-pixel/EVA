"""Resource-bounded execution of the small repair language in a clean process.

The worker is reused to avoid starting Python for every repair candidate. Only
compiled code is cached: arguments, function defaults and globals are new on
each call. No pickle or caller-provided objects cross the process boundary.
This is a bounded language executor, not an arbitrary Python sandbox.
"""
from __future__ import annotations

import ast
import atexit
import builtins
from fractions import Fraction
from functools import lru_cache
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import threading
import time

MAX_SOURCE_BYTES = 65536
MAX_WIRE_BYTES = 2 * 1024 * 1024
MAX_VALUE_NODES = 20000
MAX_VALUE_DEPTH = 40
MAX_SCALAR_BYTES = 256 * 1024
MAX_INTEGER_BITS = 8192
MEMORY_BYTES = 256 * 1024 * 1024
CPU_SECONDS = 0.25
WALL_SECONDS = 1.0
ALLOWED_BUILTINS = frozenset(("min", "max", "all", "any", "sum", "abs", "len", "int", "float", "str"))
ALLOWED_ATTRIBUTES = frozenset(("get", "items"))


def _encode(value, depth=0, budget=None):
    budget = [MAX_VALUE_NODES, MAX_WIRE_BYTES] if budget is None else budget
    budget[0] -= 1
    budget[1] -= 24
    if depth > MAX_VALUE_DEPTH or budget[0] < 0 or budget[1] < 0:
        raise ValueError("PROGRAM_VALUE_BUDGET")
    kind = type(value)
    if value is None:
        return ["none"]
    if kind is bool:
        return ["bool", value]
    if kind is int:
        if value.bit_length() > MAX_INTEGER_BITS:
            raise ValueError("PROGRAM_INTEGER_BUDGET")
        budget[1] -= value.bit_length() // 3 + 1
        return ["int", str(value)]
    if kind is float:
        return ["float", value.hex()]
    if kind is complex:
        return ["complex", value.real.hex(), value.imag.hex()]
    if kind is Fraction:
        return ["fraction", _encode(value.numerator, depth + 1, budget), _encode(value.denominator, depth + 1, budget)]
    if kind in (str, bytes):
        if len(value) > MAX_SCALAR_BYTES:
            raise ValueError("PROGRAM_SCALAR_BUDGET")
        # Reserve a conservative JSON-escaped size before allocating the wire
        # representation, including repeated references to the same large value.
        budget[1] -= len(value) * (12 if kind is str else 2)
        if budget[1] < 0:
            raise ValueError("PROGRAM_VALUE_BUDGET")
        return ["str", value] if kind is str else ["bytes", value.hex()]
    if kind in (list, tuple, set, frozenset):
        return [kind.__name__, [_encode(x, depth + 1, budget) for x in value]]
    if kind is dict:
        return ["dict", [[_encode(k, depth + 1, budget), _encode(v, depth + 1, budget)] for k, v in value.items()]]
    raise ValueError("PROGRAM_VALUE_TYPE_NOT_ALLOWED:" + kind.__name__)


def _decode(value):
    tag = value[0]
    if tag == "none":
        return None
    if tag in ("bool", "str"):
        return value[1]
    if tag == "int":
        return int(value[1])
    if tag == "float":
        return float.fromhex(value[1])
    if tag == "complex":
        return complex(float.fromhex(value[1]), float.fromhex(value[2]))
    if tag == "fraction":
        return Fraction(_decode(value[1]), _decode(value[2]))
    if tag == "bytes":
        return bytes.fromhex(value[1])
    if tag == "dict":
        return {_decode(k): _decode(v) for k, v in value[1]}
    constructor = {"list": list, "tuple": tuple, "set": set, "frozenset": frozenset}.get(tag)
    if constructor is None:
        raise ValueError("PROGRAM_WIRE_TYPE")
    return constructor(_decode(x) for x in value[1])


def equivalent(a, b):
    """Successor-style sequence equality with type-aware booleans at every level."""
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(equivalent(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        if len(a) != len(b):
            return False
        remaining = list(b.items())
        for key, value in a.items():
            for index, (other_key, other_value) in enumerate(remaining):
                if equivalent(key, other_key) and equivalent(value, other_value):
                    remaining.pop(index)
                    break
            else:
                return False
        return True
    if isinstance(a, (set, frozenset)) and isinstance(b, (set, frozenset)):
        if len(a) != len(b):
            return False
        remaining = list(b)
        for value in a:
            for index, other in enumerate(remaining):
                if equivalent(value, other):
                    remaining.pop(index)
                    break
            else:
                return False
        return True
    return a == b


@lru_cache(maxsize=256)
def _compile(source, name, safe_names, safe_attributes):
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise ValueError("PROGRAM_SOURCE_BUDGET")
    tree = ast.parse(source)
    banned = (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.With,
              ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda, ast.While, ast.For,
              ast.AsyncFor, ast.Try, ast.Raise, ast.Yield, ast.YieldFrom, ast.Await, ast.Delete)
    if (len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef)
            or tree.body[0].name != name or tree.body[0].decorator_list):
        raise ValueError("PROGRAM_FUNCTION_CONTRACT")
    for node in ast.walk(tree):
        if isinstance(node, banned):
            raise ValueError("UNSAFE_PROGRAM")
        if isinstance(node, ast.Attribute) and node.attr not in safe_attributes:
            raise ValueError("UNSAFE_ATTRIBUTE")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id not in safe_names:
                    raise ValueError("CALL_NOT_ALLOWED")
            elif not (isinstance(node.func, ast.Attribute) and node.func.attr in safe_attributes):
                raise ValueError("UNSAFE_CALL")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("DUNDER_FORBIDDEN")
    return compile(tree, "<yado-isolated-program>", "exec")


def _deadline(signum, frame):
    raise TimeoutError("PROGRAM_CPU_LIMIT")


def _worker():
    import resource
    # Fail closed on platforms without the actual OS limits.
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 31))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    signal.signal(signal.SIGPROF, _deadline)
    for _ in range(10000):
        raw = sys.stdin.buffer.readline(MAX_WIRE_BYTES + 1)
        if not raw:
            return
        if len(raw) > MAX_WIRE_BYTES or not raw.endswith(b"\n"):
            return
        try:
            signal.setitimer(signal.ITIMER_PROF, CPU_SECONDS)
            request = json.loads(raw)
            source, name, arguments, names, attributes = request
            names, attributes = tuple(names), tuple(attributes)
            if not set(names) <= ALLOWED_BUILTINS or not set(attributes) <= ALLOWED_ATTRIBUTES:
                raise ValueError("PROGRAM_BUILTIN_CONTRACT")
            code = _compile(source, name, names, attributes)
            env = {name: getattr(builtins, name) for name in names}
            env["__builtins__"] = {}
            exec(code, env, env)
            result = env[name](*_decode(arguments))
            usage = resource.getrusage(resource.RUSAGE_SELF)
            response = ["ok", _encode(result), usage.ru_utime + usage.ru_stime >= 20]
            encoded = json.dumps(response, ensure_ascii=True, separators=(",", ":")).encode() + b"\n"
            if len(encoded) > MAX_WIRE_BYTES:
                raise ValueError("PROGRAM_OUTPUT_BUDGET")
        except BaseException as error:
            encoded = json.dumps(["error", type(error).__name__, str(error)[:300]]).encode() + b"\n"
        finally:
            signal.setitimer(signal.ITIMER_PROF, 0)
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()


class _Executor:
    def __init__(self):
        self.process = None
        self.lock = threading.Lock()
        self.owner = os.getpid()
        self.calls = 0

    def close(self):
        process, self.process = self.process, None
        if process is not None:
            if self.owner == os.getpid() and process.poll() is None:
                process.kill()
            if self.owner == os.getpid():
                process.wait(timeout=2)
            process.stdin.close()
            process.stdout.close()

    def _start(self):
        if os.name != "posix":
            raise RuntimeError("PROGRAM_OS_LIMITS_UNAVAILABLE")
        self.process = subprocess.Popen(
            [sys.executable, "-I", "-S", str(Path(__file__).resolve()), "--worker"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            close_fds=True, start_new_session=True, bufsize=0,
            env={"PATH": os.defpath, "LANG": "C.UTF-8"}, cwd="/",
        )
        os.set_blocking(self.process.stdin.fileno(), False)
        os.set_blocking(self.process.stdout.fileno(), False)
        self.calls = 0

    def execute(self, request):
        raw = json.dumps(request, ensure_ascii=True, separators=(",", ":")).encode() + b"\n"
        if len(raw) > MAX_WIRE_BYTES:
            raise ValueError("PROGRAM_INPUT_BUDGET")
        with self.lock:
            if self.process is not None and (self.process.poll() is not None or self.calls >= 9000):
                self.close()
            if self.process is None:
                self._start()
            process = self.process
            deadline = time.monotonic() + WALL_SECONDS
            try:
                sent = 0
                while sent < len(raw):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not select.select([], [process.stdin], [], remaining)[1]:
                        raise TimeoutError("PROGRAM_WALL_LIMIT")
                    sent += os.write(process.stdin.fileno(), raw[sent:])
                received = bytearray()
                while not received.endswith(b"\n"):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
                        raise TimeoutError("PROGRAM_WALL_LIMIT")
                    chunk = os.read(process.stdout.fileno(), 65536)
                    if not chunk:
                        raise RuntimeError("PROGRAM_WORKER_LIMIT_OR_EXIT")
                    received.extend(chunk)
                    if len(received) > MAX_WIRE_BYTES:
                        raise ValueError("PROGRAM_OUTPUT_BUDGET")
                response = json.loads(received)
                self.calls += 1
            except BaseException:
                self.close()
                raise
            if response[0] != "ok":
                kind = {"TimeoutError": TimeoutError, "MemoryError": MemoryError,
                        "ZeroDivisionError": ZeroDivisionError, "TypeError": TypeError,
                        "ValueError": ValueError, "IndexError": IndexError, "KeyError": KeyError,
                        "OverflowError": OverflowError, "NameError": NameError}.get(response[1], ValueError)
                if kind in (TimeoutError, MemoryError):
                    self.close()
                raise kind("PROGRAM_EXECUTION:" + response[2])
            result = _decode(response[1])
            if response[2]:
                self.close()
            return result


_EXECUTOR = _Executor()
atexit.register(_EXECUTOR.close)


def execute(source, function_name, arguments, safe_calls, safe_attributes=()):
    global _EXECUTOR
    if os.getpid() != _EXECUTOR.owner:
        _EXECUTOR.close()
        _EXECUTOR = _Executor()
        atexit.register(_EXECUTOR.close)
    if type(source) is not str or len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise ValueError("PROGRAM_SOURCE_BUDGET")
    if type(function_name) is not str or len(function_name) > 256:
        raise ValueError("PROGRAM_FUNCTION_CONTRACT")
    if any(name not in ALLOWED_BUILTINS or fn is not getattr(builtins, name) for name, fn in safe_calls.items()):
        raise ValueError("PROGRAM_BUILTIN_CONTRACT")
    if not set(safe_attributes) <= ALLOWED_ATTRIBUTES:
        raise ValueError("PROGRAM_ATTRIBUTE_CONTRACT")
    return _EXECUTOR.execute([source, function_name, _encode(arguments), sorted(safe_calls), sorted(safe_attributes)])


if __name__ == "__main__":
    if sys.argv[1:] != ["--worker"]:
        raise SystemExit("worker mode required")
    _worker()
