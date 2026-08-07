"""Syscall-interception probe for P07 Phase 1 (FR-1).

Calls io_uring_setup(2) directly via ctypes. Run identically under
--runtime=runc and --runtime=runsc to show gVisor's sentry answers
guest syscalls itself rather than passing them to the host kernel:
the real kernel implements io_uring_setup; gVisor's sentry does not.
"""
import ctypes
import os

libc = ctypes.CDLL(None, use_errno=True)
buf = ctypes.create_string_buffer(128)  # struct io_uring_params, zeroed

# io_uring_setup(entries, params) — syscall number 425 on x86_64
ret = libc.syscall(425, ctypes.c_uint(4), buf)
err = ctypes.get_errno()

print(f"io_uring_setup() -> ret={ret} errno={err} ({os.strerror(err) if err else 'none'})")
if err == 38:  # ENOSYS
    print("RESULT: syscall not implemented (ENOSYS) -- intercepted and rejected by the sentry")
elif ret >= 0:
    print("RESULT: syscall succeeded -- ring created, fd returned by the real kernel")
    os.close(ret)
else:
    print("RESULT: syscall reached a kernel and was rejected for other reasons (not ENOSYS)")
