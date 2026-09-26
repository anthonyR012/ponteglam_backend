# Third-party Libraries
from celery import shared_task


@shared_task(bind=True)
def add_five(self, number):
    number + 5
    return number
