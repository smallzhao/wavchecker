FROM audiofilter:v0.1

COPY requirements.txt requirements.txt

RUN apt-get install -y git autoconf autogen automake build-essential libasound2-dev libflac-dev \
    libogg-dev libtool libvorbis-dev pkg-config python

RUN export PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple/ && \
    python3 -m pip install -U pip && \
    pip3 install --no-cache-dir -r requirements.txt

COPY src /workdir/src

WORKDIR /workdir/src/filters/utils/libsndfile
RUN ./autogen.sh && \
    ./configure --enable-werror && \
    make && \
    make check && \
    make install

WORKDIR /workdir/src/filters/utils/fftw3
RUN ./configure && \
    make && \
    make install

WORKDIR /workdir/src

CMD ["python3", "main.py"]
