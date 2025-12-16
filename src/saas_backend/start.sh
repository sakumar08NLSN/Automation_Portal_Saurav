
if [ "$APP_MODE" = "dev" ]; then
    echo "🔁 Starting FastAPI in dev mode with hot reload"
    exec uvicorn main:master_app  --reload --host 0.0.0.0 --port 8000
else
    echo "🚀 Starting FastAPI in production mode"
    exec uvicorn main:master_app  --host 0.0.0.0 --port 8000
fi