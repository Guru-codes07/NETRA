# One-shot loader image: bakes in the CSVs + loader script at build time
# instead of bind-mounting them from the host. Avoids Docker Desktop
# bind-mount permission issues entirely (chmod/read errors on some
# host filesystems) since everything here is owned by the image itself.

FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir neo4j

COPY Data ./Data
COPY Graph ./Graph

WORKDIR /app/Data

CMD ["python", "../Graph/load_to_neo4j.py"]
