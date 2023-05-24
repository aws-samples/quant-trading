import json
import os
import sys
import boto3
from decimal import *
import requests
import time
import random
import hashlib

import pandas as pd
sys.path.append('/var/task/shared/python') #TODO: not a fan of hardcoded PATHS
sys.path.append('/home/ec2-user/environment/AWSQuant/aws-quant-infra/src/shared/python') #TODO: not a fan of hardcoded PATHS
import aws_quant_infra as aq_i
import aws_quant_risk as aq_r
# print(f"import aws_quant_risk is done!")
# print(aq_r.__file__)
REGION=os.environ.get('AWS_DEFAULT_REGION')
dynamodb = boto3.resource('dynamodb', region_name=REGION)
ssm_client = boto3.client("ssm", region_name=REGION)

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
    app_config_client = boto3.client('appconfig',region_name=aws_region)
    app_config_app = hosted_config_details.get('Application')
    app_config_config=hosted_config_details.get('Configuration')
    app_config = (app_config_client.get_configuration(Application=app_config_app,Environment=config_env,Configuration=app_config_config, ClientId=f'{random.randint(-sys.maxsize,sys.maxsize)}').get('Content').read())
    app_config=json.loads(app_config.decode('utf-8'))
    app_config['AWS_REGION']=aws_region
    return(config_env,app_config)

config_env,app_config = check_config()

def get_secret():
    secret_name = app_config.get('secrets')[0]
    secret = f'{secret_name}'
    secret_data = aq_i.get_secret(secret, REGION)
    print(secret_data)
    try:
        print('Testing format of response')
        print(secret_data[secret])
    except:
        print('get_secret response in wrong format!!!')
    
    return secret_data[secret]
    
SECRET_DATA = get_secret()


def get_sp_symbols():
    # Returns list of current S&P 500 companies
    
    table=pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    df = table[0]
    symbols = df["Symbol"]
    
    return symbols
    
        
def get_latest_updates(symbols):
    attributes = ['iexOpen', 'latestPrice']
    table = []
    iexOpen, latestPrice = 0, 0
    
    for i in symbols:
        ticker = i
        api_url = f'https://cloud.iexapis.com/stable/stock/{ticker}/quote?token={SECRET_DATA}'
        df = requests.get(api_url).json()
        iexOpen = df[attributes[0]]
        latestPrice = df[attributes[1]]
        
        if iexOpen is None:
            iexOpen = 0
        if latestPrice is None:
            latestPrice = 0
            
        table.append([i, iexOpen, latestPrice])

    return table
    

def calculate_diff(symbols):
    diff_table = [Decimal(str(i[2])) - Decimal(str(i[1])) for i in symbols]
    return diff_table
    
def calculate_weights(diff_table):
    neg_count = len(list(filter(lambda x: (x < 0), diff_table)))
    pos_count = len(diff_table) - neg_count
    neg_weight = "{:.3f}".format(-1/neg_count) if neg_count != 0 else -1
    pos_weight = "{:.3f}".format(1/pos_count) if pos_count != 0 else 1
    
    weights_table = list(map(lambda x: Decimal(neg_weight) if x < 0 else Decimal(pos_weight), diff_table))
    return weights_table

    
    
def get_final_payload(weights, symbols):
    table_len = len(weights)
    return [{symbols[i][0]: weights[i]} for i in range(table_len)]
    
def add_parameter(value, name, purpose):
    param_name = '/Mvp-PortfolioMonitoring-IntradayMomentum' + name
    new_string_parameter = ssm_client.put_parameter(
        Name=param_name,
        Description='Portfolio ' + purpose + ' of intraday momentum table',
        Value=value,
        Type='String',
        Overwrite=True,
        Tier='Standard',
        DataType='text'
    )
    
    return new_string_parameter



def lambda_handler(event, context):
    #event['AWS_REGION']=os.environ['AWS_REGION']
    # all_symbols,delta_symbols,delta_symbols_stripes,jobs,portf_batch= \
    #     aq_r.PortfolioTrackerFactory.handle_portfolio_update(event)
    # print(f'submitted jobs:{[response["jobName"] for response in jobs]} for {delta_symbols} '
    #       f'out of: {all_symbols} in batches:{delta_symbols_stripes}')
    # print(f'submitted portfolios:{[response["jobName"] for response in portf_batch]}')
    
    symbols = get_sp_symbols()
    updates = get_latest_updates(symbols)
    diffs = calculate_diff(updates)
    weights = calculate_weights(diffs)
    final_payload = get_final_payload(weights, updates)
    print("Event: ", event)
    print("Context: ", context)
    print("Final payload: ", final_payload)

        
    prtf_name='long_short'

    portf_table = dynamodb.Table('MvpPortfolioMonitoringPortfolioTable')
    create_ts = int(time.time() * 1000000)
    portf_id = hashlib.md5((f'{prtf_name}{create_ts}').encode()).hexdigest()
    add_parameter(portf_id, "PortfID", "ID")
    add_parameter(str(create_ts), "PortfCreateTS", "time stamp")
    portf_item = {
        'portf_id': portf_id
        , 'portf_name': prtf_name
        , 'portf_create_ts': create_ts
        ,
        'positions': final_payload
        , 'handler_info': {'deploy': 'batch', 'refresh_sec': 60,'app_config_dict':{
            'Application':'PortfolioMonitoring'
            ,'Environment':'dev'#config_env
            ,'Configuration':'PortfolioMonitoringConfigProfile'
        }}
    }
    portf_table.put_item(
        TableName='MvpPortfolioMonitoringPortfolioTable',
        Item=portf_item
    )