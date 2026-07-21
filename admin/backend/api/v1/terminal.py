from __future__ import annotations

import fcntl
import os
import pty
import select
import struct
import subprocess
import termios
import uuid
from flask import Blueprint, Response, current_app, jsonify, request
from admin.backend.api.responses import error_response

terminal_bp = Blueprint("terminal", __name__)

# Dictionary holding active shell sessions
# session_id -> {"fd": master_fd, "proc": subprocess.Popen}
sessions: dict[str, dict] = {}


@terminal_bp.post("/session")
def create_session():
    try:
        master_fd, slave_fd = pty.openpty()
        
        # Set master_fd to non-blocking
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        # Spawn shell process tied to the PTY in interactive mode
        bench_root = current_app.config["BENCH_ROOT"]
        proc = subprocess.Popen(
            ["/bin/bash", "-i"],
            preexec_fn=os.setsid,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=str(bench_root),
            env=os.environ.copy()
        )
        
        # Close the slave descriptor in the parent process
        os.close(slave_fd)

        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "fd": master_fd,
            "proc": proc
        }

        return jsonify({"session_id": session_id})
    except Exception as e:
        return error_response("session_creation_failed", f"Failed to spawn terminal session: {e}", 500)


@terminal_bp.get("/stream/<session_id>")
def stream_output(session_id: str):
    session = sessions.get(session_id)
    if not session:
        return error_response("session_not_found", "Terminal session does not exist.", 404)

    def generate():
        fd = session["fd"]
        proc = session["proc"]
        
        # Echo shell path / info on startup
        yield f"data: {b'=== Pilot Shell Console ===\\r\\n'.hex()}\n\n"

        while True:
            if proc.poll() is not None:
                # Process ended
                break
            
            # Use select with timeout to read from PTY master
            r, _, _ = select.select([fd], [], [], 0.05)
            if fd in r:
                try:
                    data = os.read(fd, 4096)
                    if not data:
                        break
                    yield f"data: {data.hex()}\n\n"
                except OSError:
                    break

        # Cleanup process and session keys
        try:
            os.close(fd)
        except OSError:
            pass
        sessions.pop(session_id, None)
        yield "event: close\ndata: session_ended\n\n"

    return Response(generate(), mimetype="text/event-stream")


@terminal_bp.post("/input/<session_id>")
def send_input(session_id: str):
    session = sessions.get(session_id)
    if not session:
        return error_response("session_not_found", "Terminal session does not exist.", 404)

    data_json = request.get_json(silent=True) or {}
    hex_data = data_json.get("data", "")
    if not hex_data:
        return error_response("invalid_request", "hex data is required.", 422)

    try:
        input_bytes = bytes.fromhex(hex_data)
        os.write(session["fd"], input_bytes)
        return jsonify({"success": True})
    except Exception as e:
        return error_response("write_failed", f"Failed to write stdin to shell: {e}", 500)


@terminal_bp.post("/resize/<session_id>")
def resize_terminal(session_id: str):
    session = sessions.get(session_id)
    if not session:
        return error_response("session_not_found", "Terminal session does not exist.", 404)

    data_json = request.get_json(silent=True) or {}
    cols = data_json.get("cols")
    rows = data_json.get("rows")
    if cols is None or rows is None:
        return error_response("invalid_request", "cols and rows are required.", 422)

    try:
        size = struct.pack("HHHH", int(rows), int(cols), 0, 0)
        fcntl.ioctl(session["fd"], termios.TIOCSWINSZ, size)
        return jsonify({"success": True})
    except Exception as e:
        return error_response("resize_failed", f"Failed to resize terminal: {e}", 500)
