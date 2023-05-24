FROM amazon/aws-lambda-python:3.8

# WORKDIR /app
# Copy handler function (from the local app directory)
# COPY  index.py  .
# Install git
RUN yum update -y \
    && yum install -y git zip unzip wget tar gzip jq
# Make sure git is installed
RUN git version

# Install git-remote-codecommit
RUN pip install git-remote-codecommit

# # Clone aws-quant repo
# RUN git clone --mirror https://github.com/aws-samples/aws-machine-learning-university-accelerated-nlp.git aws-quant-tmp && ls -la aws-quant-tmp

# Install awscli
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

# Make sure awscli is installed
RUN aws --version

# Prepare codecommit
RUN git config --global credential.helper '!aws codecommit credential-helper $@'
RUN git config --global credential.UseHttpPath true

COPY . /var/task/base
COPY deployment/cdk/lib/shared/index.py /var/task/
RUN ls -la /var/task/*
# Overwrite the command by providing a different command directly in the template.
CMD ["/var/task/index.handler"]        