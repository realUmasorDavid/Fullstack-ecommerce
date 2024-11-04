from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from requests.exceptions import ConnectionError
from datetime import datetime
from django.urls import reverse
from django.contrib.auth.models import User

class ConnectionErrorMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if isinstance(exception, ConnectionError):
            return redirect('connection_error_view')

class CountdownMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.countdown_date = datetime(2024, 11, 15, 9, 0, 0)  # Set your countdown date here

    def __call__(self, request):
        if datetime.now() < self.countdown_date:
            if not request.user.is_authenticated:
                return redirect('coming_soon')
            elif not request.user.profile.is_staff:
                return redirect('coming_soon')
        response = self.get_response(request)
        return response
