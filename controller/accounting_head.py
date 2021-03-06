from __future__ import print_function
from flask import Flask, request, make_response, jsonify, session, Blueprint
import sys
import os
import json
import re
import dialogflow_v2
from dialogflow_v2 import types

from google.cloud import language_v1, language
from google.cloud.language_v1 import enums, types


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


def getTags(JSONObject):
    if(JSONObject):
        content = JSONObject
        # Call NLP API
        client1 = language_v1.LanguageServiceClient()
        document = language.types.Document(
            content=content['inputText'],
            type=language.enums.Document.Type.PLAIN_TEXT
        )
        features = language.types.AnnotateTextRequest.Features(
            extract_syntax=True,
            extract_entities=True,
            extract_document_sentiment=False,
            extract_entity_sentiment=False,
            classify_text=False)

        response = client1.annotate_text(document, features)
        listEntityname = []

        # from all entities
        for entity in response.entities:
            if(enums.Entity.Type(entity.type).name != "PRICE" or enums.Entity.Type(entity.type).name != "DATE"):
                # call to Dialogflow
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"../tags.json"
                client = dialogflow_v2.SessionsClient()
                session = client.session_path(
                    'slotfilling1-hyalrc', '1234abcdd')
                text_input = dialogflow_v2.types.TextInput(
                    text=entity.name, language_code="en")
                query_input = dialogflow_v2.types.QueryInput(text=text_input)
                response = client.detect_intent(
                    session=session, query_input=query_input)

                print('Query text: {}'.format(response.query_result.query_text))
                print('Detected intent: {} (confidence: {})\n'.format(
                    response.query_result.intent.display_name,
                    response.query_result.intent_detection_confidence))
                intentName = response.query_result.intent.display_name
                if(intentName != 'Default Fallback Intent'):
                    listEntityname.append(intentName)

        if(not listEntityname):
            listEntityname.append('Miscellaneous')
        # remove duplicates
        print(listEntityname)
        listEntityname = list(set(listEntityname))
        return {'outflow_tags': listEntityname}
    else:
        return {}


@account_head.route('/accounthead/', methods=['GET', 'POST'])
def add_message():
    acHead = sendResponse(request.json)
    tags = getTags(request.json)
    acHead.update(tags)
    newList = list(acHead["outflow_tags"])
    newList.append(acHead["accountHead"])
    acHead["outflow_tags"] = newList
    return jsonify(acHead)
