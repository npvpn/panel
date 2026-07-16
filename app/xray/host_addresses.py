from app.models.node import NodeStatus


def _visible_nodes(host) -> list:
    """Ноды хоста, которые он реально «представляет» клиенту.

    Инвариант: адреса (resolve_host_addresses) и node_ids (resolve_host_node_ids)
    строятся по ОДНОМУ И ТОМУ ЖЕ множеству нод — иначе БС-признак/БС-блокировка
    хоста могут относиться к ноде, чей адрес в подписку уже не попадает.

    - статический host.address (в т.ч. домен-маскировка) → хост отдаёт этот адрес
      всегда, за ним стоят ВСЕ привязанные ноды, включая disabled: disabled в панели
      не значит, что сервер физически выключен, и БС-лимит по такой ноде обходить
      нельзя;
    - пустой host.address → адреса собираются от нод, disabled из них исключены
      (удалённые ноды уже выпали из связи через FK CASCADE), поэтому и node_ids
      считаем только по живым.
    """
    if host.address:
        return list(host.nodes)
    return [node for node in host.nodes if node.status != NodeStatus.disabled]


def resolve_host_addresses(host) -> list[str]:
    """Адреса хоста для подписки.

    Приоритет у статического host.address (обратная совместимость). Если он
    пуст — собираем Node.address связанных нод (см. _visible_nodes).
    """
    if host.address:
        return [i.strip() for i in host.address.split(",")]
    return [node.address for node in _visible_nodes(host)]


def resolve_host_node_ids(host) -> list[int]:
    """Ноды хоста, по которым определяется его БС-признак и БС-блокировки (NPVPN-1652).

    Согласовано с resolve_host_addresses: см. инвариант в _visible_nodes.
    """
    return [node.id for node in _visible_nodes(host)]
