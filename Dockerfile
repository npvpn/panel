# ARG PYTHON_VERSION=3.12

# FROM python:${PYTHON_VERSION}-slim AS build
# ENV PYTHONUNBUFFERED=1

# WORKDIR /code

# # RUN apt-get update \
# #     && apt-get install -y --no-install-recommends \
# #        build-essential gcc python3-dev libpq-dev curl unzip ca-certificates \
# #     && update-ca-certificates \
# #     && curl -fsSL https://github.com/Gozargah/Marzban-scripts/raw/master/install_latest_xray.sh | bash \
# #     && rm -rf /var/lib/apt/lists/*

# RUN apt-get update \
#     && apt-get install -y --no-install-recommends \
#        build-essential gcc python3-dev libpq-dev curl unzip ca-certificates \
#     && update-ca-certificates \
#     # Передайте версию как параметр скрипту
#     && curl -fsSL https://github.com/Gozargah/Marzban-scripts/raw/master/install_latest_xray.sh | bash -s v25.9.11 \
#     && rm -rf /var/lib/apt/lists/*
    
# COPY ./requirements.txt /code/requirements.txt
# RUN python3 -m pip install --upgrade pip setuptools \
#     && pip install --no-cache-dir --upgrade -r /code/requirements.txt

# FROM python:${PYTHON_VERSION}-slim
# ENV PYTHONUNBUFFERED=1
# ARG PYTHON_VERSION
# ENV PYTHON_LIB_PATH=/usr/local/lib/python${PYTHON_VERSION}/site-packages
# WORKDIR /code

# RUN rm -rf $PYTHON_LIB_PATH/*

# COPY --from=build $PYTHON_LIB_PATH $PYTHON_LIB_PATH
# # COPY --from=build /usr/local/share/xray /usr/local/share/xray
# RUN mkdir -p /usr/local/share/xray
# COPY --from=build /usr/local/bin/xray /usr/local/bin/
# COPY --from=build /usr/local/share/xray/geo*.dat /usr/local/share/xray/

# COPY . /code

# RUN ln -sf /code/marzban-cli.py /usr/bin/marzban-cli || true \
#     && chmod +x /usr/bin/marzban-cli || true \
#     && marzban-cli completion install --shell bash || true

# CMD ["bash", "-c", "alembic upgrade head && python /code/main.py"]
FROM python:3.10-slim AS build
ARG PYTHON_VERSION=3.12

FROM python:$PYTHON_VERSION-slim AS build

ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl unzip gcc python3-dev \
    && apt-get install -y --no-install-recommends build-essential curl unzip gcc python3-dev libpq-dev \
    && curl -L https://github.com/Gozargah/Marzban-scripts/raw/master/install_latest_xray.sh | bash \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/
RUN python3 -m pip install --upgrade pip setuptools \
    && pip install --no-cache-dir --upgrade -r /code/requirements.txt

FROM python:3.10-slim
FROM python:$PYTHON_VERSION-slim

ENV PYTHON_LIB_PATH=/usr/local/lib/python${PYTHON_VERSION%.*}/site-packages
WORKDIR /code

RUN rm -rf /usr/local/lib/python3.10/site-packages/*
RUN rm -rf $PYTHON_LIB_PATH/*

COPY --from=build /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=build $PYTHON_LIB_PATH $PYTHON_LIB_PATH
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /usr/local/share/xray /usr/local/share/xray

COPY . /code

RUN ln -s /code/marzban-cli.py /usr/bin/marzban-cli \
    && chmod +x /usr/bin/marzban-cli \
    && marzban-cli completion install --shell bash

CMD ["bash", "-c", "alembic upgrade head; python main.py"]