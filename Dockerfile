FROM python:3.9-slim-buster AS build-env
COPY ./requirements.txt .
RUN pip install --upgrade pip && pip install -r ./requirements.txt
COPY . /app
WORKDIR /app
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
