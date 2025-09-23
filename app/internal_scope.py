# internal_scope.py
from jinja2 import Template
import pdfkit
import datetime
import os
from flask import request
import re
import json
import math

ROOT_URL = os.environ.get("ROOT_URL", "http://localhost")

def _walk_items(categories):
    """Итерируемся по всем айтемам во всех категориях/подкатегориях."""
    for cat in categories:
        for subcat in cat.get('subcategories', []):
            for item in subcat.get('items', []):
                yield item

def make_internal_scope():
    body = request.json

    # Подтянем шаблон
    with open('./templates/InternalScope.html', encoding='utf-8') as f:
        jinja_t = Template(f.read())

    # Форматируем totals у категорий
    for cat in body.get('categories', []):
        cat['totalFormatted'] = f"{cat.get('total', 0) :,}"

    # Обработка EXP[...] в longDescription (оставляем, как в proposal)
    for item in _walk_items(body.get('categories', [])):
        # ВАЖНО: убираем логику скрытия цены (priceHidden) — цену показываем всегда
        # if item.get('priceHidden', False):
        #     item['price'] = "N/A"
        #     item['total'] = "N/A"

        long_desc = item.get('longDescription', '') or ''
        if "EXP[" in long_desc and "]EXP" in long_desc:
            expressions = re.findall(r'EXP\[(.*?)\]EXP', long_desc)
            long_desc = long_desc.replace("EXP[", "").replace("]EXP", "")
            for expression in expressions:
                try:
                    result = eval(expression)
                except Exception:
                    result = expression
                long_desc = long_desc.replace(expression, str(result))
            item['longDescription'] = long_desc

    # Собираем Custom items (для сводной таблицы сверху)
    custom_items = []
    for item in _walk_items(body.get('categories', [])):
        if not item.get('omitFromPDF') and item.get('catelogId') == 'Custom':
            custom_items.append(item)

    # Рендер
    rendered = jinja_t.render(data=body, custom_items=custom_items)

    ts = datetime.datetime.now().timestamp()
    if not os.path.exists('./static'):
        os.makedirs('./static')
    out_path = f"./static/internal_scope_{ts}.pdf"
    pdfkit.from_string(rendered, out_path)

    response = {
        'statusCode': 200,
        'body': {
            "internal_scope": f"{ROOT_URL}/static/internal_scope_{ts}.pdf",
            "data": json.dumps(body)
        }
    }
    return response

make_internal_scope.methods = ['POST']
