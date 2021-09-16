FROM python:3.8.1-buster

# install basic tools
RUN apt-get update
RUN apt-get install -yq \
    vim

# set up murphy
RUN mkdir /home/murphy
ENV HOME=/home/murphy
ENV USER=murphy
WORKDIR /home/murphy

# install requirements
ADD ./requirements.txt /home/murphy/requirements.txt
RUN pip install -r /home/murphy/requirements.txt --src /usr/local/src

# install library
ADD ./swagger_ui /home/murphy/swagger_ui
ADD ./setup.py /home/murphy/setup.py
ADD ./node_normalizer /home/murphy/node_normalizer
ADD ./config.json /home/murphy/config.json
ADD ./redis_config.yaml /home/murphy/redis_config.yaml
ADD ./load.py /home/murphy/load.py

RUN pip install -e .

# setup entrypoint
# gunicorn, hypercorn also options https://fastapi.tiangolo.com/deployment/manually/
# ENTRYPOINT ["python", "-m" , "uvicorn", "node_normalizer.server:app", "--app-dir", "/home/murphy/", "--port", "6380"]

ENTRYPOINT ["uvicorn", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--app-dir", "/home/murphy/", "node_normalizer.server:app"]

