#!/usr/bin/env bash

# This command starts the Uvicorn server, using 0.0.0.0 and the port provided by Render
# We use 'main:master_app' as verified previously.
exec uvicorn main:master_app --host 0.0.0.0 --port $PORT