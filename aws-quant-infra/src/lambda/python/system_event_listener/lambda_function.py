import json
import os
import sys

sys.path.append('/var/task/shared/python')
sys.path.append('/home/ec2-user/environment/AWSQuant/aws-quant-infra/src/shared/python')
import aws_quant_risk as aq_r
print(f"import aws_quant_risk is done!")
print(aq_r.__file__)

def lambda_handler(event, context):
    res=aq_r.PortfolioTrackerFactory.handle_system_event(event)
    print(f'{event} result:{res}')
    return {
            'statusCode': 200,
            'body': json.dumps(f'{event} result:{res}')
        }
