import json
import os
import sys
import boto3
import random
import urllib.request
# AWS lambda expects all the code to be in /var/task/ directory. for this project dir is below (shared/python has custom code)
# sh-4.2# ls -la /var/task/
# total 40
# drwxr-xr-x 1 root root 4096 Aug 19 23:47 .
# drwxr-xr-x 1 root root 4096 Aug 19 23:46 ..
# drwxrwxr-x 2 root root 4096 Aug 19 23:12 handle_portfolio_update
# -rw-r--r-- 1 root root    0 Aug 19 23:12 __init__.py
# drwxrwxr-x 2 root root 4096 Aug 19 23:12 schedule_listener
# drwxr-xr-x 1 root root 4096 Aug 19 23:47 shared
# drwxrwxr-x 2 root root 4096 Aug 19 23:12 system_event_listener
# drwxrwxr-x 2 root root 4096 Aug 19 23:12 test_custom_layer
if (True):
    try:
        sys.path.append('/var/task/shared/python')
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

REGION = os.environ['AWS_REGION']
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
    version = app_config_details.get(env)
    print(f'App: {app} Config: {config} Version: {version}')
    app_config = (boto3.client('appconfig'). \
                      get_configuration(Application=app
                                        ,Environment=env
                                        ,Configuration=config
                                        , ClientId=f'{random.randint(-sys.maxsize,sys.maxsize)}'
                                        ,ClientConfigurationVersion=version
                                        ).get('Content').read())
    # app_config = urllib.request.urlopen(
    #     f'http://localhost:2772/applications/{app}/environments/{env}/configurations/{config}'
    # ).read()

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


def lambda_handler(event, context):
    # TODO implement
    dirs = ['/var/task/', '/var/task/shared', '/var/task/shared/python']
    for one_dir in dirs:
        try:
            print(f"dir list {one_dir}:", os.listdir(one_dir),"\n")
        except:
            print(f"NO dir: {one_dir}","\n")
    print("PYTHONPATH:", os.environ.get('PYTHONPATH'),"\n")
    print("PATH:", os.environ.get('PATH'),"\n")
    print("LD_LIBRARY_PATH:", os.environ.get('LD_LIBRARY_PATH'),"\n")
    print("sys.path:", sys.path,"\n")
    print("incoming event:", event,"\n")

    boto3_test()

    return {
            'statusCode': 200,
            'body': json.dumps('Hello from Lambda!')
        }
