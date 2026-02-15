# Source - https://stackoverflow.com/a/45611960
# Posted by NGix
# Retrieved 2026-02-15, License - CC BY-SA 3.0

import sys
import django
from django.conf import settings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

INSTALLED_APPS = [
    'db',
]

DATABASES = {
    'default': {
        'ENGINE' : 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

settings.configure(
    INSTALLED_APPS = INSTALLED_APPS,
    DATABASES = DATABASES,
)

django.setup()

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)