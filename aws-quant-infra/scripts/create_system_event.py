import json
import boto3
from decimal import *
import time
from dateutil.parser import isoparse
import sys
import hashlib
import random
 # event_name='intraday_start_all'
#   #  'intraday_start_all','intraday_stop','intraday_stop_all'
events = ['intraday_start_all','intraday_stop','intraday_stop_all']
session = boto3.session.Session(profile_name='quant')
dynamodb = session.resource('dynamodb', region_name='us-west-2')

aws_region='us-west-2'
# app_config = (boto3.client('appconfig',region_name=aws_region). \
#                 get_configuration(Application='PortfolioMonitoring'
#                                 # ,Environment=config_env
#                                 ,Configuration='PortfolioMonitoringConfigProfile'
#                                 , ClientId=f'{random.randint(-sys.maxsize,sys.maxsize)}').get('Content').read())
# app_config=json.loads(app_config.decode('utf-8'))
portf_system_table = dynamodb.Table('MvpPortfolioMonitoringSystemEventTable')
for event_name in events:
    create_ts = int(time.time() * 1000000)
    event_id = hashlib.md5((f'{event_name}{create_ts}').encode()).hexdigest()
    event_item = {
        'event_id': event_id
        , 'event_create_ts': create_ts
        , 'event_name': event_name
        , 'commands': [{'batch': [{'c4fa6bae-6e6b-4618-af75-a7f967a12cc0': 'stop'}]}]
        , 'config': {'stale_threshold': '1m', 'symbol_stripe_size': '1'}
        , 'handler_info': {'app_config_dict':{'Configuration': 'PortfolioMonitoringConfigProfile',
                            'Environment': 'dev',
                            'Application': 'PortfolioMonitoring'}}
    }
    portf_system_table.put_item(
        TableName='MvpPortfolioMonitoringSystemEventTable',
        Item=event_item
    )
