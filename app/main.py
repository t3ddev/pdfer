
import logging
import os
from flask import Flask, request
import schedule
import re
import json
import math
import proposal
import checklist


app = Flask(__name__, static_url_path='/static')
log = logging.getLogger('werkzeug')
log.disabled = True

app.add_url_rule('/proposal', view_func=proposal.make_proposal)
app.add_url_rule('/checklist', view_func=checklist.make_checklist)

@app.route("/check",methods=['GET'])
def health_check():
    return "CHECK WORKING"



def clean_static():
    count = 0
    for file in os.listdir('./static'):
        count += 1
        os.remove(file)

schedule.every().day.at("01:00").do(clean_static)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)