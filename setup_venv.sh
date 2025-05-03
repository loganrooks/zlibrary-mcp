#!/bin/bash

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the required packages
pip install zlibrary

# Create a requirements.txt file
pip freeze > requirements.txt