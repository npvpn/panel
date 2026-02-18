ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS build
ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential gcc python3-dev libpq-dev curl unzip ca-certificates \
    && update-ca-certificates \
    # Передаем версию как параметр скрипту
    && curl -fsSL https://github.com/Gozargah/Marzban-scripts/raw/master/install_latest_xray.sh | bash -s v25.9.11 \
    && rm -rf /var/lib/apt/lists/*
    
COPY ./requirements.txt /code/requirements.txt
RUN python3 -m pip install --upgrade pip \
    && pip install --no-cache-dir --upgrade -r /code/requirements.txt

FROM python:${PYTHON_VERSION}-slim
ENV PYTHONUNBUFFERED=1
ARG PYTHON_VERSION
ENV PYTHON_LIB_PATH=/usr/local/lib/python${PYTHON_VERSION}/site-packages
WORKDIR /code

RUN rm -rf $PYTHON_LIB_PATH/*

COPY --from=build $PYTHON_LIB_PATH $PYTHON_LIB_PATH
# COPY --from=build /usr/local/share/xray /usr/local/share/xray
RUN mkdir -p /usr/local/share/xray
# COPY --from=build /usr/local/bin/xray /usr/local/bin/
# COPY --from=build /usr/local/share/xray/geo*.dat /usr/local/share/xray/
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /usr/local/share/xray /usr/local/share/xray
COPY . /code
RUN mkdir -p /code/app/dashboard/build/statics
COPY ./app/dashboard/build/statics/ /code/app/dashboard/build/statics/

RUN ln -sf /code/marzban-cli.py /usr/bin/marzban-cli || true \
    && chmod +x /usr/bin/marzban-cli || true \
    && marzban-cli completion install --shell bash || true

CMD ["bash", "-c", "alembic upgrade head && python /code/main.py"]