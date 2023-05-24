import json
import boto3
import datetime
import time
import random
import sys
import os

import pandas as pd
# IEX
from sseclient import SSEClient
# BPIPE
# TODO add logic to dockerfiles
import asyncio
from xbbg import blp

sys.path.append('/var/task/shared/python')
sys.path.append('/src/shared/python/')
sys.path.append(('/home/ec2-user/environment/MvpPortfolioMonitoring-code-repo/aws-quant-infra'))
sys.path.append(('/home/ec2-user/environment/MvpPortfolioMonitoring-code-repo/aws-quant-infra/src/shared/python'))
import aws_quant_infra as aq_i
import aws_quant_risk as aq_r
if True:# for debugging
    import aws_quant_infra as aq_i
    import imp
    imp.reload(aq_i) 
    import aws_quant_risk as aq_r
    imp.reload(aq_r) 

if True: # debugging
    os.environ["SSM_PREFIX"] = "Mvp"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

def check_config():
    config_env="dev"
    
    app_prefix = f"{os.environ['SSM_PREFIX']}-"
    aws_region=os.environ.get('AWS_DEFAULT_REGION',"us-east-1")
    env_config = aq_i.replace_string_dict_keys(aq_i.get_app_config_from_paramstore(aws_region),app_prefix,'')
    
    
    hosted_config_details = json.loads(env_config.get('PortfolioMonitoring-AppConfigDetails'))
    app_config_client =boto3.client('appconfig',region_name=aws_region)
    app_config_app = hosted_config_details.get('Application')
    app_config_config=hosted_config_details.get('Configuration')
    app_config = (app_config_client.get_configuration(Application=app_config_app,Environment=config_env,Configuration=app_config_config, ClientId=f'{random.randint(-sys.maxsize,sys.maxsize)}').get('Content').read())
    app_config=json.loads(app_config.decode('utf-8'))
    app_config['AWS_REGION']=aws_region
    
    return(config_env,app_config)

config_env,app_config = check_config()

def get_portfolio_inits(config_env,portf_id='JD2966'):
    # portf_id='7af1fa7c6b01edd3826c880082270775'
    if False: # debugging
        os.environ["SSM_PREFIX"] = "Mvp"
        max_symbols = 1
        config_json= '{"version":"sandbox",' \
                     '"token_secret":"iex_api_token_pk_sandbox",' \
                     '"token_secret_streaming":"iex_api_token_pk",' \
                     '"url":"https://cloud-sse.iexapis.com",' \
                     '"streaming_endpoint_equity":"stocksUSNoUTP"}'
    app_prefix = f"{os.environ['SSM_PREFIX']}-"
    aws_region=os.environ.get('AWS_DEFAULT_REGION',"us-east-2")
    env_config = aq_i.get_app_config_from_paramstore(aws_region)
    app_config_client= boto3.client('appconfig',region_name=aws_region)
    app_config_temp=app_config_client.get_configuration(Application='PortfolioMonitoring',
                                                        Environment=config_env,
                                                        Configuration='PortfolioMonitoringConfigProfile', 
                                                        ClientId=f'{random.randint(-sys.maxsize,sys.maxsize)}')
    app_config = app_config_temp.get('Content').read()
    app_config=json.loads(app_config.decode('utf-8'))
    return (env_config, app_config, app_prefix, portf_id)

env_config, app_config, app_prefix, portf_id= get_portfolio_inits(config_env)
one_port = aq_r.PortfolioTracker( app_config,env_config,app_prefix, portf_id)
#aq_r.PortfolioTracker.portfolio_tracker_main("dev",'d16af770c75df7fc23b922773cf1a450')
if True:
    one_port.portfolio['last_tracker_update']='2022-06-23 19:00:00.493000000'
one_port.load_portf_market_data()
one_port.calc_portf_priceline()
one_port.calc_portf_pnl()
one_port.save_portf_priceline()
one_port.save_portf_pnl()
