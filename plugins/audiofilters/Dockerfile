FROM registry.cn-beijing.aliyuncs.com/shujutang/checknoise:v0.10.0

ENV LANG C.UTF-8

COPY requirements.txt requirements.txt

RUN apt-get install -y ffmpeg

RUN export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple/ && \
    python3 -m pip install -U pip && \
    pip3 install --no-cache-dir -r requirements.txt

COPY src /workdir/src

WORKDIR /workdir/src

CMD ["python3", "main.py"]
