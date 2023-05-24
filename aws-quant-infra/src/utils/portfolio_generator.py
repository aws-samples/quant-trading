import csv
import argparse
import json
from hashlib import md5
import random
import numpy as np
import json
import boto3
import datetime
import time
import random
import sys
import os

from decimal import *

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
import aws_quant_market_data as aq_md
import aws_quant_risk as aq_r

parser = argparse.ArgumentParser(description="Portfolio generator")
parser.add_argument('--name', required=True)
parser.add_argument('--filename', required=True)
parser.add_argument('--ticker-amount', default=50, required=False, type=int)
parser.add_argument('--random-order', default=False, required=False, type=bool)
args = parser.parse_args()


def write_portfolio(name, data, weights, ticker_amount, random_order):
    portfolio = dict()
    portfolio['portf_id'] = md5(name.encode('utf-8')).hexdigest()
    portfolio['portf_create_ts'] = int(datetime.datetime.now().timestamp()*1000)
    portfolio['positions'] = []
    portfolio['portf_name'] = name
    portfolio['handler_info'] = {
        "refresh_sec": "60",
        "deploy": "batch",
    }
    portfolio["app_config_dict"] = {
        "Configuration": "PortfolioMonitoringConfigProfile",
        "Application": "PortfolioMonitoring",
        "Environment": "dev"
    }
    
    tickers = []

    if random_order is False and ticker_amount <= len(data):
        tickers = data[:ticker_amount]
    elif ticker_amount <= len(data):
        for i in range(ticker_amount):
            rnx = random.randrange(len(data) -1)
            tickers.append(data[rnx])

    for tick in tickers:
        mapper = dict()
        mapper[f'{tick} US Equity'] = (weights.pop())
        portfolio['positions'].append(mapper)

    #with open(f'portfolio-{name}.json', 'w') as f:
    #    f.write(json.dumps(portfolio))
        
    return(portfolio)

def main():
    list_tickers = []

    try:
        with open(args.filename, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                list_tickers.append(row[0])
    except Exception as e:
        print(e)

    weights = np.random.dirichlet(np.ones(args.ticker_amount), size=1)
    weights = [Rounded(round(i,4)) for i in list(weights.flatten())]

    ptf=write_portfolio(args.name, list_tickers, weights, args.ticker_amount, True)
    aq_r.PortfolioTrackerTester.test_harness(ptf=ptf)
    


if __name__ == '__main__':
    main()
