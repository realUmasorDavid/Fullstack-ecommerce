import os
import json
from dotenv import load_dotenv
import requests
load_dotenv()

secret_key = os.getenv('paystack')

def initialize_payment(amount, email, callback_url):
    url = 'https://api.paystack.co/transaction/initialize'
    headers = {
        'Authorization': f'Bearer {secret_key}',
        'Content-Type': 'application/json',
    }
    data = {
        'amount': int(amount) * 100,  # Paystack expects amount in kobo
        'email': email,
        'callback_url': callback_url,
    }

    response = requests.post(url, headers=headers, json=data)
    response_data = response.json()

    if response_data.get('status'):
        return response_data.get('data')
    else:
        return None

def verify_payment(reference):
    url = f'https://api.paystack.co/transaction/verify/{reference}'
    headers = {
        'Authorization': f'Bearer {secret_key}',
    }

    response = requests.get(url, headers=headers)
    response_data = response.json()

    if response_data.get('status'):
        return response_data.get('data')
    else:
        return None
