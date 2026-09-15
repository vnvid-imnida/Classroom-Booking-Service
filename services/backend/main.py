# Uses PEP 8
# Tools: black, flake8, mypy

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("SERVICE_PORT", "8083"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, log_level="info")
