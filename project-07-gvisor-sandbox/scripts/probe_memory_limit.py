"""P07 Phase 2 (FR-2) memory-ceiling proof.

Allocates well beyond a configured --memory cap. Under an enforced
limit the container should be OOM-killed (nonzero/killed exit) before
this prints its final line; without a limit it completes cleanly.
"""
import sys

MB = 1024 * 1024
chunks = []
try:
    for i in range(1, 401):  # up to ~400MB, well past a 64m cap
        chunks.append(bytearray(MB))
        if i % 50 == 0:
            print(f"allocated {i}MB", flush=True)
    print("DONE: allocated 400MB without being killed", flush=True)
except MemoryError:
    print("MemoryError raised inside the process", flush=True)
    sys.exit(1)
