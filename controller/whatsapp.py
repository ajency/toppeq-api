from __future__ import print_function
from flask import Flask, request, redirect, Blueprint
from twilio.twiml.messaging_response import MessagingResponse
import time
import os
import dialogflow_v2
from dialogflow_v2 import types
from twilio.rest import Client

from google.cloud import language_v1, language
from google.cloud.language_v1 import enums, types
from google.oauth2.service_account import Credentials


whatsapp_call = Blueprint('whatsapp', __name__)


@whatsapp_call.route("/sms", methods=['GET', 'POST'])
def incoming_sms():
    # Get the message the user sent our Twilio number
    print(vars(request.values))
    body = request.values.get('Body', None)

    if(body.lower() == "new" | | body.lower() == "reset" | | body.lower() == "help"):
        account_sid = 'AC797feaab84bdd385bbb2ae0f1c08e8b6'
        auth_token = '4835d9b49f5dbdd284d5ab2d251918'
        client = Client(account_sid, auth_token)

        message = client.messages \
            .create(
                from_=request.values.get('To', None),
                body="To record an expense, simply try typing in like this \n \n \"Bought office stationery for $20K.\" ",
                to=request.values.get('From', None)
            )

        print(message.sid)
        message = client.messages \
            .create(
                from_=request.values.get('To', None),
                body="In case you want to notify additional users,  you can do so by adding something like @john @email_id \n Ex. \"Bought office stationery for $20K. @john @mike\" ",
                to=request.values.get('From', None)
            )
        message = client.messages \
            .create(
                from_=request.values.get('To', None),
                body="Tip: :bulb: Type \"new\" or \"reset\", anytime if you want to start adding a fresh expense. To learn more about adding an expense, simply type \"help\"  ",
                to=request.values.get('From', None)
            )
        return ''

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
    print(str(resp))

    return str(resp)


@whatsapp_call.route("/status", methods=['GET', 'POST'])
def incoming_status():
    # Prints the current call status and returns nothing
    print(str(request))
    return ''
