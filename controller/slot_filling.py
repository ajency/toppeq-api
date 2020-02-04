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
from random import randint
import time
import dateparser
import dateutil.relativedelta
from datetime import datetime, date, time, timedelta
from pprint import pprint

import re

slot_fill = Blueprint('slot_fill', __name__)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\Dattaprasad\Downloads\intent.json"

client = dialogflow_v2.SessionsClient()
session = client.session_path('classify-intents-ujpxuu', '1234abcdpqrs')

client1 = language_v1.LanguageServiceClient()
defaultCurrency = 'INR'


class lastEntry():
    Amount = '0'
    entitySend = ''
    ExpenseType = ""
    recurrence = "No"
    frequency = "Monthly"
    paymentDate = ''
    DueDate = ""
    paymentStatus = 'Pending'
    Description = ''
    currency = defaultCurrency
    fullEntity = 0

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
        self.frequency = "Monthly"
        self.paymentDate = ''
        self.DueDate = ""
        self.paymentStatus = 'Unpaid'
        self.Description = ''
        self.currency = defaultCurrency
        self.fullEntity = 0


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

    # Step 3.1: if price is detected by NLP, mark it with currency
    if(oldValue.Amount == '0'):
        flag = 0
    else:
        flag = 1

    if(oldValue.Amount == '0'):
        for entity in response.entities:
            if(enums.Entity.Type(entity.type).name == "PRICE" and flag == 0):
                oldValue.Amount = entity.metadata[u"value"]
                oldValue.currency = entity.metadata[u"currency"]
                flag = 1

        # Step 3.3 Check from Dialogflow
        if(flag == 0):
            if(req.get('queryResult').get('parameters').get('PRICE')):
                oldValue.Amount = str(
                    req.get('queryResult').get('parameters').get('PRICE'))
                flag = 1

        # Step 3.4 In case nothing is found, pick a number from the list
        if(flag == 0):
            maxValue = 0
            for entity in response.entities:
                if(enums.Entity.Type(entity.type).name == "NUMBER"):
                    maxValue = int(float(entity.metadata[u"value"])) if(
                        int(float(entity.metadata[u"value"])) > int(float(maxValue))) else maxValue

            if(maxValue > 0):
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
        else:
            oldValue.ExpenseType = "Buy/Purchase"

    # Check if Dialogflow had picked up a date (18th, last wednesday)
    if(oldValue.paymentDate == ''):
        if(req.get('queryResult').get('parameters').get('date')):
            oldValue.paymentDate = dateparser.parse(
                req.get('queryResult').get('parameters').get('date'))
            if(oldValue.recurrence == "Yes"):
                oldValue.DueDate = oldValue.paymentDate - \
                    timedelta(days=(oldValue.paymentDate.day-1))

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
                    oldValue.Amount = 0
        except:
            print('Date Error')

    # Checking NLP API for Values
    if(oldValue.fullEntity == 0):
        for entity in response.entities:
            entityDetectList = ["CONSUMER_GOOD", "OTHER", "WORK_OF_ART",
                                "UNKNOWN", "EVENT", "PERSON", "ORGANIZATION"]
            # For List of entities
            if any(x in enums.Entity.Type(entity.type).name for x in entityDetectList):
                if((entity.name.title() != 'Subscription' or entity.name.title() != 'Rent')):
                    oldValue.entitySend += (entity.name + ', ')

        # For date
            if ("DATE" in enums.Entity.Type(entity.type).name):
                oldValue.paymentDate = dateparser.parse(entity.name)
                if(oldValue.DueDate == "" and oldValue.recurrence == "Yes"):
                    oldValue.DueDate = oldValue.paymentDate - \
                        timedelta(days=(oldValue.paymentDate.day-1))
        oldValue.fullEntity = 1

    # Detect Tense for Paid/Unpaid
    for token in response.tokens:
        # 3 = enum for Past
        if(token.part_of_speech.tense == 3):
            oldValue.paymentStatus = "Paid"
            if(oldValue.ExpenseType == "Rent/Subscription"):
                if(oldValue.paymentDate != ''):
                    oldValue.DueDate = oldValue.paymentDate - \
                        timedelta(days=(oldValue.paymentDate.day-1))

    # Output String
    value = ''
    if(int(float(oldValue.Amount)) != 0):
        value += 'Amount = ' + str(format(int(float(oldValue.Amount)))+', ')
        
        value += 'Currency = ' + str(format(oldValue.currency)+', ')


    value += 'purchaseType = ' + oldValue.ExpenseType + ', '

    # Entities(Expenses for)
    if(oldValue.entitySend != ''):
        value += 'Expense For(Entities): ' + str(oldValue.entitySend)+' '

    # description
    if(oldValue.Description == ''):
        oldValue.Description = inputText
        value += 'Description = '+oldValue.Description+', '

    # Recurrence
    if(oldValue.recurrence == "Yes"):
        value += 'Recurrence: Yes , Frequency: ' + oldValue.frequency + ', '

    # Due date, Payment Day
    try:
        value += 'PaymentDate = ' + \
            str(oldValue.paymentDate.strftime(r"%b %d %Y ")) + ', '
    except:
        print('Date not Set')

    if(oldValue.DueDate != ""):
        value += 'Due Date: ' + \
            str(oldValue.DueDate.strftime(r"%b %d %Y ")) + ', '

    # Payment Status
    value += 'paymentStatus = ' + oldValue.paymentStatus+' '

    resultList =  str(req.get('queryResult').get('fulfillmentText'))

    if(resultList.find('?') == -1):
        result = ''
        result += 'Amount = ' + str(oldValue.Amount) + ' \n '
        result += 'currency = ' + str(oldValue.currency) + ' \n '
        result += 'recurrence = ' + oldValue.recurrence + ' \n '
        result += 'ExpenseType = ' + oldValue.ExpenseType + ' \n '  
        result += 'Entities = ' + oldValue.entitySend + ' \n '  
        result += 'Description = ' + oldValue.Description + ' \n '
        try:
            result += 'paymentDate = ' + \
                oldValue.paymentDate.strftime(r"%b %d %Y ") + ' \n '
        except:
            print('No date yet')
        try:
            result += 'DueDate = ' + \
                oldValue.DueDate.strftime(r"%b %d %Y ") + ' \n '
        except:
            print('No Due Date')
        oldValue.clearIt()
    else:
        result = req.get('queryResult').get('fulfillmentText')

    pprint(vars(oldValue))
    return {'fulfillmentText':  result}

