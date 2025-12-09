ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS build
ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc python3-dev libpq-dev curl unzip \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости Marzban из вашего requirements.txt форка
COPY ./requirements.txt /code/requirements.txt
RUN python3 -m pip install --upgrade pip setuptools \
    && pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Кладём детерминированный Xray и базы (из репозитория форка)
COPY xray/xray /usr/local/bin/xray
COPY xray/geoip.dat /usr/local/share/xray/geoip.dat
COPY xray/geosite.dat /usr/local/share/xray/geosite.dat
RUN chmod +x /usr/local/bin/xray

FROM python:${PYTHON_VERSION}-slim
ENV PYTHONUNBUFFERED=1
ARG PYTHON_VERSION
ENV PYTHON_LIB_PATH=/usr/local/lib/python${PYTHON_VERSION%.*}/site-packages

WORKDIR /code

# Чистим системные site-packages и копируем установленные в build-слое
RUN rm -rf $PYTHON_LIB_PATH/*
COPY --from=build $PYTHON_LIB_PATH $PYTHON_LIB_PATH

# Копируем бинарь xray и базы из build-слоя
COPY --from=build /usr/local/bin/xray /usr/local/bin/xray
COPY --from=build /usr/local/share/xray /usr/local/share/xray

# Копируем код форка целиком
COPY . /code

# Опционально: symlink на marzban-cli (если он есть в корне форка)
RUN ln -sf /code/marzban-cli.py /usr/bin/marzban-cli || true \
    && chmod +x /usr/bin/marzban-cli || true \
    && marzban-cli completion install --shell bash || true

# ВАЖНО: точка входа как у вас в docker-compose
CMD ["bash", "-c", "alembic upgrade head && python /code/marzban.py"]