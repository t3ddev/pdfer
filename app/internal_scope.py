# internal_scope.py
import datetime
import json
import os
import re
import unicodedata
from decimal import Decimal

import pdfkit
from flask import request
from jinja2 import Environment, FileSystemLoader

ROOT_URL = os.environ.get("ROOT_URL", "http://localhost")

BASE_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")


def _walk_items(categories):
    """Итерация по всем items во всех подкатегориях."""
    for cat in categories or []:
        for subcat in cat.get("subcategories", []) or []:
            for item in subcat.get("items", []) or []:
                yield item


# ---------- Денежный фильтр ----------

def _only_number_like(s: str):
    """
    Если строка выглядит как одно число (допускаются $, пробелы, запятые, точка),
    вернёт Decimal; иначе None.
    """
    if s is None:
        return None
    s = unicodedata.normalize("NFKC", str(s)).strip()
    s_no_sym = s.replace("$", "").replace(" ", "")
    if re.fullmatch(r"[0-9][0-9,]*([.][0-9]+)?", s_no_sym):
        try:
            return Decimal(s_no_sym.replace(",", ""))
        except Exception:
            return None
    return None


def money(val):
    """
    Jinja-фильтр форматирования денег.
    - Если val число (или строка-число) → "$12,345.00".
    - Если val содержит текст/несколько $ → вернуть как есть.
    """
    if isinstance(val, (int, float, Decimal)):
        try:
            return f"${Decimal(str(val)):,.2f}"
        except Exception:
            return f"${val}"
    as_num = _only_number_like(val)
    if as_num is not None:
        return f"${as_num:,.2f}"
    return "" if val is None else str(val)


# ---------- Основной обработчик ----------

def make_internal_scope():
    body = request.json or {}

    # 1) Готовим Jinja окружение ЗАРАНЕЕ, вешаем фильтр, затем берём шаблон
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=False,  # у тебя HTML генерится вручную, как раньше
    )
    env.filters["money"] = money
    template = env.get_template("internalScope.html")

    # 2) Формат суммы по категориям (без $ — знак добавит фильтр)
    for cat in body.get("categories", []):
        cat["totalFormatted"] = f"{cat.get('total', 0):,}"

    # 3) Обработка EXP[...] внутри longDescription
    for item in _walk_items(body.get("categories", [])):
        long_desc = (item.get("longDescription") or "")
        if "EXP[" in long_desc and "]EXP" in long_desc:
            expressions = re.findall(r"EXP\[(.*?)\]EXP", long_desc)
            tmp = long_desc.replace("EXP[", "").replace("]EXP", "")
            for expr in expressions:
                try:
                    result = eval(expr)  # как и раньше, источник контролируем
                except Exception:
                    result = expr
                tmp = tmp.replace(expr, str(result))
            item["longDescription"] = tmp

    # 4) Соберём все кастомные айтемы
    custom_items = [i for i in _walk_items(body.get("categories", []))
                    if i.get("catelogId") == "Custom"]

    # 5) Рендер
    rendered = template.render(data=body, custom_items=custom_items)

    # 6) Генерация PDF
    os.makedirs(STATIC_DIR, exist_ok=True)
    ts = datetime.datetime.now().timestamp()
    out_path = os.path.join(STATIC_DIR, f"internal_scope_{ts}.pdf")
    pdfkit.from_string(rendered, out_path)

    return {
        "statusCode": 200,
        "body": {
            "internal_scope": f"{ROOT_URL}/static/internal_scope_{ts}.pdf",
            "data": json.dumps(body)
        }
    }


# для Flask роутинга через фабрику/регистратор
make_internal_scope.methods = ["POST"]
