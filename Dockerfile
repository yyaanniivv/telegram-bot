FROM python:3.9-slim-buster AS build-env
ADD . /app
WORKDIR /app
RUN pip install --upgrade pip && pip install -r ./requirements.txt

CMD ["python", "app.py"]
