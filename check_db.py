import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ponteglam.settings')
django.setup()
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='services_appointmentservice';")
print("Columns in services_appointmentservice:")
print([row[0] for row in cursor.fetchall()])
