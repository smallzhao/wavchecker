ARG REGISTRY=registry.cn-beijing.aliyuncs.com/shujutang
ARG TAG=0.10.0

FROM ${REGISTRY}/wooey-base:${TAG}
MAINTAINER Zhao WenHua zhaowenhua@datatang.com

COPY requirements.txt app-requirements.txt

RUN export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple/ && \
    pip install --no-cache-dir -r app-requirements.txt

COPY asr.py wavcheck.py
RUN python manage.py addscript wavcheck.py

COPY .kube /.kube
COPY data /data

COPY run-server run-server

