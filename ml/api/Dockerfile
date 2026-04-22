FROM python:3.11-slim
WORKDIR /app

COPY requirements_api.txt .
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    -r requirements_api.txt

# Le code source est monté via volume (hot reload) — pas de COPY src
EXPOSE 8000
CMD ["uvicorn", "ml.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
