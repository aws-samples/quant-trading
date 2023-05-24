curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o Miniconda3-latest-Linux-x86_64.sh
chmod +x Miniconda3-latest-Linux-x86_64.sh
./Miniconda3-latest-Linux-x86_64.sh  -b
PATH=/root/miniconda3/bin:${PATH}
# RUN ls -la
# RUN ls -la bin
# RUN conda init bash
# RUN exec bash
RUN conda create --name bpipe python=3.8 -y
RUN conda init bash
# ENV PATH=/root/miniconda3/envs/${PYTHON_ENVS}/bin:${PATH}
RUN source activate bpipe
RUN conda install -c conda-forge blpapi -y
RUN pip install xbbg==0.7.7a3
RUN mkdir /src
COPY bpipe.py /src/
COPY stream_data.py /src/