"""FastAPI entrypoint for the Face Emotion Monitor backend."""

from .runtime import app, run_server


if __name__ == "__main__":
    run_server()
