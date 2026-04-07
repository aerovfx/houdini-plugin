"""Pixibox Live Bridge - Socket.IO v4 client for Houdini.

Connects to the server's /bridge Socket.IO namespace using raw WebSocket
(Engine.IO v4 protocol). No python-socketio dependency — uses only
websocket-client which is a single pip install.

Protocol summary (Engine.IO v4 over WebSocket):
  Engine.IO packets:  0=open  2=ping  3=pong  4=message
  Socket.IO packets:  0=connect  2=event  (prefixed inside EIO message packet)

Install websocket-client into Houdini's Python:
  <houdini>/python/bin/python -m pip install websocket-client

See server/src/sockets/index.ts initBridgeNamespace() for the backend.
"""

import json
import os
import re
import threading
import time
import tempfile
from typing import Optional, Callable, Any, Dict, List
import ssl
from queue import Queue, Empty

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

try:
    import hou
    HOUDINI_AVAILABLE = True
except ImportError:
    HOUDINI_AVAILABLE = False
    hou = None


class PixiboxLiveBridge:
    """Socket.IO v4 client for the /bridge namespace.

    Uses a background thread for the WebSocket connection and a
    thread-safe message queue that Houdini operators drain via a timer.
    """

    BASE_URL = "wss://pixibox.ai"
    RECONNECT_DELAY = 5
    MAX_RECONNECT_ATTEMPTS = 10

    def __init__(self, api_key: str, base_url: str = ""):
        if not WEBSOCKET_AVAILABLE:
            raise RuntimeError("websocket-client library not installed")

        self.api_key = api_key
        origin = (base_url or self.BASE_URL).rstrip("/")
        # Convert http(s) to ws(s)
        origin = re.sub(r"^http", "ws", origin)
        # Socket.IO v4 WebSocket transport URL
        self.ws_url = f"{origin}/socket.io/?EIO=4&transport=websocket"

        self.ws: Any = None
        self.thread: Optional[threading.Thread] = None
        self.is_running = False
        self.connected = False
        self.sid: Optional[str] = None
        self.message_queue: Queue = Queue()
        self.callbacks: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self.reconnect_count = 0
        self._ping_interval = 25
        self._ping_timeout = 20

    # ── public API ───────────────────────────────────────────

    def start(self) -> bool:
        """Start the WebSocket connection in a background thread.

        Returns:
            True if started, False otherwise
        """
        if not WEBSOCKET_AVAILABLE:
            if HOUDINI_AVAILABLE and hou:
                hou.ui.displayMessage(
                    "websocket-client not installed. Run: <houdini>/python/bin/python -m pip install websocket-client",
                    severity=hou.severityType.Error
                )
            return False

        if self.is_running:
            return False

        self.is_running = True
        self.connected = False
        self.reconnect_count = 0
        self.thread = threading.Thread(target=self._ws_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        """Disconnect and stop the background thread."""
        self.is_running = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        self.ws = None
        with self._lock:
            self.connected = False

    def is_connected(self) -> bool:
        """Check if connected to bridge.

        Returns:
            True if connected
        """
        with self._lock:
            return self.connected

    def on(self, event: str, callback: Callable):
        """Register a callback for a Socket.IO event.

        Args:
            event: Event name (e.g. 'dcc_push', 'generation_complete')
            callback: fn(data_dict) — called from the WS thread
        """
        self.callbacks[event] = callback

    def emit(self, event: str, data: Any = None) -> bool:
        """Emit a Socket.IO event to the /bridge namespace.

        Args:
            event: Event name
            data: JSON-serializable payload

        Returns:
            True if sent, False otherwise
        """
        if not self.connected or not self.ws:
            return False
        # Socket.IO event packet: 42/bridge,["event", data]
        payload = json.dumps([event, data] if data is not None else [event])
        packet = f"42/bridge,{payload}"
        try:
            self.ws.send(packet)
            return True
        except Exception:
            return False

    def get_messages(self) -> List[dict]:
        """Drain all queued messages (thread-safe).

        Returns:
            List of message dicts with 'type', 'data', 'timestamp'
        """
        msgs = []
        try:
            while True:
                msgs.append(self.message_queue.get_nowait())
        except Empty:
            pass
        return msgs

    # ── internal ─────────────────────────────────────────────

    def _ws_loop(self):
        """Reconnect loop running in the background thread."""
        while self.is_running:
            try:
                self._connect_and_listen()
            except Exception as e:
                print(f"[Pixibox Bridge] Error: {e}")
                with self._lock:
                    self.connected = False

            if not self.is_running:
                break

            if self.reconnect_count >= self.MAX_RECONNECT_ATTEMPTS:
                print("[Pixibox Bridge] Max reconnect attempts reached — giving up")
                break

            self.reconnect_count += 1
            delay = min(self.RECONNECT_DELAY * (2 ** self.reconnect_count), 60)
            print(f"[Pixibox Bridge] Reconnecting in {delay}s (attempt {self.reconnect_count})…")
            time.sleep(delay)

    def _connect_and_listen(self):
        """Single connection lifecycle."""
        if not WEBSOCKET_AVAILABLE:
            raise RuntimeError("websocket-client not installed")

        sslopt = {"cert_reqs": ssl.CERT_REQUIRED}

        self.ws = websocket.WebSocket(sslopt=sslopt)
        self.ws.connect(self.ws_url)

        # 1) Receive Engine.IO OPEN packet: 0{...}
        raw = self.ws.recv()
        if not raw or raw[0] != '0':
            raise RuntimeError(f"Expected EIO open, got: {raw[:80] if raw else 'None'}")

        eio_data = json.loads(raw[1:])
        self.sid = eio_data.get("sid")
        self._ping_interval = eio_data.get("pingInterval", 25000) / 1000
        self._ping_timeout = eio_data.get("pingTimeout", 20000) / 1000

        # 2) Send Socket.IO CONNECT to /bridge namespace with auth token
        connect_packet = f'40/bridge,{json.dumps({"token": self.api_key})}'
        self.ws.send(connect_packet)

        # 3) Receive Socket.IO CONNECT ack: 40/bridge,{...}
        raw = self.ws.recv()
        if raw and raw.startswith("40/bridge"):
            with self._lock:
                self.connected = True
            self.reconnect_count = 0
            print("[Pixibox Bridge] Connected to /bridge namespace")
        else:
            raise RuntimeError(f"Bridge connect failed: {raw[:120] if raw else 'None'}")

        # 4) Listen loop
        self.ws.settimeout(self._ping_interval + self._ping_timeout)
        while self.is_running:
            try:
                raw = self.ws.recv()
                if raw is None or raw == '':
                    break
                self._handle_packet(raw)
            except websocket.WebSocketTimeoutException:
                # No data within ping window — send a ping ourselves
                try:
                    self.ws.send("2")
                except Exception:
                    break
            except websocket.WebSocketConnectionClosedException:
                break
            except Exception as e:
                print(f"[Pixibox Bridge] Recv error: {e}")
                break

        with self._lock:
            self.connected = False

    def _handle_packet(self, raw: str):
        """Parse Engine.IO / Socket.IO packets.

        Args:
            raw: Raw packet string
        """
        if not raw:
            return

        eio_type = raw[0]

        if eio_type == '2':
            # Engine.IO PING → respond with PONG
            try:
                self.ws.send("3")
            except Exception:
                pass
            return

        if eio_type == '3':
            # Engine.IO PONG — ignore
            return

        if eio_type == '4':
            # Engine.IO MESSAGE → contains a Socket.IO packet
            sio_raw = raw[1:]
            self._handle_sio_packet(sio_raw)
            return

        # Try to parse as a bare Socket.IO event (42/bridge,[...])
        self._handle_sio_packet(raw)

    def _handle_sio_packet(self, raw: str):
        """Parse a Socket.IO packet.

        Args:
            raw: Raw Socket.IO packet string
        """
        if not raw:
            return

        sio_type = raw[0]

        if sio_type == '2':
            # Socket.IO EVENT
            # Format: 2/bridge,["event_name", {...}]  or  42/bridge,["event_name",{...}]
            rest = raw[1:]
            # Strip namespace prefix
            if rest.startswith("/bridge,"):
                rest = rest[len("/bridge,"):]

            try:
                arr = json.loads(rest)
                if isinstance(arr, list) and len(arr) >= 1:
                    event = arr[0]
                    data = arr[1] if len(arr) > 1 else {}
                    self._dispatch_event(event, data)
            except json.JSONDecodeError:
                pass
            return

        if sio_type == '0':
            # Socket.IO CONNECT (namespace ack) — already handled
            return

        if sio_type == '1':
            # Socket.IO DISCONNECT
            print("[Pixibox Bridge] Server disconnected namespace")
            return

        if sio_type == '4':
            # Socket.IO ERROR
            print(f"[Pixibox Bridge] Server error: {raw}")
            return

    def _dispatch_event(self, event: str, data: Any):
        """Route a received Socket.IO event to callbacks and the message queue.

        Args:
            event: Event name
            data: Event payload
        """
        msg = {"type": event, "data": data, "timestamp": time.time()}
        self.message_queue.put(msg)

        if event in self.callbacks:
            try:
                self.callbacks[event](data)
            except Exception as e:
                print(f"[Pixibox Bridge] Callback error ({event}): {e}")

        # Handle well-known events with default logging
        if event == "ping":
            # Server keepalive — respond
            self.emit("pong", {})
        elif event == "dcc_push":
            print(f"[Pixibox Bridge] Received dcc_push: {len(data.get('models', []))} model(s)")
        elif event == "generation_complete":
            gid = data.get("generation_id", "?")
            print(f"[Pixibox Bridge] Generation complete: {gid}")
        elif event == "generation_progress":
            gid = data.get("generation_id", "?")
            pct = data.get("progress", "?")
            print(f"[Pixibox Bridge] Progress {gid}: {pct}%")
        elif event == "generation_failed":
            gid = data.get("generation_id", "?")
            err = data.get("errorMessage", "unknown")
            print(f"[Pixibox Bridge] Generation failed {gid}: {err}")


# ── Helper: download models for Houdini import ──────────────────

def download_glb_for_import(url: str, filename: str = "pixibox_push.glb") -> Optional[str]:
    """Download a GLB file to a temp directory, return the local path.

    Args:
        url: Public URL of the .glb file
        filename: Filename to save as

    Returns:
        Local file path, or None on failure
    """
    import urllib.request
    try:
        dest = os.path.join(tempfile.gettempdir(), filename)
        urllib.request.urlretrieve(url, dest)
        return dest
    except Exception as e:
        print(f"[Pixibox Bridge] Download GLB failed: {e}")
        return None


def download_usd_for_import(url: str, filename: str = "pixibox_push.usda") -> Optional[str]:
    """Download a USD file to a temp directory, return the local path.

    Args:
        url: Public URL of the .usda or .usdz file
        filename: Filename to save as

    Returns:
        Local file path, or None on failure
    """
    import urllib.request
    try:
        dest = os.path.join(tempfile.gettempdir(), filename)
        urllib.request.urlretrieve(url, dest)
        return dest
    except Exception as e:
        print(f"[Pixibox Bridge] Download USD failed: {e}")
        return None


# ── Global bridge instance and control functions ──────────────────

_live_bridge_instance: Optional[PixiboxLiveBridge] = None


def start_live_bridge(api_key: str, base_url: str = "") -> tuple[bool, str]:
    """Start the Live Bridge.

    Args:
        api_key: Pixibox API key
        base_url: Optional custom base URL (default: wss://pixibox.ai)

    Returns:
        Tuple of (success, message)
    """
    global _live_bridge_instance

    try:
        if _live_bridge_instance and _live_bridge_instance.connected:
            return False, "Live Bridge already connected"

        _live_bridge_instance = PixiboxLiveBridge(api_key, base_url)

        if _live_bridge_instance.start():
            # Give it a moment to connect
            for _ in range(50):  # 5 second timeout
                if _live_bridge_instance.connected:
                    return True, "Live Bridge connected"
                time.sleep(0.1)

            return True, "Live Bridge starting (connecting...)"
        else:
            return False, "Failed to start Live Bridge"

    except Exception as e:
        return False, str(e)


def stop_live_bridge() -> tuple[bool, str]:
    """Stop the Live Bridge.

    Returns:
        Tuple of (success, message)
    """
    global _live_bridge_instance

    try:
        if not _live_bridge_instance:
            return False, "Live Bridge not initialized"

        _live_bridge_instance.stop()
        _live_bridge_instance = None
        return True, "Live Bridge disconnected"

    except Exception as e:
        return False, str(e)


def get_live_bridge() -> Optional[PixiboxLiveBridge]:
    """Get the global Live Bridge instance.

    Returns:
        Bridge instance or None
    """
    return _live_bridge_instance


def is_live_bridge_connected() -> bool:
    """Check if Live Bridge is connected.

    Returns:
        True if connected
    """
    return _live_bridge_instance is not None and _live_bridge_instance.connected
