from __future__ import print_function
from flask import Flask, request, make_response, jsonify, session, Blueprint
import sys
import os
import json
import dialogflow_v2
from dialogflow_v2 import types

from google.cloud import language_v1, language
from google.cloud.language_v1 import enums, types
from text2digits import text2digits
import time
import dateparser
import dateutil.relativedelta
from datetime import datetime, date, time, timedelta
from pprint import pprint

from controller.accounting_head import sendResponse
import re

slot_fill = Blueprint('slot_fill', __name__)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"../intent.json"

client = dialogflow_v2.SessionsClient()
session = client.session_path('classify-intents-ujpxuu', '1234abcdpqrs')

client1 = language_v1.LanguageServiceClient()
defaultCurrency = 'INR'


class lastEntry():
    Amount = '0'
    entitySend = ''
    ExpenseType = ""
    recurrence = "No"
    frequency = ""
    paymentDate = ''
    DueDate = ""
    paymentStatus = 'Pending'
    Description = ''
    currency = defaultCurrency
    fullEntity = 0
    askFor = 'None'
    category = ''

    def isEmpty(self):
        if self.Amount == '0' and self.Description == '' and self.ExpenseType == '' and self.entitySend == '':
            return True
        else:
            return False

    def isFull(self):
        if self.Amount == '0' or self.Description == '' or self.ExpenseType == '' or self.entitySend == '':
            return False
        else:
            return True

    def clearIt(self):
        self.Amount = '0'
        self.entitySend = ''
        self.ExpenseType = ""
        self.recurrence = "No"
        self.frequency = ""
        self.paymentDate = ''
        self.DueDate = ""
        self.paymentStatus = 'Unpaid'
        self.Description = ''
        self.currency = defaultCurrency
        self.fullEntity = 0
        self.askFor = 'None'
        self.category = ''

    def emptyList(self):
        if self.Amount == '0':
            return 'Amount'
        if self.paymentDate == '':
            return 'Date'
        if self.entitySend == '':
            return 'Entity'
        if self.frequency == '' and self.recurrence == 'Yes':
            return 'Frequency'

        return 'None'


oldValue = lastEntry()


def removeStopwords(text):
    # removes stopwords from the text
    stopWords = ["and "]
    big_regex = re.compile(r'\b%s\b' %
                           r'\b|\b'.join(map(re.escape, stopWords)))
    return big_regex.sub("", text)


def convertWordstoNum(text):
    # converts words to numbers
    t2d = text2digits.Text2Digits()
    convertedText = t2d.convert(text)

    # convert lakh to numbers
    secondConvertedText = re.sub(
        r'(?P<money>[0-9]+)( |)l ', r'\g<money>00000 ', convertedText.lower())
    thirdConvertedText = re.sub(
        r'(?P<money>[0-9]+)( |)la(kh|c)(|s) ', r'\g<money>00000 ', secondConvertedText)
    return re.sub(r'(?P<money>[0-9]+)( |)cr ', r'\g<money>0000000 ', thirdConvertedText)


def removeConsecutiveSpaces(text):

    value = re.sub(
        r'(?P<number1>[0-9]+) (?P<number2>[0-9]+) ', r'\g<number1>+\g<number2> ', text+' ')

    List = re.findall(r'([0-9]+)\+([0-9]+)', value)
    for items in List:
        sumNumber = int(items[0]) + int(items[1])
        value = value.replace(str(items[0])+r'+'+str(items[1]), str(sumNumber))

    return value


def lowerCaps(text):
    if(not 'Rs.' in text.title()):
        text = re.sub(
            r'( )(rs(| |\.))', r' Rs. ', text+' ')
    return re.sub(
        r'(\d+(?P<ordinal>[A-z])+)', lambda m: m.group(0).lower(), text+' ')


def filterResults(text):
    op = removeConsecutiveSpaces(convertWordstoNum(removeStopwords(text)))
    return lowerCaps(op)


