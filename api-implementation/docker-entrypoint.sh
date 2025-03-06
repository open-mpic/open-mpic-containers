#!/bin/bash
set -e

# Execute the Python script
exec hatch env run -e production -- python /app/run_uvicorn.py
