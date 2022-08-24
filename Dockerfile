FROM python:3.10.6-buster

# update/install basic tools
RUN apt-get update
RUN apt-get -y dist-upgrade
RUN apt-get install -yq build-essential curl

# create a new non-root user
RUN groupadd -r nru && useradd -m -r -g nru nru
RUN chmod 755 /home/nru

ENV PATH="/home/nru/.cargo/bin:/home/nru/.local/bin:${PATH}"

USER nru
RUN curl --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal

RUN python -m pip install --upgrade pip

RUN mkdir /home/nru/code
WORKDIR /home/nru/code

# install requirements
COPY ./requirements.txt requirements.txt
COPY ./swagger_ui swagger_ui
COPY ./setup.py setup.py
COPY ./nn_io_rs nn_io_rs
COPY ./node_normalizer node_normalizer
COPY ./config.json config.json
COPY ./redis_config.yaml redis_config.yaml
COPY ./load.py load.py
COPY ./pyproject.toml pyproject.toml
COPY ./start_server.sh start_server.sh

USER root
RUN chown -R nru:nru ./
USER nru
RUN python -m venv ./venv

RUN . venv/bin/activate && pip install -r requirements.txt --no-cache-dir && maturin develop -r -m ./nn_io_rs/Cargo.toml

# setup entrypoint
# gunicorn, hypercorn also options https://fastapi.tiangolo.com/deployment/manually/
#ENTRYPOINT ["python", "-m" , "uvicorn", "node_normalizer.server:app", "--app-dir", "/home/murphy/", "--port", "6380"]

CMD ./start_server.sh
