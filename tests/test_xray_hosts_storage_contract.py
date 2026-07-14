"""Контракт storage-словаря хоста, который строит app/xray/__init__.py::hosts().

BsContext._matches (app/subscription/bs_context.py) читает host.get("node_ids") or ().
Функцию hosts() нельзя выполнить в песочнице напрямую — она тянет GetDB/crud (БД,
рантайм xray), поэтому контракт проверяется по AST исходника: ключ "node_ids" должен
присутствовать в dict-литерале, который кладётся в storage[inbound_tag]. Если ключ
пропадёт/переименуется, БС-логика (заглушки лимита и routing_bs) молча отключится у
всех хостов, а обычные тесты BsContext/subscription (которые строят словари хостов
руками, не через hosts()) этого не заметят — этот тест ловит именно такой разрыв.
"""

from __future__ import annotations

import ast
import pathlib

_SOURCE_PATH = pathlib.Path(__file__).parent.parent / "app" / "xray" / "__init__.py"


def _host_dict_literal_keys() -> set[str]:
    tree = ast.parse(_SOURCE_PATH.read_text())
    hosts_func = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "hosts")
    dict_literals = [node for node in ast.walk(hosts_func) if isinstance(node, ast.Dict)]
    assert len(dict_literals) == 1, (
        "ожидался ровно один dict-литерал хоста внутри hosts() — структура функции изменилась, проверь тест вручную"
    )
    (host_dict,) = dict_literals
    return {key.value for key in host_dict.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)}


def test_hosts_storage_dict_has_node_ids_key():
    """app.xray.hosts() кладёт host.node_ids в storage под ключом "node_ids".

    Это единственный источник БС-признака хоста для BsContext (NPVPN-1652). Тест
    падает, если ключ убрать или переименовать в билдере — эмпирически проверено:
    удаление строки `"node_ids": host.node_ids,` из app/xray/__init__.py делает
    тест красным, возврат строки — снова зелёным.
    """
    assert "node_ids" in _host_dict_literal_keys()
