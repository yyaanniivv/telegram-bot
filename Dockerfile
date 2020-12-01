FROM python:3.9-slim-buster AS build-env

# This helps docker not rebuild unless "requirements.txt" is touched.
COPY ./requirements.txt .

# # Gcc is needed for one of the packages.
RUN apt-get update \
  && apt-get install -y --no-install-recommends gcc libssl-dev python3-dev libffi-dev\
  && rm -rf /var/lib/apt/lists/* \
  && pip install --upgrade pip \
  && pip install -r requirements.txt \
  && apt-get purge -y --auto-remove gcc libssl-dev python3-dev libffi-dev

USER 1000:1000
COPY . /app
WORKDIR /app
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
