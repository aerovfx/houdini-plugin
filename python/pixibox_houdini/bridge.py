"""
Live WebSocket bridge for real-time Pixibox generation updates.

Connects to Pixibox.ai WebSocket server to receive generation progress
in real-time, with thread-safe callback support for Houdini environment.
"""

import os
import json
import threading
import time
from typing import Callable, Optional, Dict, Any
from queue import Queue
import websocket

try:
    import hou
except ImportError:
    hou = None  # type: ignore


class PixiboxBridge:
    """
    WebSocket client for real-time generation updates.

    Maintains persistent connection to Pixibox backend and dispatches
    generation status updates via thread-safe callbacks.

    Args:
        endpoint (str, optional): WebSocket endpoint. Defaults to
                                 wss://pixibox.ai/ws
        token (str, optional): Auth token (reads PIXIBOX_AUTH_TOKEN if not set)
        auto_reconnect (bool): Automatically reconnect on disconnect

    Example:
        >>> bridge = PixiboxBridge(token="...")
        >>> bridge.on_generation_update(
        ...     lambda gen: print(f"Status: {gen['status']}")
        ... )
        >>> bridge.connect()
        >>> bridge.wait(timeout=300)  # Wait up to 5 min for completion
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        token: Optional[str] = None,
        auto_reconnect: bool = True,
    ) -> None:
        self.endpoint = endpoint or os.getenv(
            "PIXIBOX_WEBSOCKET_ENDPOINT",
            "wss://pixibox.ai/ws"
        )
        self.token = token or os.getenv("PIXIBOX_AUTH_TOKEN", "")
        self.auto_reconnect = auto_reconnect

        if not self.token:
            raise ValueError(
                "PIXIBOX_AUTH_TOKEN not set. Set via parameter or environment."
            )

        self._ws: Optional[websocket.WebSocket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._callbacks: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self._event_queue: Queue = Queue()
        self._lock = threading.RLock()

    def on_generation_update(
        self,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Register callback for generation status updates.

        Callback receives dict with keys:
            - id: Generation ID
            - status: "pending", "processing", "completed", "failed"
            - progress: 0-100 (for processing status)
            - model: AI provider
            - timestamp: Unix timestamp

        Args:
            callback: Function taking generation dict as argument

        Example:
            >>> def on_update(gen):
            ...     print(f"{gen['id']}: {gen['status']} ({gen.get('progress', 0)}%)")
            >>> bridge.on_generation_update(on_update)
        """
        with self._lock:
            self._callbacks["generation_update"] = callback

    def on_error(
        self,
        callback: Callable[[str], None],
    ) -> None:
        """
        Register error callback.

        Args:
            callback: Function taking error message (str) as argument
        """
        with self._lock:
            self._callbacks["error"] = callback

    def on_connected(
        self,
        callback: Callable[[], None],
    ) -> None:
        """
        Register callback for successful connection.

        Args:
            callback: Function with no arguments
        """
        with self._lock:
            self._callbacks["connected"] = callback

    def connect(self) -> None:
        """
        Connect to WebSocket server and start listening.

        Spawns background thread to handle incoming messages.
        Thread-safe and can be called multiple times.
        """
        with self._lock:
            if self._running:
                return

            self._running = True

        try:
            # Enable websocket debug logging if PIXIBOX_DEBUG set
            if os.getenv("PIXIBOX_DEBUG"):
                websocket.enableTrace(True)

            self._ws = websocket.WebSocketApp(
                self.endpoint,
                header={f"Authorization: Bearer {self.token}"},
                on_message=self._on_message,
                on_error=self._on_ws_error,
                on_close=self._on_close,
                on_open=self._on_open,
            )

            # Run in background thread
            self._thread = threading.Thread(
                target=self._ws.run_forever,
                daemon=False,
            )
            self._thread.start()

        except Exception as e:
            self._running = False
            self._dispatch_callback("error", f"Connection failed: {str(e)}")
            raise

    def disconnect(self) -> None:
        """
        Close WebSocket connection and stop listening.

        Thread-safe. Waits for background thread to finish.
        """
        with self._lock:
            if not self._running:
                return

            self._running = False

        if self._ws:
            self._ws.close()

        if self._thread:
            self._thread.join(timeout=5)

    def wait(
        self,
        timeout: Optional[int] = None,
        generation_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Block until generation completes or timeout.

        Useful for waiting for specific generation to finish
        before proceeding with import.

        Args:
            timeout: Max seconds to wait (None = infinite)
            generation_id: Wait for specific generation (optional)

        Returns:
            Final generation status dict, or None if timeout

        Example:
            >>> bridge = PixiboxBridge()
            >>> final_gen = bridge.wait(timeout=300)
            >>> if final_gen and final_gen["status"] == "completed":
            ...     import_to_stage(final_gen["id"])
        """
        start_time = time.time()
        last_gen: Optional[Dict[str, Any]] = None

        def capture_update(gen: Dict[str, Any]) -> None:
            nonlocal last_gen
            if generation_id is None or gen.get("id") == generation_id:
                last_gen = gen

        with self._lock:
            old_callback = self._callbacks.get("generation_update")
            self._callbacks["generation_update"] = capture_update

        try:
            while self._running:
                if timeout and (time.time() - start_time) > timeout:
                    return None

                # Houdini-safe wait (non-blocking)
                if hou:
                    hou.ui.updateUI()

                time.sleep(0.1)

                if last_gen and last_gen.get("status") in ("completed", "failed"):
                    return last_gen

            return last_gen
        finally:
            with self._lock:
                if old_callback:
                    self._callbacks["generation_update"] = old_callback
                else:
                    self._callbacks.pop("generation_update", None)

    def _on_message(self, ws: Any, message: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")

            if msg_type == "generation_update":
                self._dispatch_callback("generation_update", data.get("payload", {}))
            elif msg_type == "error":
                self._dispatch_callback("error", data.get("message", "Unknown error"))

        except Exception as e:
            self._dispatch_callback("error", f"Message parse error: {str(e)}")

    def _on_open(self, ws: Any) -> None:
        """Handle WebSocket connection opened."""
        self._dispatch_callback("connected")

    def _on_ws_error(self, ws: Any, error: Exception) -> None:
        """Handle WebSocket error."""
        self._dispatch_callback("error", f"WebSocket error: {str(error)}")

        if self.auto_reconnect and self._running:
            time.sleep(5)
            try:
                self.connect()
            except Exception:
                pass

    def _on_close(self, ws: Any, close_status_code: int, close_msg: str) -> None:
        """Handle WebSocket connection closed."""
        if self._running and self.auto_reconnect:
            time.sleep(5)
            try:
                self.connect()
            except Exception:
                pass

    def _dispatch_callback(self, callback_type: str, data: Any = None) -> None:
        """
        Dispatch callback in Houdini-safe way.

        Uses event queue to avoid threading issues in Houdini.
        """
        with self._lock:
            callback = self._callbacks.get(callback_type)
            if not callback:
                return

        # Queue for safe execution
        self._event_queue.put((callback, data))

        # Try to execute if possible
        try:
            callback, event_data = self._event_queue.get_nowait()
            if event_data is not None:
                callback(event_data)
            else:
                callback()
        except Exception:
            # Queue operations may fail outside Houdini context
            pass

    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        return self._running and self._ws is not None and self._ws.sock is not None
