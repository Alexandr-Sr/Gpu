
#!/usr/bin/env bash
export FLASK_APP=run:app
exec gunicorn --bind 0.0.0.0:8000 --workers 2 run:app
