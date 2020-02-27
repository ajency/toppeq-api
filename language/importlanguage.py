import json
import os
default = 'en'

def defaultLanguage():
    return default

def getLanguage(lang=default):
    print("here = ",os.getcwd())
    with open('language/'+default+'.json') as f:
        data = json.load(f)

    return data
