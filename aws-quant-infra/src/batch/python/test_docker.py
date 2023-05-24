import pyEX
print("import pyEX:",pyEX.__file__)
import binance
print("import pyEX:",binance.__file__)
import sys
print("sys.path:",'\n'.join(sys.path))
import boto3
import os
import json
import random
#TODO: check code committ stack; it wiped out existing repo when deployed [potentially rolled back] into non-greenfield account
if (True):
    try:
        sys.path.append('/src/shared/python')
        import aws_quant_infra as aq_i
        print(f"import aws_quant_infra is done!")
        print(aq_i.__file__)
        import aws_quant_risk as aq_r
        print(f"import aws_quant_risk is done!")
        print(aq_r.__file__)
    except Exception as exc:
        print(f'error importing:{exc}')
else:
    pass


REGION = os.environ['AWS_DEFAULT_REGION']
print(f'aws region: {REGION}')

def boto3_test():
    print('Starting tests to check various boto3 calls')
    env, app = aqi_test()
    aqr_test(env, app)

def aqi_test():
    print('Testing aws_quant_infra.get_app_config_from_paramstore')
    env_config = aq_i.get_app_config_from_paramstore(REGION)
    print(env_config)

    print('Testing appconfig call')
    env = 'dev'
    app_config_details = json.loads(env_config.get('Mvp-PortfolioMonitoring-AppConfigDetails'))
    app = app_config_details.get('Application')
    config = app_config_details.get('Configuration')
    app_config = (boto3.client('appconfig').\
            get_configuration(Application=app
                              ,Environment=env
                              ,Configuration=config
                              , ClientId=f'{random.randint(-sys.maxsize,sys.maxsize)}').get('Content').read())

    app_config=json.loads(app_config.decode('utf-8'))
    print(app_config)

    print('Testing aws_quant_infra.get_secret')
    secret_name = app_config.get('secrets')[0]
    # secret = f'MvpPortfolioMonitoring-{secret_name}'
    secret = f'{secret_name}'
    secret_data = aq_i.get_secret(secret, REGION)
    print(secret_data)
    try:
        print('Testing format of response')
        print(secret_data[secret])
    except:
        print('get_secret response in wrong format!!!')

    return env_config, app_config

def aqr_test(env_config, app_config):
    print('Testing Batch call')
    batch_client = boto3.client('batch')
    batch_jobs_resp = batch_client.list_jobs(jobQueue='MvpPortfolioMonitoring_q_ec2')
    print(batch_jobs_resp)

    print('Testing aws_quant_risk.PortfolioTrackerFactory')
    PTF = aq_r.PortfolioTrackerFactory(env_config, app_config, 'Mvp-')
    print(str(PTF))

    print('Testing aq_r.PTF.get_all_portfolios (Dynamodb call)')
    PTF.load_all_portfolios()
    print(PTF.all_portfolios)

    print('Testing Events calls')
    for rule_name in [ 'trading_EOD', 'trading_SOD']:
        print(f'Checking call for rule name: {rule_name}')
        print(boto3.client('events').list_targets_by_rule(Rule=rule_name))

    print('Testing timestream call')
    timestream_db = env_config.get('Mvp-PortfolioMonitoring-TimestreamDb')
    timestream_table = 'iex_realtime_data'
    print('Checking for query endpoints')
    query = f'SELECT * FROM {timestream_db}.{timestream_table} LIMIT 10'
    print(boto3.client('timestream-query').query(
        QueryString=query,
    ))
    print('Checking for write endpoints')
    print(boto3.client('timestream-write').describe_database(
        DatabaseName=timestream_db
    ))

boto3_test()