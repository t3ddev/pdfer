from jinja2 import Template
import pdfkit
import datetime
import os
from flask import Flask, request
import re
import json
ROOT_URL = os.environ.get("ROOT_URL", "http://localhost")

def make_checklist():
    body = request.json
    with open('./templates/checklist.html') as f:
        jinja_t = Template(f.read())

    for section in body['todo_list_sections']:
        for task in section['tasks']:
            for photo in task['photos']:
                for url in photo['uris']:
                    if url['type'] == 'original':
                        photo['original_url'] = url['url']
                    if url['type'] == 'thumbnail':
                        photo['thumbnail'] = url['url']
            for subtask in task['sub_tasks']:
                options = subtask.get('answer_options',[])
                if subtask['answer_type'] == 'open_text':
                    subtask['answer_array'] = [subtask['answer_text']]
                else:
                    subtask['answer_array'] = [options[o] for o in subtask['answer_choices'] ] 

          

    rendered = jinja_t.render(data=body)


    response = {
            'statusCode': 200,
            'body': rendered
        }
    return response

make_checklist.methods = ['POST']