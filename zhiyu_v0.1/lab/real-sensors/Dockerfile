FROM python:3.12.14-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea
# Regional mirror listed by Debian; retain the base image's Signed-By keyring.
# Never accept unsigned indexes/packages or disable HTTPS certificate checks.
RUN sed -i 's|http://deb.debian.org|https://mirrors.ustc.edu.cn|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=5 -o Acquire::https::Timeout=30 -o APT::Update::Error-Mode=any update \
    && apt-get -o Acquire::Retries=5 -o Acquire::https::Timeout=30 install -y --no-install-recommends suricata openssl \
    && dpkg-query -W > /package-versions.txt \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /lab
# Capture the public, disposable Basic account used only by this isolated Lab.
# Never enable credential-header logging for a real/customer service via this image.
RUN sed -i 's/#custom: \[Accept-Encoding, Accept-Language, Authorization\]/custom: [Authorization]/' /etc/suricata/suricata.yaml
COPY target.py client.py suricata_start.py ./
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
CMD ["python", "target.py"]
