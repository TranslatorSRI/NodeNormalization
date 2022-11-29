FROM renciorg/renci-python-image:v0.0.1

RUN mkdir /code
WORKDIR /code

# install library
COPY ./requirements.txt requirements.txt
COPY ./setup.py setup.py
COPY ./node_normalizer node_normalizer
COPY ./redis_config.yaml redis_config.yaml

# install requirements
RUN pip install -r requirements.txt

RUN chmod 777 ./

USER nru
ENTRYPOINT ["uvicorn", "--host", "0.0.0.0", "--port", "8080", "--root-path", "/1.3", "--workers", "1", "node_normalizer.server:app"]
