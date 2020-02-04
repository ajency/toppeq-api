from __future__ import print_function
from flask import Flask, request, make_response, jsonify, session
import sys
sys.path.append('../controller')
from controller.accounting_head import account_head
from controller.date import date
import os

app = Flask(__name__)
app.secret_key = b'o\xd0\xaa\xf8\x96\x90EnRy\xeavV\xb7/T\xc1\xf1\x14\xa21 \xb2\x18'

app.register_blueprint(account_head, url_prefix='/api/')


@app.route('/')
def hello():
    return "API Endpoint for Toppeq"


if __name__ == '__main__':
    app.run(port=3001)
