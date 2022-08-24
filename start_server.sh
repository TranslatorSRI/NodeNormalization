#!/bin/bash

. venv/bin/activate && uvicorn --host "0.0.0.0" --port "8080" --root-path "/1.3" --workers "1" --loop "uvloop" --http "httptools" node_normalizer.server:app