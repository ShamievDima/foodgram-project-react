FROM python:3.9-slim

WORKDIR /app
COPY . .
RUN pip install --upgrade pip && pip install -r requirements.txt
ADD django_entrypoint.sh /django_entrypoint.sh
RUN chmod a+x /django_entrypoint.sh
ENTRYPOINT ["/django_entrypoint.sh"]
CMD gunicorn foodgram.wsgi:application --bind 0.0.0.0:8000