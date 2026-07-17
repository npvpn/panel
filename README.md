# npvpn panel

**npvpn panel** — форк Marzban, разработанный для реальных коммерческих VPN-проектов.  
Панель оптимизирована под масштабируемые конфигурации, высокую производительность и удобное управление распределённой инфраструктурой.  
Проект развивается как основа для запуска VPN-сервисов и автоматизированных Telegram-ботов и VPN-сервисов.

---

## Назначение

- Масштабируемая архитектура для больших VPN-проектов  
- Оптимизация производительности и стабильности  
- Поддержка реальных боевых конфигураций (VLESS, XRay, multi-node)  
- Упрощённая работа с узлами и серверами  
- Интеграция с Telegram-ботами npvpn  
- Подходит для бизнеса, партнёрских сервисов и white-label решений

---

## Установка

### Партнёрский сервер (рекомендуется)

Полная автоматическая установка: UFW, certbot, MySQL, SSL, порт 8001, админ панели.

**Перед запуском:** создайте администратора в админке бота и скопируйте логин, MySQL-пароль и хэш пароля.  
Подробнее: [Установка панели для партнера.md](https://github.com/npvpn/Marzban-scripts/blob/master/Установка%20панели%20для%20партнера.md)

```bash
sudo bash -c "$(curl -sL https://github.com/npvpn/Marzban-scripts/raw/master/marzban.sh)" @ install-partner
```

С параметрами (без интерактивных вопросов):

```bash
sudo bash -c "$(curl -sL https://github.com/npvpn/Marzban-scripts/raw/master/marzban.sh)" @ install-partner \
  --domain your-domain.tld \
  --cert-email admin@example.com \
  --mysql-password 'YOUR_MYSQL_PASSWORD' \
  --admin-username partner_admin \
  --admin-password-hash '$argon2id$...' \
  --subscription-title 'My VPN' \
  --support-telegram support_bot \
  --bot-telegram my_vpn_bot \
  --token 'GITHUB_RUNNER_REGISTRATION_TOKEN' \
  --non-interactive
```

`--token` — registration token runner’а в репе `npvpn/telegram_bot` (метка будет `partner-<bot-telegram>`). Опционально: `--project-dir /opt/marzban`, `--skip-runner`.

Панель будет доступна по адресу: `https://<домен>:8001/dashboard/`

**Обновление панели на партнёрах:** образ собирается в этом репозитории (`build.yml` → Docker Hub). Выкат — Actions приватного [`npvpn/telegram_bot`](https://github.com/npvpn/telegram_bot) (workflow **Deploy partner panels**). Инструкция: [docs/deploy.md](https://github.com/npvpn/telegram_bot/blob/master/docs/deploy.md#partner-panels).

---

### Обычная установка (без автоматизации SSL/certbot)

1. Используйте команду для установки панели с нужной базой данных:

- **Install Marzban with SQLite**:

  ```bash
  sudo bash -c "$(curl -sL https://github.com/npvpn/Marzban-scripts/raw/master/marzban.sh)" @ install
  ```

- **Install Marzban with MySQL**:

  ```bash
  sudo bash -c "$(curl -sL https://github.com/npvpn/Marzban-scripts/raw/master/marzban.sh)" @ install --database mysql
  ```

- **Install Marzban with MariaDB**:

  ```bash
  sudo bash -c "$(curl -sL https://github.com/npvpn/Marzban-scripts/raw/master/marzban.sh)" @ install --database mariadb
  ```

2. Следуйте инструкции по установке и задайте значения для аккаунта поддержки, названия подписки в клиенте, аккаунта бота (или оставьте пустыми).
Дождитесь окончания загрузки и ваша панель запущена.

3. Если вы используете не SQLite, то предварительно потребуются сертификаты для сервера, на котором запущена панель.

4. Введите 

```bash
marzban edit
```

чтобы открыть docker-compose.yaml.

5. Пропишите путь к вашим сертификатам на сервере и путь, где они будут внутри контейнера marzban:

```                                                                       
services:
marzban:
    image: npvpn/panel:latest
    restart: always
    env_file: .env
    network_mode: host
    volumes:
    - /var/lib/marzban:/var/lib/marzban
    - /var/lib/marzban/logs:/var/lib/marzban-node
    - <путь к сертифиату на сервере>:<путь к сертификату внутри контейнера>
    - <путь к ключу на сервере>:<путь к ключу внутри контейнера>
    depends_on:
    mysql:
        condition: service_healthy
```

Сохраняем и выходим.

6. Вводим 

```bash
marzban edit-env
```

чтобы открыть файл с переменными окружения.

7. Раскомментируйте строки 

```bash
# UVICORN_SSL_CERTFILE = "/var/lib/marzban/certs/example.com/fullchain.pem"
# UVICORN_SSL_KEYFILE = "/var/lib/marzban/certs/example.com/key.pem"
```

и замените на пути к сертифкату и ключу внутри контейнера, которые вы прописали ранее:

```bash
UVICORN_SSL_CERTFILE = "<путь к сертификату внутри контейнера>"
UVICORN_SSL_KEYFILE = "<путь к ключу внутри контейнера>"
```

Сохраняем и выходим.

8. Перезапустите marzban:
```bash
marzban restart
```

9. Создайте администратора панели с помощью команды:
```bash
marzban cli admin create
```

10. Войдите в панель по адресу **<ваш домен>:8000/dashboard/#/login** и введите данные для администратора.

---

## Обновление с оригинальной панели

Если панель была установлена из оригинального репозитория Marzban, вы можете переключить ее на `npvpn panel` без переустановки:

1. Подключитесь к серверу, где установлена панель.

2. Откройте `docker-compose`:

```bash
marzban edit
```

3. В сервисе `marzban` укажите образ `npvpn/panel:latest` и проверьте блок `volumes`:

```
services:
marzban:
    image: npvpn/panel:latest
    restart: always
    env_file: .env
    network_mode: host
    volumes:
    - /var/lib/marzban:/var/lib/marzban
    - /var/lib/marzban/logs:/var/lib/marzban-node
    - <путь к сертифиату на сервере>:<путь к сертификату внутри контейнера>
    - <путь к ключу на сервере>:<путь к ключу внутри контейнера>
    depends_on:
    mysql:
        condition: service_healthy
```

4. Загрузите новый образ:

```bash
docker pull npvpn/panel:latest
```

5. Перезапустите панель:

```bash
marzban restart
```

---

## Лицензия

Проект распространяется под лицензией **AGPL-3.0**, как и оригинальный Marzban.  
Это означает, что любые модификации панели, доступные пользователям через сеть, должны быть опубликованы в открытом виде.

Отдельные интеграции (боты, биллинг, API-шлюзы), не включающие код панели, могут использовать другие лицензии.

---

## Контакты

Telegram: https://t.me/npvpn  
