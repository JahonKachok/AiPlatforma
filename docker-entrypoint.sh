#!/bin/sh
set -e

python manage.py migrate --noinput
# input.css - Tailwind manba fayli (@import "tailwindcss"), u tarqatilmaydi.
python manage.py collectstatic --noinput --ignore=input.css
python manage.py setup_periodic_tasks
python manage.py setup_pult_periodic_tasks

exec "$@"
