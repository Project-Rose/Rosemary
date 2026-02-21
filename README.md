# Rosemary
Project Rosé's Discord server helper bot, written in Python.
# Setup
- Copy .env.example to .env and modify the values inside to your liking.
- Run `python3 -m pip install -r requirements.txt`
- Run `python3 manage.py migrate`
- And finally, run `python3 main.py` to start the bot

## if you want to host the frontend
Instructions are short for this (because I'm lazy), but should be enough if you know what you're doing

- Set debug to False in .env if not already done.
- Install gunicorn and run the wsgi application (rosemary.wsgi) with it (use systemd or whatever if you want to keep this running all the time)
- Run `python3 manage.py collectstatic` to get all the static files in (working directory)/static/.
- Serve the static files using apache2 or whatever you want 