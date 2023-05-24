import json
import os
import sys
import boto3


sys.path.append('/var/task/shared/python') #TODO: not a fan of hardcoded PATHS
sys.path.append('/home/ec2-user/environment/AWSQuant/aws-quant-infra/src/shared/python') #TODO: not a fan of hardcoded PATHS
import aws_quant_risk as aq_r
print(f"import aws_quant_risk is done!")
print(aq_r.__file__)

REGION=os.environ.get('AWS_DEFAULT_REGION')
dynamodb = boto3.resource('dynamodb', region_name=REGION)
ssm_client = boto3.client("ssm", region_name=REGION)

def lambda_handler(event, context):
    portf_table = dynamodb.Table('MvpPortfolioMonitoringPortfolioTable')
    get_portf_id_response = ssm_client.get_parameter(Name='/Mvp-PortfolioMonitoring-IntradayMomentumPortfID')
    portf_id = get_portf_id_response['Parameter']['Value']
    
    get_portf_create_ts_response = ssm_client.get_parameter(Name='/Mvp-PortfolioMonitoring-IntradayMomentumPortfCreateTS')
    portf_create_ts = int(get_portf_create_ts_response['Parameter']['Value'])
    print("TS: ", portf_create_ts)

    response = portf_table.delete_item(
        Key={
            'portf_id': portf_id,
            'portf_create_ts': portf_create_ts
        }
    )
    
    status_code = response['ResponseMetadata']['HTTPStatusCode']
    print(status_code)
    