#--------------------- STAGE 1: Builder ---------------------
FROM python:3.12-slim as builder

RUN apt-get update && apt-get install -y \
build-essential \
git \
libpq-dev \
libgl1-mesa-glx \
libglib2.0-0 \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --user -r requirements.txt

ENV HF_HOME=/root/.cache/huggingface
ENV TRANSFORMERS_CACHE=/root/.cache/huggingface/transformers

RUN python - <<EOF
from huggingface_hub import snapshot_download
snapshot_download(
  "microsoft/Florence-2-base",
  cache_dir="/root/.cache/huggingface/hub",
  library_name="transformers",
  library_version="4.x"
)
snapshot_download(
  "patrickjohncyh/fashion-clip",
  cache_dir="/root/.cache/huggingface/hub",
  library_name="transformers",
  library_version="4.x"
)
EOF

RUN python -c "from transformers import CLIPModel, CLIPProcessor; \
    CLIPModel.from_pretrained('patrickjohncyh/fashion-clip'); \
    CLIPProcessor.from_pretrained('patrickjohncyh/fashion-clip')"

#--------------------- STAGE 2: Final Image ---------------------
FROM python:3.12-slim

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y \
libgl1-mesa-glx \
libglib2.0-0 \
&& rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:${PATH}"

COPY --from=builder /root/.local /root/.local
# Copy the PyTorch hub cache with models
COPY --from=builder /root/.cache /root/.cache
COPY . .

ENV PYTHONUNBUFFERED=1

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