@slot_fill.route('/slotfill/', methods=['GET', 'POST'])
def send_response():
    req = request.get_json(force=True)

    inputText = str(req.get('queryResult').get('queryText'))

    oldValue.Description = inputText if oldValue.Description == '' else oldValue.Description

    oldValue.category = sendResponse(
        {'inputText': oldValue.Description})['accountHead'] if oldValue.category == '' else oldValue.category

    inputIntent = str(req.get('queryResult').get('intent').get('displayName'))

    filteredText = filterResults(inputText)

    # Step 2: call to Google NL API with the filtered text

    document = language.types.Document(
        content=filteredText.title(),
        type=language.enums.Document.Type.PLAIN_TEXT
    )
    features = language.types.AnnotateTextRequest.Features(
        extract_syntax=True,
        extract_entities=True,
        extract_document_sentiment=False,
        extract_entity_sentiment=False,
        classify_text=False)

    response = client1.annotate_text(document, features)

    # Price Check

    print('Checking for : '+oldValue.askFor)

    # Step 3.1: if price is detected by NLP, mark it with currency
    if(oldValue.Amount == '0'):
        flag = 0
    else:
        flag = 1

    if(oldValue.Amount == '0'):
        for entity in response.entities:
            if(enums.Entity.Type(entity.type).name == "PRICE" and flag == 0):
                oldValue.Amount = float(entity.metadata[u"value"])
                oldValue.currency = entity.metadata[u"currency"]
                flag = 1

        # Step 3.3 Check from Dialogflow
        if(flag == 0):
            if(req.get('queryResult').get('parameters').get('PRICE')):
                oldValue.Amount = float(
                    req.get('queryResult').get('parameters').get('PRICE'))
                flag = 1

        # Step 3.4 In case nothing is found, pick a number from the list
        if(flag == 0):
            maxValue = 0
            for entity in response.entities:
                if(enums.Entity.Type(entity.type).name == "NUMBER"):
                    maxValue = float(entity.metadata[u"value"]) if(
                        int(float(entity.metadata[u"value"])) > int(float(maxValue))) else maxValue

            if(int(maxValue) > 0):
                oldValue.Amount = maxValue
                flag = 1

  # Step 3.5 Detect Recurrence

    if(oldValue.ExpenseType == ''):
        if(req.get('queryResult').get('intent').get('displayName') == "checkRentExpense"):
            oldValue.recurrence = "Yes"
            oldValue.ExpenseType = "Rent/Subscription"

            textString = filteredText.lower()
            if("weekly" in textString or "per week" in textString):
                oldValue.frequency = "Weekly"
            elif("yearly" in textString or "per year" in textString or "annual" in textString):
                oldValue.frequency = "Yearly"
            elif("monthly" in textString or "per month" in textString or "every month" in textString):
                oldValue.frequency = "Monthly"
        else:
            oldValue.ExpenseType = "Buy/Purchase"

    elif(oldValue.askFor == 'Frequency'):
        textString = filteredText.lower()
        if("weekly" in textString or "per week" in textString):
            oldValue.frequency = "Weekly"
        elif("yearly" in textString or "per year" in textString or "annual" in textString):
            oldValue.frequency = "Yearly"
        elif("monthly" in textString or "per month" in textString or "every month" in textString):
            oldValue.frequency = "Monthly"

    # Check if Dialogflow had picked up a date (18th, last wednesday)
    if(oldValue.askFor == 'Date'):
        oldValue.paymentDate = dateparser.parse(str(filteredText))
        if(oldValue.paymentDate == None):
            print('failed to parse data')
            oldValue.paymentDate = ''

    if(oldValue.paymentDate == ''):
        if(req.get('queryResult').get('parameters').get('date')):
            oldValue.paymentDate = dateparser.parse(
                str(req.get('queryResult').get('parameters').get('date')))
            if(oldValue.recurrence == "Yes"):
                oldValue.DueDate = oldValue.paymentDate - \
                    timedelta(days=(oldValue.paymentDate.day-1))

            if(str(int(float(oldValue.Amount))) in str(req.get('queryResult').get('parameters').get('date'))):
                oldValue.Amount = '0'

        # Check if Dialogflow had picked up a date (this month, next june, last year)
        try:
            if(req.get('queryResult').get('parameters').get('date-period') != ''):
                if(req.get('queryResult').get('parameters').get('date-period').get('endDate')):
                    oldValue.paymentDate = dateparser.parse(
                        req.get('queryResult').get('parameters').get('date-period').get('endDate'))
                if(oldValue.recurrence == "Yes"):
                    oldValue.DueDate = oldValue.paymentDate - \
                        timedelta(days=(oldValue.paymentDate.day-1))

                # If the number caught by amount is in date, negate that.
                if(str(int(float(oldValue.Amount))) in str(req.get('queryResult').get('parameters').get('date'))):
                    oldValue.Amount = '0'

        except:
            print('Date Error')

    # Checking NLP API for Values

    changeVar = 0
    for entity in response.entities:
        entityDetectList = ["CONSUMER_GOOD", "OTHER", "WORK_OF_ART",
                            "UNKNOWN", "EVENT", "PERSON", "ORGANIZATION"]
        # For List of entities
        if any(x in enums.Entity.Type(entity.type).name for x in entityDetectList):
            if((entity.name.title() != 'Subscription' or entity.name.title() != 'Rent' or entity.name.title() != 'Purchase')):
                if(oldValue.fullEntity == 0 and (oldValue.askFor == 'None' or oldValue.askFor == 'Entity')):
                    oldValue.entitySend += (entity.name + ', ')
                    changeVar = 1

    # For date
        if ("DATE" in enums.Entity.Type(entity.type).name):
            oldValue.paymentDate = dateparser.parse(entity.name)
            if(oldValue.DueDate == "" and oldValue.recurrence == "Yes"):
                oldValue.DueDate = oldValue.paymentDate - \
                    timedelta(days=(oldValue.paymentDate.day-1))

    oldValue.fullEntity = changeVar

    # Detect Tense for Paid/Unpaid
    for token in response.tokens:
        # 3 = enum for Past
        if(token.part_of_speech.tense == 3):
            oldValue.paymentStatus = "Paid"
            if(oldValue.ExpenseType == "Rent/Subscription"):
                if(oldValue.paymentDate != ''):
                    oldValue.DueDate = oldValue.paymentDate - \
                        timedelta(days=(oldValue.paymentDate.day-1))

    listTosend = {'inputText':  str(filteredText)}
    oldValue.category = json.loads(json.dumps(sendResponse(
        json.loads(json.dumps(listTosend)))))['accountHead']

    result = 'Following is the Output: \n\n'
    if(oldValue.Amount != '0'):
        result += ' Amount : ' + \
            str(oldValue.currency) + ' ' + str(oldValue.Amount) + ' \n  \n'

    result += ' Entities : ' + oldValue.entitySend + ' \n  \n'
    result += ' ExpenseType: ' + oldValue.ExpenseType + ' \n  \n'
    if('Rent' in oldValue.ExpenseType):
        result += ' recurrence : ' + oldValue.recurrence + ' \n  \n'
        if('Yes' in oldValue.recurrence):
            result += ' Frequency : ' + oldValue.frequency + ' \n  \n'

    result += ' Payment Status : ' + oldValue.paymentStatus + ' \n  \n'

    if(oldValue.paymentStatus == 'Paid'):
        try:
            result += ' paymentDate : ' + \
                oldValue.paymentDate.strftime(r"%b %d %Y ") + ' \n  \n'
        except:
            print('No date yet')
        try:
            result += ' DueDate : ' + \
                oldValue.DueDate.strftime(r"%b %d %Y ") + ' \n  \n'
        except:
            print('No Due Date')

    result += ' Accounting Subhead : ' + oldValue.category + ' \n  \n'

    print('Missing Value = ' + oldValue.emptyList())
    oldValue.askFor = oldValue.emptyList()

    pprint(vars(oldValue))
    if 'None' in oldValue.emptyList():
        oldValue.clearIt()
    elif 'Amount' in oldValue.emptyList():
        result = 'How much was the amount for the transaction?'
    elif 'Date' in oldValue.emptyList():
        result = 'When did the transaction Occur? '
    elif 'Entity' in oldValue.emptyList():
        result = 'What was the transaction done for?'
    elif 'Frequency' in oldValue.emptyList():
        result = 'How freqently you want the transaction to repeat? \n (Yearly, Monthly, Weekly)'

    return {'fulfillmentText':  result}
