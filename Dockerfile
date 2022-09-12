FROM renciorg/renci-python-image:v0.0.1

RUN mkdir /code
WORKDIR /code

# install requirements
ADD ./requirements.txt requirements.txt
RUN pip install -r requirements.txt # --src /usr/local/src

# install library
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

USER nru
ENTRYPOINT ["uvicorn", "--host", "0.0.0.0", "--port", "8080" , "--root-path", "/1.3", "--workers", "1", "--app-dir", "/code/", "--loop", "uvloop", "--http", "httptools",  "node_normalizer.server:app"]
