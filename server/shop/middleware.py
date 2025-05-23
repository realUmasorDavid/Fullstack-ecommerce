from django.shortcuts import redirect
from datetime import datetime
from django.urls import reverse


class CountdownMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.countdown_date = datetime(2024, 11, 15, 9, 0, 0)  # Set your countdown date here

    def __call__(self, request):
        if datetime.now() < self.countdown_date:
            if not request.user.is_authenticated or not request.user.profile.is_staff:
                if request.path != reverse('coming_soon'):
                    return redirect('coming_soon')
        response = self.get_response(request)
        return response