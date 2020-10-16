[![Build Status](https://travis-ci.com/TranslatorIIPrototypes/NodeNormalization.svg?branch=master)](https://travis-ci.com/TranslatorIIPrototypes/NodeNormalization)

# NodeNormalization

## Introduction

Node normalization takes a CURIE, and returns:

* The preferred CURIE for this entity
* All other known equivalent identifiers for the entity
* Semantic types for the entity as defined by the [Biolink Model](https://biolink.github.io/biolink-model/)

The data currently served by Node Normalization is created by the prototype project [Babel](https://github.com/TranslatorIIPrototypes/Babel), which attempts to find identifier equivalences, and makes sure that CURIE prefixes are BioLink Model compliant.  The NodeNormalization service, however, is independent of Babel and as improved identifier equivalence tools are developed, their results can be easily incorporated.

To determine whether Node Normalization is likely to be useful, check /get_semantic_types, which lists the BioLink semantic types for which normalization has been attempted, and /get_curie_prefixes, which lists the number of times each prefix is used for a semantic type.

For examples of service usage, see the example [notebook](documentation/NodeNormalization.ipynb).

Most users of NodeNormalization can access it via the public [service](https://nodenormalization-sri.renci.org/apidocs) but instructions follow for standing up a new instance of the service.

## Installation

Create a virtual environment

    > python -m venv nodeNormalization-env

Activate the virtual environment

    # on Linux
    > source nodeNodemaization-env/bin/activate
    # on Windows
    > source nodeNormalization-env/Scripts/activate 

Install requirements 

    > pip install -r requirements.txt

## Loading Redis


### Starting redis server 
The Load script can be used to put data to a running Redis instance. Inline with this we recommend using 
[R3 (Redis-REST with referencing)](https://github.com/TranslatorIIPrototypes/r3). 
### Config
Once we have a running
redis-server we can modify our config file located at `./config.json` as the following.

    {
    "compendium_directory": "<path to files>",
    "redis_port": <redis-server-port>,
    "redis_host": "<redis-host>",
    "redis_password": "<redis-password>"
    }   

`compendium_directory` Is a path to the files that are going to be loaded to the  redis instance. And example of the files' contents  
looks like :

    {id": {"identifier": "PUBCHEM:50986940"}, "equivalent_identifiers": [{"identifier": "PUBCHEM:50986940"}, {"identifier": "INCHIKEY:CYMOSKLLKPIPCD-UHFFFAOYSA-N"}], "type": ["chemical_substance", "named_thing", "biological_entity", "molecular_entity"]}
    {"id": {"identifier": "CHEMBL.COMPOUND:CHEMBL1546789", "label": "CHEMBL1546789"}, "equivalent_identifiers": [{"identifier": "CHEMBL.COMPOUND:CHEMBL1546789", "label": "CHEMBL1546789"}, {"identifier": "PUBCHEM:4879549"}, {"identifier": "INCHIKEY:FUIYIXDZTPMQEH-UHFFFAOYSA-N"}], "type": ["chemical_substance", "named_thing", "biological_entity", "molecular_entity"]}

where each line is a json parsable entry. 

### Loading

After the proper configuration run
 
    > cd  src
    > python load.py

### Kubernetes configurations
    kubernetes configurations and helm charts for this project can be found at: 
    
    note: the helm charts for edge normalization are also shared with node normalization
    
    https://github.com/helxplatform/translator-devops/helm/edge-normalization
    