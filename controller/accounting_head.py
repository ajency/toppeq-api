from __future__ import print_function
from flask import Flask, request, make_response, jsonify, session, Blueprint
import sys
import os
import json
import dialogflow_v2
from dialogflow_v2 import types

account_head = Blueprint('account_head', __name__)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"../intent.json"

client = dialogflow_v2.SessionsClient()
session = client.session_path('classify-intents-ujpxuu', 'Testing values')

def sendResponse(JSONObject):
    if(JSONObject):
        content = JSONObject
        text_input = dialogflow_v2.types.TextInput(
            text=content['inputText'], language_code="en")
        query_input = dialogflow_v2.types.QueryInput(text=text_input)
        response = client.detect_intent(
            session=session, query_input=query_input)

        print('Query text: {}'.format(response.query_result.query_text))
        print('Detected intent: {} (confidence: {})\n'.format(
            response.query_result.intent.display_name,
            response.query_result.intent_detection_confidence))

        confidence = float("{0:.2f}".format(
            response.query_result.intent_detection_confidence * 100))

        if('Default Welcome Intent' in response.query_result.intent.display_name or 'Default Fallback Intent'in response.query_result.intent.display_name):
            intentName = 'Others'
        else:
            intentName = response.query_result.intent.display_name

        intentName = intentName.lower().replace(" ", "_")
        result = jsonify({'inputText': response.query_result.query_text, 'accountHead': intentName,
                          'confidence': confidence})
        return result
    else:
        return "Request Failed."



@account_head.route('/accounthead/', methods=['GET', 'POST'])
def add_message():
    return sendResponse (request.json)
        
