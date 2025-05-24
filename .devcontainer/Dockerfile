FROM mcr.microsoft.com/vscode/devcontainers/python:3.10

# Install Java for DynamoDB Local
RUN apt-get update && \
    apt-get install -y default-jre-headless wget unzip && \
    apt-get clean

# Set up workspace
WORKDIR /workspace

# Copy requirements.txt
COPY app/requirements.txt /workspace/requirements.txt

# Copy install script
COPY .devcontainer/install.sh /usr/local/bin/install.sh
RUN chmod +x /usr/local/bin/install.sh