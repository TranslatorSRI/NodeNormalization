# Node Normalization

Node normalization takes a CURIE, and returns:
* The preferred CURIE for this entity
* All other known equivalent identifiers for the entity
* Semantic types for the entity as defined by the <a href="https://biolink.github.io/biolink-model/">BioLink Model</a>

  The data served by Node Normalization is created by <a href="https://github.com/TranslatorIIPrototypes/Babel">Babel</a>,
  which attempts to find identifier equivalences, and makes sure that CURIE prefixes are BioLink Model Compliant.  To
  determine whether Node Normalization is likely to be useful, check /get_semantic_types, which lists the BioLink semantic
  types for which normalization has been attempted, and /get_curie_prefixes, which lists the number of times each prefix

## Deployment

Assume a Redis database running on localhost port 6379.

### Local

```bash
pip install -r requirements.txt
export REDIS_HOST=localhost
export REDIS_PORT=6379
./main.py --port 6380
```

### Docker

```bash
docker build -t redis_rest .
docker run \
    -p 6380:6380 \
    --env REDIS_HOST=host.docker.internal \
    --env REDIS_PORT=6379 \
    redis_rest --port 6380
```

### Docker compose

To run both Redis database and REST interface, a docker-compose file is provided:

```bash
docker-compose up
```

## Usage

    <https://nodenormalization-sri.renci.org/apidocs/>
