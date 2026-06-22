import re

# RFC 7230 token: допустимые символы имени заголовка.
_TOKEN_RE = re.compile(r"^[A-Za-z0-9!#$%&'*+\-.^_`|~]+$")


def parse_custom_headers(raw: str) -> dict[str, str]:
    """Парсит настройку sub_custom_headers (построчно 'Name: Value') в словарь.

    - пустые строки и строки, начинающиеся с '#', пропускаются;
    - сплит по первому ':'; имя и значение strip();
    - строки без ':' пропускаются;
    - имя обязано быть RFC-7230 token, иначе строка пропускается;
    - имя приводится к нижнему регистру (HTTP-имена регистронезависимы;
      встроенные хедеры уже в нижнем регистре — это обеспечивает override
      без дублей при любом регистре входного имени);
    - значение с символами вне печатного Latin-1 диапазона отбрасывается:
      ord < 32 (управляющие), ord == 127 (DEL) или ord > 255 (выше U+00FF);
      защищает от UnicodeEncodeError в Starlette (latin-1 кодировка хедеров);
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
        if any(ord(ch) < 32 or ord(ch) == 127 or ord(ch) > 255 for ch in value):
            continue
        headers[name.lower()] = value
    return headers
