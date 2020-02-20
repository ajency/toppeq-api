def amountMessage(status):
    if(status == "Paid"):
        return 'How much was the amount for the expense?'
    else:
        return 'How much is the amount for the expense?'


def dateMessage(status):
    if(status == "Paid"):
        return 'When was the expense done?'
    else:
        return 'When are you planning to do the expense? '


def entityMessage(status):
    if(status == "Paid"):
        return 'What was the expense done for?'
    else:
        return 'What is the expense done for?'
    return


def frequencyMessage():
    return 'How freqently you want the transaction to repeat? \n (Yearly, Monthly, Weekly)'
