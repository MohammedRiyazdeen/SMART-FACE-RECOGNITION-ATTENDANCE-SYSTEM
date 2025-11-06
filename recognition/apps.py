import os
from django.apps import AppConfig

class RecognitionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recognition'

    def ready(self):
        # We only want to start the scheduler in the main process, not in the reloader process
        if os.environ.get('RUN_MAIN', None) == 'true':
            from .scheduler import start_scheduler
            start_scheduler()
