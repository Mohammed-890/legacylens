FROM python:3.13-slim
WORKDIR /app
COPY legacylens ./legacylens
COPY fixtures ./fixtures
COPY web ./web
USER 10001:10001
ENV PYTHONDONTWRITEBYTECODE=1
EXPOSE 8765
CMD ["python", "-m", "legacylens.server", "--host", "0.0.0.0"]
