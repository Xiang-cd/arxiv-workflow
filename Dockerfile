FROM python:3.10

WORKDIR /app

COPY . .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
EXPOSE 8000
CMD ["fastapi", "run", "server.py", "--host", "127.0.0.1"]