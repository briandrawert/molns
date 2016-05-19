FROM ubuntu:14.04

RUN apt-get update

# Set up base environment.
RUN apt-get install -yy \
    software-properties-common \
    python-software-properties \
    wget \
    git \
    ipython

# Create and switch to new user.
RUN useradd -ms /bin/bash ubuntu
USER ubuntu
ENV HOME /home/ubuntu
WORKDIR /home/ubuntu