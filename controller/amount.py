# import flask dependencies
from __future__ import print_function
from flask import Flask, request, make_response, jsonify, Blueprint
from google.cloud import language_v1, language
from google.cloud.language_v1 import enums
from text2digits import text2digits
import sys
import os
import json
import re

amount = Blueprint('amount', __name__)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"../amount.json"

# setting default values which can be configured
defaultCurrency = 'INR'


class getAmount():

    amount = '0'
    currency = defaultCurrency

    def writeAmt(self, amt, curr=defaultCurrency):
        self.amount = amt
        self.currency = curr

    def readAmt(self):
        return self.amount

    def readCurr(self):
        return self.currency


# initialize the flask app
client = language_v1.LanguageServiceClient()


def toLowercase(text):
    # converts input string to lower case.
    return text.lower()


def removeStopwords(text):
    # removes stopwords from the text
    stopWords = ["i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as",
                 "until", "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"]
    stopWords = [x + ' ' for x in stopWords]
    big_regex = re.compile(r'\b%s\b' %
                           r'\b|\b'.join(map(re.escape, stopWords)))
    return big_regex.sub("", text)


def convertWordstoNum(text):

    t2d = text2digits.Text2Digits()
    convertedText = t2d.convert(text)
    secondConvertedText = re.sub(
        r'(?P<money>[0-9]+)( |)l ', r'\g<money>00000 ', convertedText)
    return re.sub(r'(?P<money>[0-9]+)( |)cr ', r'\g<money>0000000 ', secondConvertedText)


def removeConsecutiveSpaces(text):
    value = re.sub(
        r'(?P<number1>[0-9]+) (?P<number2>[0-9]+) ', r'\g<number1>\g<number2>', text+' ')
    return value


def filterResults(text):
    return convertWordstoNum(removeConsecutiveSpaces(removeStopwords(toLowercase(text))))


def results():
    # build a request object
    req = request.get_json(force=True)
    real_amount = getAmount()

    inputText = str(req.get('queryResult').get('queryText'))
    # Step 1:  Convert input text to lowercase and removing stopwords

    filteredText = filterResults(inputText)

    # Step 2: call to Google NL API with the filtered text

    document = language.types.Document(
        content=filteredText,
        type=language.enums.Document.Type.PLAIN_TEXT
    )
    response = client.analyze_entities(document)

    # Step 3.1: if price is detected by NLP, mark it with currency
    flag = 0
    for entity in response.entities:
        if(enums.Entity.Type(entity.type).name == "PRICE"):
            real_amount.writeAmt(
                entity.metadata[u"value"], entity.metadata[u"currency"])
            flag = 1
            break

    # Step 3.2 : Checking number followed by /- condition to get amount
    if(flag == 0):
        number = re.search(r'[0-9]+\/-', inputText)
        if((number) is not None):
            number = number.group(0).replace('/-', '')
            real_amount.writeAmt(number)
            flag = 1

    # Step 3.3 Check from Dialogflow
    if(flag == 0):
        if(req.get('queryResult').get('parameters').get('PRICE')):
            real_amount.writeAmt(
                str(req.get('queryResult').get('parameters').get('PRICE')))

    # Step 3.4 In case nothing is found, pick a number from the list
    if(flag == 0):
        for entity in response.entities:
            if(enums.Entity.Type(entity.type).name == "NUMBER"):
                real_amount.writeAmt(entity.metadata[u"value"])
                flag = 1

    value = 'Amount: ' + str(real_amount.readCurr()) + ' ' + \
        str(format(int(float(real_amount.readAmt())), ',d'))
    return {'fulfillmentText':  value}


# create a route for webhook
@amount.route('/amount/', methods=['GET', 'POST'])
def webhook():
    return make_response(jsonify(results()))
