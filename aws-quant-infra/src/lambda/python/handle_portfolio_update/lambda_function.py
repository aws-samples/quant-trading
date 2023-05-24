import json
import os
import sys

sys.path.append('/var/task/shared/python') #TODO: not a fan of hardcoded PATHS
sys.path.append('/home/ec2-user/environment/AWSQuant/aws-quant-infra/src/shared/python') #TODO: not a fan of hardcoded PATHS
import aws_quant_risk as aq_r
print(f"import aws_quant_risk is done!")
print(aq_r.__file__)

def lambda_handler(event, context):
    #event['AWS_REGION']=os.environ['AWS_REGION']
    all_symbols,delta_symbols,delta_symbols_stripes,jobs,portf_batch= \
        aq_r.PortfolioTrackerFactory.handle_portfolio_update(event)
    print(f'submitted jobs:{[response["jobName"] for response in jobs]} for {delta_symbols} '
          f'out of: {all_symbols} in batches:{delta_symbols_stripes}')
    print(f'submitted portfolios:{[response["jobName"] for response in portf_batch]}')
    return {
            'statusCode': 200,
            'body': json.dumps(f'submitted jobs:{[response["jobName"] for response in jobs]} for {delta_symbols} out of: {all_symbols} in batches:{delta_symbols_stripes}')
        }
