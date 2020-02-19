from __future__ import print_function
from flask import Flask, request, redirect, Blueprint
from twilio.twiml.messaging_response import MessagingResponse
import time
import os
import json
import dialogflow_v2
from dialogflow_v2 import types
from twilio.rest import Client

from google.cloud import language_v1, language
from google.cloud.language_v1 import enums, types
from google.oauth2.service_account import Credentials

account_sid = 'AC797feaab84bdd385bbb2ae0f1c08e8b6'

with open('../twiliokey.json', 'r') as jsonfile:
    data = jsonfile.read()

obj = json.loads(data)
auth_token = str(obj['key'])

whatsapp_call = Blueprint('whatsapp', __name__)


def new_text():
    client = Client(account_sid, auth_token)
    message = client.messages \
        .create(
            from_=request.values.get('To', None),
            body="Hi there 👋\nMy name's Expense buddy and I'm here to assist you with recording expenses. ",
            to=request.values.get('From', None)
        )
    time.sleep(1)


def help_text():
    client = Client(account_sid, auth_token)
    message = client.messages \
        .create(
            from_=request.values.get('To', None),
            body="To *record an expense*, simply try typing \n \n_\"Bought office stationery for $20K.\"_  \nI will automatically categorize and notify the respective users once you have added your expense.",
            to=request.values.get('From', None)
        )
    time.sleep(1)

    message = client.messages \
        .create(
            from_=request.values.get('To', None),
            body="Tip: 💡 Type _\"new\"_ if you want to start adding a fresh expense. \nType _\"help\"_  , if you need help in adding an expense. ",
            to=request.values.get('From', None)
        )


@whatsapp_call.route("/sms", methods=['GET', 'POST'])
def incoming_sms():
    # Get the message the user sent our Twilio number
    print(vars(request.values))
    body = request.values.get('Body', None)
    incoming_text = body
    if(body.lower() == "new" or body.lower() == "reset" or body.lower() == "help"):
        body = 'reset vars'

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"../expenseslot.json"
    client = dialogflow_v2.SessionsClient()
    session = client.session_path(
        'expenseslot-lbtasi', '1234abcdd')

    text_input = dialogflow_v2.types.TextInput(
        text=body, language_code="en")

    query_input = dialogflow_v2.types.QueryInput(text=text_input)
    response = client.detect_intent(
        session=session, query_input=query_input)

    print('Query text: {}'.format(response.query_result.fulfillment_text))

    # Start our TwiML response
    resp = MessagingResponse()

    # Determine the right reply for this message
    resp.message(response.query_result.fulfillment_text)
    outputIntent = response.query_result.intent.display_name
    print(str(resp))
    if(response.query_result.fulfillment_text == 'Cleared'):
        resp = ''
        if(outputIntent == 'Default Welcome Intent'):
            new_text()
        help_text()
    return str(resp)


@whatsapp_call.route("/status", methods=['GET', 'POST'])
def incoming_status():
    # Prints the current call status and returns nothing
    print(str(request))
    return ''
