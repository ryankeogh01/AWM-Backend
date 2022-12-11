FROM continuumio/miniconda3
MAINTAINER Ryan Keogh

RUN apt-get -y update && apt-get -y upgrade && \
    apt-get -y install build-essential libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info  && \
    conda update -n base conda && conda update -n base --all

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE=mydjango.settings

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY ENV.yml /usr/src/app
RUN conda env create -n mydjango --file ENV.yml

RUN echo "conda activate mydjango" >> ~/.bashrc
SHELL ["/bin/bash", "--login", "-c"]

RUN conda config --add channels conda-forge && conda config --set channel_priority strict
RUN cat ~/.condarc
RUN conda install gunicorn

COPY . /usr/src/app

EXPOSE 8002

CMD gunicorn mydjango.wsgi --config gunicorn.conf.py