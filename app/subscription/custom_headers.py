import re

# RFC 7230 token: допустимые символы имени заголовка.
_TOKEN_RE = re.compile(r"^[A-Za-z0-9!#$%&'*+\-.^_`|~]+$")


def parse_custom_headers(raw: str) -> dict[str, str]:
    """Парсит настройку sub_custom_headers (построчно 'Name: Value') в словарь.

    - пустые строки и строки, начинающиеся с '#', пропускаются;
    - сплит по первому ':'; имя и значение strip();
    - строки без ':' пропускаются;
    - имя обязано быть RFC-7230 token, иначе строка пропускается;
    - значение с управляющими символами (ord < 32) отбрасывается
      (защита от порчи ответа);
    - при дубликате имени побеждает последняя строка.
    """
    headers: dict[str, str] = {}
    if not raw:
        return headers
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        name = name.strip()
        value = value.strip()
        if not name or not _TOKEN_RE.match(name):
            continue
        if any(ord(ch) < 32 for ch in value):
            continue
        headers[name] = value
    return headers
