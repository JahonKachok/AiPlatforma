@echo off
env\Scripts\activate && uvicorn core.asgi:application --host 0.0.0.0 --port 3031 --workers 4 --log-level debuge