FROM amazonlinux:2018.03
ARG SSM_PREFIX
ENV SSM_PREFIX ${SSM_PREFIX}
RUN echo SSM_PREFIX: $SSM_PREFIX
ARG AWS_REGION
ENV AWS_DEFAULT_REGION ${AWS_REGION}
RUN echo AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION}
ARG PY_VERSION=3.7
ENV conda_version=Anaconda3-2022.10-Linux-x86_64.sh
RUN echo 'we are running some # of cool things'
RUN ulimit -n 1024 && yum -y update
RUN ulimit -n 1024 && yum install -y wget
RUN ulimit -n 1024 && yum install -y git
RUN ulimit -n 1024 && yum install -y unzip
RUN ulimit -n 1024 && yum install -y zip
RUN ulimit -n 1024 && yum install -y bzip2
RUN wget https://repo.continuum.io/archive/${conda_version}
RUN bash ${conda_version} -b
ENV PATH=/root/anaconda3/bin:${PATH}
#ENV PY_PACKAGE_DIR=/root/miniconda3/envs/lambda_layer/lib/python$PY_VERSION/site-packages
ENV CUSTOM_SOURCE_DIR=/src
ENV PYTHON_ENVS=fsibd_python
RUN conda create -n ${PYTHON_ENVS} python=3.7 -y
ENV PATH=/root/anaconda3/envs/${PYTHON_ENVS}/bin:${PATH}
RUN source activate ${PYTHON_ENVS}
RUN conda install -n ${PYTHON_ENVS} pandas -y
RUN conda install -n ${PYTHON_ENVS} fsspec -y
RUN /root/anaconda3/envs/${PYTHON_ENVS}/bin/pip install python-binance
RUN /root/anaconda3/envs/${PYTHON_ENVS}/bin/pip install pyEX
RUN /root/anaconda3/envs/${PYTHON_ENVS}/bin/pip install awswrangler
RUN /root/anaconda3/envs/${PYTHON_ENVS}/bin/pip install xbbg==0.7.7a3
RUN /root/anaconda3/envs/${PYTHON_ENVS}/bin/pip install blpapi --index-url=https://bcms.bloomberg.com/pip/simple/
RUN conda install -n ${PYTHON_ENVS} numpy -y
RUN conda install -n ${PYTHON_ENVS} boto3 -y
RUN conda install -n ${PYTHON_ENVS} s3fs -y
RUN conda install -n ${PYTHON_ENVS} -c conda-forge ta-lib -y
##### RUN conda install -n ${PYTHON_ENVS} hashlib -y
ENV ENTRY_POINT='source activate '${PYTHON_ENVS}
RUN mkdir ${CUSTOM_SOURCE_DIR}
COPY batch/python/ ${CUSTOM_SOURCE_DIR}
COPY shared ${CUSTOM_SOURCE_DIR}/shared
RUN ls -la ${CUSTOM_SOURCE_DIR}/*
ENV PYTHONPATH=${CUSTOM_SOURCE_DIR}
RUN curl "https://s3.amazonaws.com/aws-cli/awscli-bundle.zip" -o "awscli-bundle.zip"
RUN unzip awscli-bundle.zip
RUN ./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws
RUN aws --version
RUN aws configure set region ${AWS_REGION}
ENTRYPOINT ["python3.7"]
#CMD ["conda activate fsibd_python"]
#RUN /root/anaconda3/envs/lambda_layer/bin/pip install pyEX
