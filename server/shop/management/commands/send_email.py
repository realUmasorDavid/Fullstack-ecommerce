from django.core.management.base import BaseCommand
from django.core.mail import send_mass_mail
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Send a marketing email to all users'

    def handle(self, *args, **kwargs):
        subject = 'Marketing Email Subject'
        message = 'This is the body of the marketing email.'
        from_email = 'Marrigold Django <davidumasor18@gmail.com>'

        emails = [(subject, message, from_email, [user.email]) for user in User.objects.all()]

        send_mass_mail(emails, fail_silently=False)
        self.stdout.write(self.style.SUCCESS('Successfully sent marketing emails'))
