"""
FastAPI application for the Megabyte Environment.

This module creates an HTTP server that exposes the MegabyteEnvironment
over HTTP and WebSocket endpoints, compatible with EnvClient.

Endpoints:
    - GET /      : Root endpoint for Hugging Face Spaces / browser access
    - GET /health: Health check endpoint
    - POST /reset: Reset the environment
    - POST /step : Execute an action
    - GET /state : Get current environment state
    - GET /schema: Get action/observation schemas
    - WS /ws     : WebSocket endpoint for persistent sessions

Usage:
    # Development (with auto-reload):
    uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4

    # Or run directly:
    python -m server.app
"""

from fastapi.responses import JSONResponse

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:  # pragma: no cover
    raise ImportError(
        "openenv is required for the web interface. Install dependencies before running the server."
    ) from e

try:
    from ..models import MegabyteAction, MegabyteObservation
    from .megabyte_environment import MegabyteEnvironment
except (ModuleNotFoundError, ImportError):
    from models import MegabyteAction, MegabyteObservation
    from server.megabyte_environment import MegabyteEnvironment


# Create the OpenEnv-compatible FastAPI app
app = create_app(
    MegabyteEnvironment,
    MegabyteAction,
    MegabyteObservation,
    env_name="megabyte",
    max_concurrent_envs=1,  # increase this number to allow more concurrent WebSocket sessions
)


@app.get("/")
def root():
    """
    Root endpoint for browser/Hugging Face access.
    Prevents 404 at the Space homepage.
    """
    return JSONResponse(
        {
            "status": "ok",
            "message": "Megabyte Environment server is running.",
            "available_endpoints": [
                "/health",
                "/schema",
                "/reset",
                "/step",
                "/state",
                "/ws",
            ],
        }
    )


@app.get("/health")
def health():
    """
    Health check endpoint.
    """
    return {"status": "healthy"}


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == '__main__':
    main()