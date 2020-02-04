# import flask dependencies
from __future__ import print_function
from flask import Flask, request, make_response, jsonify, Blueprint
from google.cloud import language_v1, language
from google.cloud.language_v1 import enums, types
from text2digits import text2digits
import time
import dateparser
import dateutil.relativedelta
from datetime import datetime, date, time, timedelta
import sys
import os
import json
import re

date_object = Blueprint('date', __name__)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"amount.json"

client = language_v1.LanguageServiceClient()

def results():
    # build a request object
    req = request.get_json(force=True)

    inputText = str(req.get('queryResult').get('queryText'))

    paymentDate = ''

    # Check if Dialogflow had picked up a date (18th, last wednesday)
    if(req.get('queryResult').get('parameters').get('date')):
        paymentDate = dateparser.parse(
            req.get('queryResult').get('parameters').get('date'))

    # Check if Dialogflow had picked up a date (this month, next june, last year)
    if(req.get('queryResult').get('parameters').get('date-period') != ''):
        paymentDate = dateparser.parse(
            req.get('queryResult').get('parameters').get('date-period').get('endDate'))

    # Output String
    value = 'Payment Date: ' + str(paymentDate.strftime(r"%b %d %Y "))

    # Return the string to Dialogflow
    return {'fulfillmentText':  value}


# create a route for webhook
@date_object.route('/date/', methods=['GET', 'POST'])
def webhook():
    toSend = results()
    return make_response(jsonify(toSend))

