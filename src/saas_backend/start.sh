if [ "$APP_MODE" = "dev" ]; then
    echo "🔁 Starting FastAPI in dev mode with hot reload"
    exec uvicorn main:master_app --reload --host 0.0.0.0 --port 8000 --timeout-keep-alive 600
else
    echo "🚀 Starting FastAPI in production mode"
    # We add 600 seconds (10 minutes)
    exec uvicorn main:master_app --host 0.0.0.0 --port 8000 --timeout-keep-alive 600 --proxy-headers --forwarded-allow-ips="*"
fi