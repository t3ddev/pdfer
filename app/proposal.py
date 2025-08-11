from jinja2 import Template
import pdfkit
import datetime
import os
from flask import Flask, request
import re
import json
import math
ROOT_URL = os.environ.get("ROOT_URL", "http://localhost")

def make_proposal():
    body = request.json
    with open('./templates/proposal.html') as f:
        jinja_t = Template(f.read())

    
    sqFt = body['estimatesInfo'][0]['squareFootage'] #used below in exp evaluation
    for cat in body['categories']:
        cat['totalFormatted'] = f"{cat['total'] :,}"

        for subcat in cat['subcategories']:
            for item in subcat['items']:
                if "EXP[" in item['longDescription'] and "]EXP" in item['longDescription']:
                    expressions = re.findall(r'EXP\[(.*?)\]EXP', item['longDescription'])
                    item['longDescription'] = item['longDescription'].replace("EXP[", "").replace("]EXP","")
                    for expression in expressions:
                        result = eval(expression)
                        item['longDescription'] = item['longDescription'].replace(expression, str(result))

    rendered = jinja_t.render(data=body)
    ts = datetime.datetime.now().timestamp()
    if (not os.path.exists('./static')):
        os.makedirs('./static')
    pdfkit.from_string(rendered, f"./static/proposal_{ts}.pdf")

    response = {
            'statusCode': 200,
            'body': {
                "proposal" : f"{ROOT_URL}/static/proposal_{ts}.pdf",
                "data" : json.dumps(body)
                }
        }
    return response

make_proposal.methods = ['POST']