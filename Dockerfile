FROM python:3.8.1-buster

# install basic tools
RUN apt-get update
RUN apt-get install -yq \
    vim

RUN mkdir /code
WORKDIR /code

# install requirements
ADD ./requirements.txt requirements.txt
RUN pip install -r requirements.txt # --src /usr/local/src

# install library
ADD ./swagger_ui swagger_ui
ADD ./setup.py setup.py
ADD ./node_normalizer node_normalizer
ADD ./config.json config.json
ADD ./redis_config.yaml redis_config.yaml
ADD ./load.py load.py

RUN pip install -e .

# setup entrypoint
# gunicorn, hypercorn also options https://fastapi.tiangolo.com/deployment/manually/
# ENTRYPOINT ["python", "-m" , "uvicorn", "node_normalizer.server:app", "--app-dir", "/home/murphy/", "--port", "6380"]


RUN chmod 777 ./

# create a new user and use it.
RUN useradd -M -u 1001 nonrootuser
USER nonrootuser
ENTRYPOINT ["uvicorn", "--host", "0.0.0.0", "--port", "8080" , "--root-path", "/1.2", "--workers", "1", "--app-dir", "/code/", "--loop", "uvloop", "--http", "httptools",  "node_normalizer.server:app"]
