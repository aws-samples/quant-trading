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
#from xbbg import blp

sys.path.append('/var/task/shared/python')
sys.path.append('/src/shared/python/')
sys.path.append(('/home/ec2-user/environment/AWSQuant/aws-quant-infra'))
sys.path.append(('/home/ec2-user/environment/AWSQuant/aws-quant-infra/src/shared/python'))
import aws_quant_infra as aq_i
import aws_quant_market_data as aq_md
import aws_quant_risk as aq_r
if True:# for debugging
    import aws_quant_infra as aq_i
    import imp
    imp.reload(aq_i) 
    import aws_quant_market_data as aq_md
    imp.reload(aq_md) 

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

def get_data_provider_inits(config_env,symbols):
        if False: # debugging
            os.environ["SSM_PREFIX"] = "Mvp"
            os.environ["AWS_REGION"] = "us-east-1" #TODO: move into separate debug settings and use MODE (deploy/local...) in code
        app_prefix = f"{os.environ['SSM_PREFIX']}-"
        aws_region=os.environ.get('AWS_DEFAULT_REGION',"us-east-1")
        env_config = aq_i.replace_string_dict_keys(aq_i.get_app_config_from_paramstore(aws_region),app_prefix,'')
        hosted_config_details = json.loads(env_config.get('PortfolioMonitoring-AppConfigDetails'))
        app_config = (boto3.client('appconfig',region_name=aws_region).\
            get_configuration(Application=hosted_config_details.get('Application')
                              ,Environment=config_env
                              ,Configuration=hosted_config_details.get('Configuration')
                              , ClientId=f'{random.randint(-sys.maxsize,sys.maxsize)}'
                              #,ClientConfigurationVersion=hosted_config_details.get(config_env)
                              ).get('Content').read())
        app_config=json.loads(app_config.decode('utf-8'))
        app_config['AWS_REGION']=aws_region
        if type(symbols) == str:
            symbol_list = symbols.split(',')
        else:
            symbol_list = symbols
        print(f"working with: {symbol_list}\n\n")
        print(f"app_prefix: {app_prefix}\n\n")
        print(f"aws_region: {aws_region}\n\n")
        print(f"hosted_config_details: {hosted_config_details}\n\n")
        print(f"APP CONFIG: {app_config}\n\n")
        print(f"ENV CONFIG: {env_config}\n\n")
        
        return (env_config, app_config, app_prefix, symbol_list)


symbols = ['DELL']#EURUSD BGN Curncy['SPY']#,'GS','AMZN'][{'GS': Decimal('-1')}, {'AMZN': Decimal('0.24')}, {'MSFT': Decimal('0.26')}, {'XLE': Decimal('0.25')}, {'QQQ': Decimal('0.25')}]
env_config, app_config, app_prefix, symbol_list= get_data_provider_inits(config_env,symbols)
mv=aq_md.MarketDataProvider.subscribe_main(config_env,symbols,10)