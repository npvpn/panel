from app.models.node import NodeStatus


def resolve_host_addresses(host) -> list[str]:
    """Адреса хоста для подписки.

    Приоритет у статического host.address (обратная совместимость). Если он
    пуст — собираем Node.address связанных нод, исключая disabled (удалённые
    ноды уже выпали из связи через FK CASCADE).
    """
    if host.address:
        return [i.strip() for i in host.address.split(",")]
    return [node.address for node in host.nodes if node.status != NodeStatus.disabled]
