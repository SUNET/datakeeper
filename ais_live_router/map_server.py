import argparse
import uvicorn
from ais_live_router.webserver.main import app

def main():
    parser = argparse.ArgumentParser(description="Run the AIS Live Router web server.")
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host address to bind the server to (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=80,
        help="Port number to bind the server to (default: 80)",
    )

    args = parser.parse_args()

    config = uvicorn.Config(
        app=app,
        host=args.host,
        port=args.port,
        log_level="info",
        loop="asyncio"
    )
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    # python run_server.py --host 0.0.0.0 --port 8000
    main()
