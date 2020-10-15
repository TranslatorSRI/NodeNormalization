FROM python:3.8-slim

# install basic tools
RUN apt-get update
RUN apt-get install -yq vim


# set up murphy
RUN mkdir /home/murphy
ENV HOME=/home/murphy
ENV USER=murphy
WORKDIR /home/murphy

VOLUME /home/murphy/config
VOLUME /home/murphy/data

# install requirements
ADD ./requirements.txt /home/murphy/requirements.txt
RUN pip install -r /home/murphy/requirements.txt --src /usr/local/src

# install library
ADD ./r3 /home/murphy/r3
ADD ./swagger_ui /home/murphy/swagger_ui
ADD ./main.py /home/murphy/main.py
ADD ./load.py /home/murphy/load.py
ADD ./setup.py /home/murphy/setup.py
ADD ./src /home/murphy/src

RUN pip install -e .
