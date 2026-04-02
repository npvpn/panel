ARG PYTHON_VERSION=3.12

# Stage 1: Frontend build
FROM node:16.17.0-slim AS frontend
WORKDIR /dashboard
COPY ./app/dashboard/package.json ./app/dashboard/package-lock.json ./
RUN npm ci
COPY ./app/dashboard/ ./
RUN VITE_BASE_API=/api/ npm run build -- --outDir build --assetsDir statics \
    && cp ./build/index.html ./build/404.html

# Stage 2: Python dependencies + xray
FROM python:${PYTHON_VERSION}-slim AS build
ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential gcc python3-dev libpq-dev curl unzip ca-certificates \
    && update-ca-certificates \
    && curl -fsSL https://github.com/Gozargah/Marzban-scripts/raw/master/install_latest_xray.sh | bash -s v25.9.11 \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/requirements.txt
RUN python3 -m pip install --upgrade pip \
    && pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Stage 3: Final image
FROM python:${PYTHON_VERSION}-slim
ENV PYTHONUNBUFFERED=1
ARG PYTHON_VERSION
ENV PYTHON_LIB_PATH=/usr/local/lib/python${PYTHON_VERSION}/site-packages
WORKDIR /code

RUN rm -rf $PYTHON_LIB_PATH/*

COPY --from=build $PYTHON_LIB_PATH $PYTHON_LIB_PATH
RUN mkdir -p /usr/local/share/xray
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /usr/local/share/xray /usr/local/share/xray
COPY . /code
COPY --from=frontend /dashboard/build/ /code/app/dashboard/build/
COPY ./app/dashboard/public/statics/ /code/app/dashboard/build/statics/

RUN ln -sf /code/marzban-cli.py /usr/bin/marzban-cli || true \
    && chmod +x /usr/bin/marzban-cli || true \
    && marzban-cli completion install --shell bash || true

CMD ["bash", "-c", "alembic upgrade head && python /code/main.py"]