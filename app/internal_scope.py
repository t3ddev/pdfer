# internal_scope.py
from jinja2 import Template
import pdfkit
import datetime
import os
import re
import json
from decimal import Decimal
import unicodedata
from flask import request

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
    Если строка выглядит как одно число (допускаются $, пробелы, запятые-разделители тысяч, точка),
    вернёт Decimal; иначе None.
    """
    if s is None:
        return None
    s = unicodedata.normalize("NFKC", str(s)).strip()
    # убираем $ и пробелы (внутренние пробелы тоже, чтобы "12 600" не упало)
    s_no_sym = s.replace("$", "").replace(" ", "")
    # допускаем 12,345.67
    if re.fullmatch(r"[0-9][0-9,]*([.][0-9]+)?", s_no_sym):
        try:
            return Decimal(s_no_sym.replace(",", ""))
        except Exception:
            return None
    return None


def money(val):
    """
    Jinja-фильтр форматирования денег.
    - Если val число (или строка-число), вернёт строку вида "$12,345.00".
    - Если val содержит текст/несколько знаков $, возвращает как есть (без добавления ещё одного $).
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

    # читаем шаблон
    template_path = os.path.join(TEMPLATES_DIR, "internalScope.html")
    with open(template_path, encoding="utf-8") as f:
        src = f.read()
    jinja_t = Template(src)
    # регистрируем фильтр
    jinja_t.environment.filters["money"] = money

    # формат для суммы по категориям (без $ — знак добавит фильтр)
    for cat in body.get("categories", []):
        cat["totalFormatted"] = f"{cat.get('total', 0):,}"

    # обработка EXP[...] внутри longDescription
    for item in _walk_items(body.get("categories", [])):
        long_desc = (item.get("longDescription") or "")
        if "EXP[" in long_desc and "]EXP" in long_desc:
            expressions = re.findall(r"EXP\[(.*?)\]EXP", long_desc)
            # уберём маркеры, вычислим выражения и подставим результат
            tmp = long_desc.replace("EXP[", "").replace("]EXP", "")
            for expr in expressions:
                try:
                    result = eval(expr)  # как в proposal: доверяем бэку, источник контролируем
                except Exception:
                    result = expr
                tmp = tmp.replace(expr, str(result))
            item["longDescription"] = tmp

    # соберём все кастомные айтемы (если нужно игнорировать omitFromPDF — верни условие)
    custom_items = [i for i in _walk_items(body.get("categories", []))
                    if i.get("catelogId") == "Custom"]

    # рендер
    rendered = jinja_t.render(data=body, custom_items=custom_items)

    # генерация PDF
    os.makedirs(STATIC_DIR, exist_ok=True)
    ts = datetime.datetime.now().timestamp()
    out_path = os.path.join(STATIC_DIR, f"internal_scope_{ts}.pdf")

    # можно задать опции wkhtmltopdf при необходимости
    # options = {"enable-local-file-access": None}
    # pdfkit.from_string(rendered, out_path, options=options)
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
