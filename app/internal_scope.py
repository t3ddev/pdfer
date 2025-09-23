# internal_scope.py
from jinja2 import Template
import pdfkit, datetime, os, re, json
from flask import request

ROOT_URL = os.environ.get("ROOT_URL", "http://localhost")

BASE_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

def _walk_items(categories):
    for cat in categories or []:
        for subcat in cat.get("subcategories", []) or []:
            for item in subcat.get("items", []) or []:
                yield item

def make_internal_scope():
    body = request.json or {}

    # Шаблон (маленькая i)
    template_path = os.path.join(TEMPLATES_DIR, "internalScope.html")
    with open(template_path, encoding="utf-8") as f:
        jinja_t = Template(f.read())

    # Форматируем суммы по категориям
    for cat in body.get("categories", []):
        cat["totalFormatted"] = f"{cat.get('total', 0):,}"

    # Обрабатываем EXP[...] в longDescription
    for item in _walk_items(body.get("categories", [])):
        long_desc = (item.get("longDescription") or "")
        if "EXP[" in long_desc and "]EXP" in long_desc:
            expressions = re.findall(r"EXP\[(.*?)\]EXP", long_desc)
            long_desc = long_desc.replace("EXP[", "").replace("]EXP", "")
            for expr in expressions:
                try:
                    result = eval(expr)  # как в proposal
                except Exception:
                    result = expr
                long_desc = long_desc.replace(expr, str(result))
            item["longDescription"] = long_desc

    # Все кастом-айтемы (если нужно учитывать omitFromPDF — верни условие назад)
    custom_items = [i for i in _walk_items(body.get("categories", []))
                    if i.get("catelogId") == "Custom"]

    rendered = jinja_t.render(data=body, custom_items=custom_items)

    # Генерация PDF
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

make_internal_scope.methods = ["POST"]
