FROM python:3.9

ARG glider_gid_uid=1000
COPY . /glider-dac
ENV UDUNITS2_XML_PATH=/usr/share/xml/udunits
RUN apt-get update && \
    apt-get -y install rsync \
                       netcdf-bin && \
    cd /usr/local/src && pip install -U pip && \
    pip install --no-cache -r /glider-dac/requirements.txt && \
    rm -rf /var/lib/apt/lists/*
# TODO: move logs elsewhere
VOLUME /glider-dac/logs/ /data /usr/local/lib/python3.9/site-packages/compliance_checker/data
WORKDIR /glider-dac
RUN mkdir -p /data/submission /data/data/priv_erddap /data/data/pub_erddap \
             /erddapData/flag /erddapData/hardFlag  \
             /data/catalog/priv_erddap
ENV PYTHONPATH="${PYTHONPATH:-}:/glider-dac"
ENV FLASK_APP=glider_dac:create_app

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "glider_dac:create_app()"]
