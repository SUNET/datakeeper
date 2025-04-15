import logging
import uvicorn
import threading
from datakeeper.api.app.main import app


class APIServer:
    def __init__(self, settings, host="0.0.0.0", port=8000):
        self.settings = settings
        self.host = host
        self.port = port
        self.logger = logging.getLogger("APIServer")
        self._stop_event = threading.Event()
        self._server_thread = None

        # Set up the dependency overrides
        app.dependency_overrides[settings] = lambda: self.settings

    def start(self):
        """Start the API server in a separate thread"""
        if self._server_thread is not None and self._server_thread.is_alive():
            self.logger.warning("API server already running")
            return

        self._server_thread = threading.Thread(
            target=self._run_server, daemon=True, name="APIServerThread"
        )
        self._server_thread.start()
        self.logger.info(f"API server started on http://{self.host}:{self.port}")

    def _run_server(self):
        """Run the uvicorn server"""
        config = uvicorn.Config(
            app=app, host=self.host, port=self.port, log_level="info", loop="asyncio"
        )
        server = uvicorn.Server(config)
        server.run()

    def shutdown(self):
        """Shutdown the API server"""
        self._stop_event.set()
        self.logger.info("API server shutdown requested")
        # Note: This doesn't actually stop uvicorn cleanly - you may need a proper shutdown mechanism
