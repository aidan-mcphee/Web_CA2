#!/bin/bash

echo "PostgreSQL is ready, running migrations..."

sleep 1

echo '----migrating'
# Run migrations
python manage.py makemigrations
python manage.py migrate

#create django superuser if not exists
echo '----ensuring superuser exists'
addsuperuser="from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin')"
echo "$addsuperuser" | python manage.py shell

# run commands

# Start the web server
exec "$@"