# NodeNormalization
Service that produces Translator compliant nodes given a curie.

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

After the proper configration run
 
    > cd  src
    > python load.py
    

