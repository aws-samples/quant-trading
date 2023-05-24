import base64
from datetime import date, datetime, timezone
import boto3
import json
import os
import time
import pandas as pd
import awswrangler as wr
from botocore.exceptions import ClientError
import sys
from dateutil import parser

def get_secret(secret_name,region_name):
    # Create a Secrets Manager client
    # get_secret_value_response={'SecretString':''}
    session = boto3.session.Session(region_name=region_name)
    print(f"1: session:{session} in region:{region_name}")
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    print(f"2: session:{session} with client:{client} in region:{region_name}")
    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )

        print(f"3: session:{session} with client:{client} in region:{region_name} response:{get_secret_value_response}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e

        raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            # decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
    data = {}
    data[secret_name] = secret
    return (data)
    # return( json.loads(get_secret_value_response['SecretString']))
def get_app_config_from_paramstore(region_name):
    ssm = boto3.client('ssm',
                       region_name=region_name)
    param_page=ssm.get_paginator('describe_parameters')
    param_names = [i.get('Name') for i in param_page.paginate().build_full_result()['Parameters'] if os.environ['SSM_PREFIX'] in i.get('Name')]
    param_vals = [ssm.get_parameter(Name=i, WithDecryption=True).get("Parameter",{}).get('Value','') for i in param_names]
    assert len(param_names)==len(param_vals), f"get_app_config_from_paramstore error: len(param_names):{len(param_names)} must be equal len(param_vals):{len(param_vals)}"
    return(dict(zip(param_names, param_vals)))
def replace_string_dict_keys(dict_l,string_from,string_to):
    #dict_l =env_config
    new_keys = [i.replace(string_from,string_to) for i in dict_l.keys()]
    return(dict(zip(new_keys,dict_l.values())))
def get_batch_jobs_by_status_name(queue_array
                          ,status_array=['SUBMITTED', 'PENDING', 'RUNNABLE', 'STARTING', 'RUNNING']
                          ,job_name_filter_array=[]):
    #queue_array=['MvpPortfolioMonitoring_q_ec2','MvpPortfolioMonitoring_q_fargate']
    batch_job_array=[]
    for one_job_q in queue_array:
        batch_client = boto3.client('batch')
        batch_jobs_resp = batch_client.list_jobs(jobQueue=one_job_q)
        batch_jobs = [i for i in batch_jobs_resp.get('jobSummaryList') if i.get('status', '') in ['SUBMITTED'
            , 'PENDING'
            , 'RUNNABLE'
            , 'STARTING'
            , 'RUNNING']]
        batch_job_array=batch_job_array+batch_jobs
    if len(job_name_filter_array)>0:
        batch_job_array = [i for i in batch_job_array if [j for j in job_name_filter_array if j in i.get('jobName')]]
    return(batch_job_array)
def try_get_catch_dict(dict_set, key):
    if isinstance(dict_set, str):
        dict_set = json.loads(dict_set)
    try:
        return dict_set.get(key)
    except:
        print(f"Key: {key} not found in given dictionary!")
        print(f"Dictionary provided: {dict_set}")
        print("Portfolio monitoring stopping")
        sys.exit(1)

# def determine_

class TimestreamAdapter(object):
    normalized_dimensions = [
        'symbol'
        , 'companyName'
        , 'primaryExchange'
        , 'openTime'
        , 'openSource'
        , 'closeTime'
        , 'closeSource'
        , 'highTime'
        , 'highSource'
        , 'lowTime'
        , 'lowSource'
        , 'latestSource'
        , 'latestTime'
        , 'latestUpdate'
        , 'currency'
    ]
    normalized_measures =  [
        'open'
        , 'close'
        , 'high'
        , 'low'
        , 'latestPrice'
        , 'latestVolume'
        , 'marketCap'
        , 'peRatio'
        , 'bid'
        , 'ask'
    ]
    # Mapping is None when default return keys map 1:1
    market_data_maps = {
        # IEX Time mapping is excluded from map, manually defined in market specific write method
        'IEX': {
            # Measures
            'open': 'open',
            'close': 'close',
            'high': 'high',
            'low': 'low',
            'latestPrice': 'latestPrice',
            'iexBidPrice': 'bid',
            'iexAskPrice': 'ask',
            'latestVolume': 'latestVolume',
            # Dimensions
            'symbol': 'symbol',
            'companyName': 'companyName',
            # TODO mapping logic for primaryExchange
            'latestTime':'latestTime', #['openTime','closeTime','highTime','lowTime','latestTime','bidTime','askTime'],
            'openSource': 'openSource',
            # closeSource is mapped in write method
            'highSource': 'highSource',
            'lowSource': 'lowSource',
            'lastSource': 'lastSource',
            'latestUpdate': 'latestUpdate',
            'bidSource': 'bidSource',
            'askSource': 'askSource',
            'currency': 'currency',
            'primaryExchange':'primaryExchange',
            'iexLastUpdated': 'time'},
        'BPIPE': {
            # Measures
            'OPEN': 'open',
            'CLOSE': 'close',
            'HIGH': 'high',
            'LOW': 'low',
            'LAST_PRICE': 'latestPrice',
            'BID': 'bid',
            'ASK': 'ask',
            'CONTINUOUS_VOLUME_RT': 'latestVolume',
            # Dimensions
            'TICKER': 'symbol',
            'NAME': 'companyName',
            # TODO mapping logic for primaryExchange
            'latestTime':'latestTime', #['openTime','closeTime','highTime','lowTime','latestTime','bidTime','askTime'],
            'EXCH_CODE_OPEN': 'openSource',
            # closeSource is mapped in write method
            'EXCH_CODE_HIGH': 'highSource',
            'EXCH_CODE_LOW': 'lowSource',
            'EXCH_CODE_LAST': 'lastSource',
            'LAST_TRADE_PRICE_TIME_TODAY_RT': 'latestUpdate',
            'EXCH_CODE_BIG': 'bidSource',
            'EXCH_CODE_ASK': 'askSource',
            'CRNCY': 'currency',
            'EQY_PRIM_EXCH_SHRT':'primaryExchange',
            'tick_time': 'time'
        } 
    }
    def __init__(self, ts_config, source, region):
        self.ts_config = ts_config
        self.source = source
        self.aws_deploy_region = region
        self.boto3_session = boto3.Session(region_name=self.aws_deploy_region)
    
    def _normalize_market_data(self, md_dict):
        # If we need dict to be 'clean' (no extra fields for wrangler to parse)
        # normalized_md_dict = {}
        # normalize_map = self.market_data_maps[self.source]
        # if normalize_map is not None:
        #     for k,v in normalize_map:
        #         if v in self.normalized_dimensions or v in self.normalized_measures:
        #             normalized_md_dict[v] = md_dict[k]
        # else:
        #     for k,v in md_dict:
        #         if k in self.normalized_dimensions or v in self.normalized_measures:
        #             normalized_md_dict[k] = v
        # normalized_md_dict['openSource'] = self.source
        # return normalized_md_dict
        # Reusing existing dict approach
        normalize_map = self.market_data_maps[self.source]
        print(f"norm map:{normalize_map} \n")
        if normalize_map is not None:
            for k,v in normalize_map.items():
                if isinstance(v, list):
                    for field in v:
                        md_dict[v] = md_dict.get(k, datetime.now()) if field != 'latestTime' else md_dict.get(k, None)   
                md_dict[v] = md_dict.get(k, None)     
        md_dict['openSource'] = self.source
        if type(md_dict) is dict:
            # the rest of the flow expect list => convert to list if it is dict (happens when there is only single row update from MD provider)
            md_dict=[md_dict]
        return md_dict

    def write_iex_data(self, data_stream, buffer_size):
        dfs=[]
        for msg in data_stream:
            msg_dict = json.loads(msg.data)
            print(f"Writing symbols: {[i['symbol'] for i in msg_dict]} \n")
            if len(msg_dict) > 0:
                # Get market data in normalized format...
                normalized_md_dict = self._normalize_market_data(msg_dict[0])
                print(f"normalized_md_dict len: {len(normalized_md_dict)} \n normalized_md_dict content: {normalized_md_dict} \n")
                df = pd.DataFrame(normalized_md_dict)
                record_time_str =df.get('iexLastUpdated','lastTradeTime').values[0]
                if record_time_str==None:
                    record_time_str = df.get('lastTradeTime').values[0]
                print(f"{df[['iexLastUpdated','lastTradeTime']]} {record_time_str}")
                record_time = datetime.fromtimestamp(record_time_str/1000)
                df["time"] = record_time
                df = df.fillna(0)
                dfs = dfs + [df]
                if len(dfs) > buffer_size:
                    write_df = pd.concat(dfs)
                    self._write_to_timestream(write_df)
                    dfs = []
            else:
                print("empty message", msg)
    
    def write_bpipe_data(self, market_view_pd):
        print(f"Writing symbols: {market_view_pd['TICKER'].drop_duplicates().values}")
        write_pd = market_view_pd.rename(columns=self.market_data_maps.get('BPIPE')).copy(deep=True)
        #write_pd.to_csv('~/environment/write_pd.csv')
        #dfs=[]
        #for one_symbol in market_view.keys():
        #    print(f"symbol: {one_symbol} \n, market_view {market_view.get(one_symbol)} \n")
        #    normalized_md_dict = self._normalize_market_data(market_view.get(one_symbol))
        #    print(f"normalized mv: {one_symbol} \n, normalized_md_dict: {normalized_md_dict} \n")
        #    df = pd.DataFrame([normalized_md_dict])
        #    df = df.fillna(0)
        #    dfs = dfs + [df]
        #write_df = pd.concat(dfs)
        #print(f"len of DF:{len(dfs)}")
        self._write_to_timestream(write_pd)
        
    # Remove None values from df before calling this method
    def _write_to_timestream(self,md_df,time_col = 'time'):
        ts_session = boto3.Session(region_name='us-east-1')
        if False:
            #for debugging
            print(f'DEBUG: cols:{md_df.columns}')
            md_df.to_csv('md_df.csv')
            md_df[time_col]= md_df[time_col].apply(parser.parse) 
        start_time = md_df[time_col].min()
        end_time =md_df[time_col].max()
        for m in self.normalized_measures:
            md_df[m] = pd.to_numeric(md_df[m], downcast="float")
            #md_df[m] =md_df[m].astype(str)
            #print(f'writing measure: {m} , data: {md_df[m]},database={self.ts_config.get("db_name")},table={self.ts_config.get("table_name")},dims={self.normalized_dimensions}')
            if (md_df[m].count()>0):  
                try:
                    min_val=md_df[m].min()
                    max_val=md_df[m].max()
                    rr = wr.timestream.write(
                        df=md_df,
                        database=self.ts_config.get('db_name'),
                        table=self.ts_config.get('table_name'),
                        time_col=time_col,
                        measure_col=m,
                        dimensions_cols=self.normalized_dimensions,
                        boto3_session=self.boto3_session
                    )
                    if len(rr) > 0:
                        rr_pd = pd.DataFrame(rr)
                        reasons = rr_pd.groupby('Reason').count()
                        print(f"Rejected, measure ({m}):\n{reasons}\ncontent:{md_df[[m]+[time_col]]}\n")
                    else:
                        print(f"Measure:{m}, records:{len(md_df)}, min_val:{min_val}, max_val:{max_val} timeframe {start_time}:{end_time}")
                except Exception as _exc:
                    print(f"Exc:{_exc}\n writing to TS, measure:{m}, min_val:{min_val}, max_val:{max_val} timeframe {start_time}:{end_time} total: {len(md_df)}")
               

    # Without using awswrangler
    # def write_to_timestream(self, data_stream, buffer_size):
    #     record_buffer = []
    #     rec_count = 0
    #     for msg in data_stream:
    #         msg_dict = json.loads(msg.data)
    #         print(f"Writing symbols: {[i['symbol'] for i in msg_dict]}")
    #         if len(msg_dict) > 0:
    #             # If there is a list of prefixes to remove from md, remove them
    #             if self.prefix is not None:
    #                 msg_dict = self._clean_market_data(msg_dict)
    #             dim_dict = [{'Name': i, 'Value': str(msg_dict[0][i])} for i in self.dimensions]
    #             record_time = str(msg_dict[0][self.time_f])
    #             records = [{
    #                             'Dimensions': dim_dict,
    #                             'MeasureName': str(i),
    #                             'MeasureValue': str(msg_dict[0].get(i, 0)),
    #                             'Time': record_time,
    #                             'TimeUnit': 'MILLISECONDS'
    #                         } if (msg_dict[0].get(i, 0)) is not None else {
    #                 'Dimensions': dim_dict,
    #                 'MeasureName': str(i),
    #                 'MeasureValue': str('0'),
    #                 'Time': record_time,
    #                 'TimeUnit': 'MILLISECONDS'
    #             }
    #                         for i in self.measures]
    #             record_buffer = record_buffer + records
    #             rec_count += 1
    #             print(
    #                 f"Records: {list(set([i['Dimensions'][0]['Value'] for i in records if i['Dimensions'] [0]['Name'] == 'symbol']))}"
    #             )
    #             if rec_count == buffer_size:
    #                 self.write_records_to_timestream(record_buffer=record_buffer)
    #                 rec_count = 0
    #                 record_buffer = []
    #         else:
    #             print("empty message", msg)

    # def write_records_to_timestream(self, record_buffer):
    #     start_time = time.strftime("%d-%b-%Y %H:%M:%S %Z", time.localtime(
    #         int(min([i.get("Time", 0) for i in record_buffer])) / 1000))
    #     end_time = time.strftime("%d-%b-%Y %H:%M:%S %Z", time.localtime(
    #         int(max([i.get("Time", 0) for i in record_buffer])) / 1000))
    #     try:
    #         self.ts_config.get('ts_write_client',boto3.client('timestream-write')).write_records(
    #             DatabaseName=self.ts_config.get('db_name','AWsomeBuilder_east2'),
    #             TableName=self.ts_config.get('table_name','iex_realtime_data'),
    #             Records=record_buffer
    #         )
    #         print(f'accepted:{len(record_buffer)} records from {start_time} to {end_time}')
    #     except self.ts_config.get('ts_write_client',boto3.client('timestream-write')).exceptions.RejectedRecordsException as err:
    #         print(f'exception {err} for {len(record_buffer)} records from {start_time} to {end_time}')
    #         for rr in err.response["RejectedRecords"]:
    #             print("Rejected Index " + str(rr["RecordIndex"]) + ": " + rr["Reason"])

    #     except Exception as excp:
    #         print("Error:", excp)