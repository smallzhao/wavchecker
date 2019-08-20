FROM ubuntu:16.04

ENV download=null

RUN rm /etc/apt/sources.list
COPY sources.list /etc/apt/sources.list

RUN apt-get update
RUN apt-get install -y sox python3-dev python3-pip ffmpeg

COPY requirements.txt requirements.txt

RUN export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple/ && \
    pip3 install --no-cache-dir -r requirements.txt

COPY src /workdir/src

WORKDIR /workdir/src

CMD ["python3", "main.py"]
