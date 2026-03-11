#!/bin/bash

echo "Installing BashForge..."

mkdir -p ~/.bashforge

cp bashforge.py ~/.bashforge/

chmod +x ~/.bashforge/bashforge.py

sudo ln -s ~/.bashforge/bashforge.py /usr/local/bin/bashforge

echo "Installed! Run using:"
echo "bashforge"