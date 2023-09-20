# nodenorm-loader
# 
# Eventually we might want to set up 
#

# Use the RENCI Python image to make it easier to work with other
# RENCI Docker packages and to make sure we have an up to date image.
# (https://github.com/TranslatorSRI/RENCI-Python-image)
FROM renciorg/renci-python-image:latest

# Upgrade system files
RUN apt update
RUN apt -y upgrade

# Install wget, Python 3, pip and venv.
apt-get install -y wget python3 python3-venv python3-pip
