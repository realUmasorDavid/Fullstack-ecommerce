from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from requests.exceptions import ConnectionError

class ConnectionErrorMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if isinstance(exception, ConnectionError):
            return redirect('connection_error_view')
