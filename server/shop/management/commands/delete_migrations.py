# shop/management/commands/delete_migrations.py
import os
import shutil
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Deletes all migration files except __init__.py'

    def handle(self, *args, **kwargs):
        migrations_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'migrations')
        for filename in os.listdir(migrations_dir):
            if filename != '__init__.py':
                file_path = os.path.join(migrations_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
        self.stdout.write(self.style.SUCCESS('Migration files deleted successfully'))
