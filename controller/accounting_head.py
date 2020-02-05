from __future__ import print_function
from flask import Flask, request, make_response, jsonify, session, Blueprint
import sys
import os
import json
import dialogflow_v2
from dialogflow_v2 import types
from google.oauth2.service_account import Credentials

[sys.path.append(i) for i in ['.', '..']]

account_head = Blueprint('account_head', __name__)


def sendResponse(JSONObject):
    if(JSONObject):

        credentials = Credentials.from_service_account_file("../intent.json")
        client = dialogflow_v2.SessionsClient(credentials=credentials)

        session = client.session_path(
            'classify-intents-ujpxuu', 'Testing values')
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
        result = {'inputText': response.query_result.query_text, 'accountHead': intentName,
                  'confidence': confidence, 'outflow_tags': ["stationery", "office", "supplies"]}
        return result
    else:
        return "Request Failed."


@account_head.route('/accounthead/', methods=['GET', 'POST'])
def add_message():
    return jsonify(sendResponse(request.json))
