web: cd estoque_app && gunicorn --workers 4 --threads 2 --worker-class gthread --bind 0.0.0.0:$PORT run:app
release: cd estoque_app && flask --app run.py db upgrade && python seed.py
