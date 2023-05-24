import ast
import boto3
from decimal import *
import time
from dateutil.parser import isoparse
import hashlib
prtf_name='long_short'
session = boto3.session.Session(profile_name='quant')
dynamodb = session.resource('dynamodb', region_name='us-west-2')
portf_table = dynamodb.Table('MvpPortfolioMonitoringPortfolioTable')
create_ts = int(time.time() * 1000000)
portf_id = hashlib.md5((f'{prtf_name}{create_ts}').encode()).hexdigest()

#load portfolio list from file sp500.txt
with open('aws-quant-infra/scripts/sp500.txt') as list_file:
    portfolio_list = ast.literal_eval(list_file.read())

portf_item_positions = {'positions': []}
for item in portfolio_list:
    position = {item: Decimal(0.25)}
    portf_item_positions['positions'].append(position)
    
    
portf_item = {
    'portf_id': portf_id, 
    'portf_name': prtf_name,
    'portf_create_ts': create_ts,
    # 'positions': [{'GS': Decimal(-1)}, {'AMZN': Decimal(0.25)}, {'MSFT': Decimal(0.25)}, {'XLE': Decimal(0.25)},
    #                 {'QQQ': Decimal(0.25)}]
    
    # load positions from dict above
    'positions': portf_item_positions['positions']
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