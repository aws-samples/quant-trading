FROM public.ecr.aws/lambda/python:3.7 AS builder
COPY lambda/extension.zip extension.zip
RUN yum install -y unzip \
  && unzip extension.zip -d /opt \
  && rm -f extension.zip

FROM amazon/aws-lambda-python:3.7
ARG SSM_PREFIX 
ENV SSM_PREFIX ${SSM_PREFIX}
RUN echo SSM_PREFIX: $SSM_PREFIX
ARG AWS_REGION
ENV AWS_REGION ${AWS_REGION}
RUN echo AWS_REGION: ${AWS_REGION}
COPY --from=builder /opt /opt
RUN pip install pandas
RUN pip install xbbg
RUN pip install pyEX
RUN pip install  boto3
RUN pip install python-binance
RUN pip install awswrangler
#RUN conda install -c conda-forge ta-lib -y

COPY lambda/python/ /var/task
COPY shared /var/task/shared
RUN ls -la /var/task/*