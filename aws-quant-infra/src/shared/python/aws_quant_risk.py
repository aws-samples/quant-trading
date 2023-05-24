import os
import json
import datetime
import boto3
import pandas as pd
from boto3.dynamodb.conditions import Key
from decimal import *
import time
from dateutil.parser import isoparse
import sys
import hashlib
import random
import pytz
import platform

sys.path.append('/var/task/shared/python')
sys.path.append('/src/shared/python/')
sys.path.append('aws-quant-infra/src/shared/python/')
import aws_quant_infra as aqi
if False:# for debugging
    import src.shared.python.aws_quant_infra as aqi
    import imp
    imp.reload(aqi)

class PortfolioTrackerFactory():
    def __init__(self, env_config,app_config,app_prefix):
        if False: # debugging info
            config_json='{"Mvp-version":"sandbox","Mvp-token_secret":"iex_api_token_pk_sandbox" \
                 ,"Mvp-token_secret_streaming":"iex_api_token_pk" \
                 ,"Mvp-url":"https://cloud-sse.iexapis.com","Mvp-streaming_endpoint_equity":"stocksUSNoUTP"}'
        config_dict_app = app_config
        config_dict_env=aqi.replace_string_dict_keys(env_config,app_prefix,'')
        self.config_dict_app = config_dict_app
        self.config_dict_env = config_dict_env
        self.app_prefix = app_prefix
        self.aws_deploy_region = boto3.session.Session().region_name
        self.portfolio_table = self.config_dict_env.get('PortfolioMonitoring-PortfoliosTable')
        self.market_data_db = self.config_dict_env.get('PortfolioMonitoring-TimestreamDb')
        self.batch_queue = self.config_dict_env.get('PortfolioMonitoring-BatchEc2JobQueueName')
        self.batch_job_definition_market_data = self.config_dict_env.get('PortfolioMonitoring-BatchGetMarketDataJobDef')
        self.batch_command_get_market_data = self.config_dict_app.get('market_data').get('default_handler').get('deploy').get('cmd')
        self.stale_threshold = self.config_dict_app.get('market_data').get('default_handler').get('stale_threshold')
        self.symbol_stripe_size = self.config_dict_app.get('market_data').get('default_handler').get('symbol_stripe_size')
        self.default_md_throttle = 10
    def load_unique_portfolio_symbols(self):
        all_positions = [i['positions'] for i in self.all_portfolios['Items']]
        self.md_throttle =  int(min([i['handler_info'].get('refresh_sec',self.default_md_throttle) for i in self.all_portfolios['Items']]))
        all_symbols = []
        for one_port_pos in all_positions:
            all_symbols = all_symbols + [list(i.keys())[0] for i in one_port_pos]
        self.all_symbols = list(set(all_symbols))
    def load_all_portfolios(self):
        dynamodb = boto3.resource('dynamodb') #TODO: move to constructor?
        dynamodb_table = dynamodb.Table(self.portfolio_table )  # TODO: get from parameter store and move to contructor
        self.all_portfolios  = dynamodb_table.scan()
    def load_symbols_without_market_data(self):
        sql_template = "select distinct symbol from (" \
                       "SELECT symbol,count(*) total_c,min(time) start_time" \
                       f",(current_timestamp-max(time)),(current_timestamp-max(time)) < {self.stale_threshold} is_fresh,max(time) end_time " \
                       f"FROM {self.market_data_db}.iex_realtime_data group by symbol) t " \
                       "where is_fresh and symbol  in ('%s') order by symbol"  # TODO: get database name and table name from parameter store
        prep_query = sql_template % "','".join(self.all_symbols)
        try:
            query_res = boto3.client('timestream-query').query(QueryString=prep_query)
            cols = [i['Name'] for i in query_res['ColumnInfo']]
            existing_symbols = pd.DataFrame([
                [j['ScalarValue'] for j in i['Data']]
                for i in query_res['Rows']]
                , columns=cols)['symbol'].tolist()
            symbols_without_market_data = [i for i in self.all_symbols if i not in existing_symbols]
        except:
            symbols_without_market_data=self.all_symbols
        self.delta_symbols=symbols_without_market_data
    def create_market_data_stripes(self):
        batch_size = int(self.symbol_stripe_size )
        stripes = []
        one_stripe = []
        for i in self.delta_symbols:
            one_stripe = one_stripe + [i]
            if len(one_stripe) >= batch_size:
                stripes = stripes + [one_stripe]
                one_stripe = []
        if len(one_stripe) > 0:
            stripes = stripes + [one_stripe]
        self.symbol_stripes=stripes
    def create_market_data_subscription(self,one_batch):
        # one_batch=["GS","AMZN",'XLF','XLE','XLC']
        batch_client = boto3.client('batch') #TODO: instance var at constructor?
        #job_name = f'md_sub_{datetime.datetime.fromtimestamp(current_time).strftime("%Y%m%d_%H%M%S")}'
        job_name = f'md_sub_{hashlib.md5((f"{one_batch}").encode()).hexdigest()}'
        command_tickers = ",".join(one_batch)
        response = batch_client.submit_job(
            jobName=job_name,
            jobQueue=self.batch_queue,
            jobDefinition=self.batch_job_definition_market_data,
            containerOverrides={
                'command': [self.batch_command_get_market_data ,f"{self.config_dict_app.get('env')}" ,f"{command_tickers}", f"{self.md_throttle}"]
                # needed: ["/src/subscribe_iex_data.py","dev","AMZN,GS","10"]
            },
            timeout={
                'attemptDurationSeconds': 60 * 60 * 24 * 7
            },
        )
        return (response)
    def subscribe_market_data(self):
        self.load_all_portfolios()
        self.load_unique_portfolio_symbols()
        self.load_symbols_without_market_data()
        self.create_market_data_stripes()
        jobs = []
        for one_batch in self.symbol_stripes:
            job = self.create_market_data_subscription(one_batch)
            jobs = jobs + [job]
        print(
            f'submitted jobs:{[response["jobName"] for response in jobs]} for {self.delta_symbols} out of: {self.all_symbols} in batches:{self.symbol_stripes}')
        return (self.all_symbols, self.delta_symbols, self.symbol_stripes, jobs)
    @staticmethod
    def get_handlerconfig_from_event_cloudwatch(event):
        event_type = event.get('detail').get('event_type')
        handler_info = event.get('detail').get('handler')
        handler_app_config = handler_info
        return(event_type,handler_app_config)
    @staticmethod
    def get_handlerconfig_from_event_dynamodb(event):
        event_type = [i['eventName'] for i in event['Records']][0]
        handler_info = [i.get('dynamodb',{}).
                            get('NewImage',{}).
                            get('handler_info',{}).
                            get('M',{}) for i in event['Records']][0]
        handler_app_config = {}
        config_params = ['Configuration','Environment','Application']
        for one_param in config_params:
            handler_app_config[one_param]=handler_info.get('app_config_dict',{}).get('M',{}).get(one_param,{}).get('S',{})
        return(event_type,handler_app_config)
    @staticmethod
    def get_env_app_config(handler_app_config):
        aws_region=os.environ.get('AWS_DEFAULT_REGION',"us-east-2")
        env_config = aqi.get_app_config_from_paramstore(aws_region)
        app_config = (boto3.client('appconfig'). \
                      get_configuration(Application=handler_app_config.get('Application')
                                        ,Environment=handler_app_config.get('Environment')
                                        ,Configuration=handler_app_config.get('Configuration')
                                        , ClientId=f'{random.randint(-sys.maxsize,sys.maxsize)}').get('Content').read())
        app_config=json.loads(app_config.decode('utf-8'))
        return(env_config,app_config)
    @staticmethod
    def handle_portfolio_update(portfolio_update_event):
        print(f"received portfolio update event:{portfolio_update_event}")
        event_type,handler_app_config=PortfolioTrackerFactory.get_handlerconfig_from_event_dynamodb(portfolio_update_event)
        if False: # debugging
            os.environ["SSM_PREFIX"] = "Mvp"
            os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        app_prefix = f'{os.environ["SSM_PREFIX"]}-'
        env_config,app_config=PortfolioTrackerFactory.get_env_app_config(handler_app_config)
        print(f"working with app_prefix:{app_prefix} \n\n,env_config:{env_config}\n\n,app_config:{app_config}\n\n")
        ####port_tracker= PortfolioTracker(env_config,app_config,app_prefix)
        all_symbols, delta_symbols, delta_symbols_stripes, jobs, portf_batch = [], [], [], [], []
        if event_type == 'REMOVE':
            print('REMOVE EVENT IS NOT YET HANDLED')
            # TODO: create unsubscribe both portfolio tracker and market data symbols - ok to do in v1.2. for MVP let it tick until EOD and handle both at SOD
            # event_types: REMOVE,MODIFY, INSERT
        if event_type == 'INSERT':
            print('INSERT EVENT')
            portfolio_tracker_factory=PortfolioTrackerFactory(env_config,app_config,app_prefix)
            all_symbols, delta_symbols, delta_symbols_stripes, jobs = portfolio_tracker_factory.subscribe_market_data()
            # TODO: line above needs stale_threshold,symbol_stripe_size values and strategy where to source it from
            portf_batch = PortfolioTracker.subscribe_portfolios(portfolio_update_event
                                                                ,portfolio_tracker_factory.config_dict_env
                                                                ,portfolio_tracker_factory.config_dict_app)
        if event_type == 'MODIFY':
            new_image_pos = [i['dynamodb']['NewImage']['positions'] for i in portfolio_update_event['Records']]
            old_image_pos = [i['dynamodb']['OldImage']['positions'] for i in portfolio_update_event['Records']]
            if new_image_pos == old_image_pos:
                print(f'identical positions: {new_image_pos} vs. {old_image_pos} - NO ACTION NEEDED')
            else:
                portfolio_tracker_factory=PortfolioTrackerFactory(env_config,app_config,app_prefix)
                all_symbols, delta_symbols, delta_symbols_stripes, jobs = portfolio_tracker_factory.subscribe_market_data()
                # TODO: line above needs stale_threshold,symbol_stripe_size values and strategy where to source it from
                portf_batch = PortfolioTracker.subscribe_portfolios(portfolio_update_event
                                                                    ,portfolio_tracker_factory.config_dict_env
                                                                    ,portfolio_tracker_factory.config_dict_app)
        assert event_type in ['REMOVE', 'MODIFY', 'INSERT'], print(f'unknown event{event_type}') #TODO: move it before IF or change to IF-ELSE?
        return (all_symbols, delta_symbols, delta_symbols_stripes, jobs, portf_batch)
    @staticmethod
    def handle_system_event(system_event):
        print(f'recieved system_event:{system_event}')
        return_code = -1000
        handler_app_config = {'Configuration': 'PortfolioMonitoringConfigProfile',
         'Environment': 'dev',
         'Application': 'PortfolioMonitoring'}  # TODO: get it from the incoming event
        env_config,app_config=PortfolioTrackerFactory.get_env_app_config(handler_app_config)
        def __handle_start_all(start_event):
            event_type,handler_app_config=PortfolioTrackerFactory.get_handlerconfig_from_event_dynamodb(start_event)
            if False: # debugging
                os.environ["SSM_PREFIX"] = "Mvp"
            app_prefix = f'{os.environ["SSM_PREFIX"]}-'
            env_config,app_config=PortfolioTrackerFactory.get_env_app_config(handler_app_config)
            print(f"working with app_prefix:{app_prefix}  \n\n,env_config:{env_config} \n\n,app_config:{app_config} \n\n")
            portfolio_tracker_factory=PortfolioTrackerFactory(env_config,app_config,app_prefix)
            all_symbols, delta_symbols, delta_symbols_stripes, jobs = portfolio_tracker_factory.subscribe_market_data()
            all_portfolios = portfolio_tracker_factory.all_portfolios
            portfolios = []
            for one_portfolio in all_portfolios.get('Items', []):
                one_portf_batch = PortfolioTracker.create_portfolio_subscription(one_portfolio.get('portf_id', '')
                                                                                 ,config_env=portfolio_tracker_factory.config_dict_app.get('env')
                                                                                 ,job_queue=portfolio_tracker_factory.config_dict_env.get('PortfolioMonitoring-BatchEc2JobQueueName')
                                                                                 ,jobDefinition=portfolio_tracker_factory.config_dict_env.get('PortfolioMonitoring-BatchPortfolioTrackerJobDef'))
                print(f"submitted portfolio:{one_portf_batch}")
                portfolios = portfolios + [one_portf_batch]
            return (all_symbols, delta_symbols, delta_symbols_stripes, jobs, portfolios)

        def __handle_stop_all(stop_all_event):
            event_type,handler_app_config=PortfolioTrackerFactory.get_handlerconfig_from_event_dynamodb(stop_all_event)
            env_config,app_config=PortfolioTrackerFactory.get_env_app_config(handler_app_config)
            job_queue_array=[]
            job_queue_array=job_queue_array+ \
                            [app_config.get('portfolio_tracker').get('default_handler').get('deploy').get('job_queue')]
            job_queue_array=job_queue_array+ \
                            [app_config.get('market_data').get('default_handler').get('deploy').get('job_queue')]
            job_queue_array= list(set(job_queue_array))
            batch_jobs =aqi.get_batch_jobs_by_status_name(job_queue_array)
            term_jobs = []
            batch_client=boto3.client('batch')
            for one_batch_job in batch_jobs:
                jobId = one_batch_job.get('jobId', '')
                resp = batch_client.terminate_job(jobId=jobId, reason=f'EOD')
                # TODO: graceful exit
                term_jobs = term_jobs + [
                    f"{jobId}:{resp.get('ResponseMetadata', 'unknown').get('HTTPStatusCode', 'unknown')}"]
                print(one_batch_job)

        def __handle_stop(stop_event):
            commands = stop_event. \
                get('Records', [{}])[0]. \
                get('dynamodb', {}). \
                get('NewImage', {}).get('commands').get('L')
            command_res = []
            for one_command in commands:
                print(one_command)
                batches_to_stop = one_command.get('M').get('batch').get('L')
                batch_client = None
                for one_batch in batches_to_stop:
                    if batch_client is None:
                        batch_client = boto3.client('batch')
                    print(one_batch)
                    for one_batch_id in list(one_batch.get('M').keys()):
                        resp = batch_client.terminate_job(jobId=one_batch_id, reason=f'event{stop_event}')
                        command_res = command_res + [
                            f"{one_batch_id}:{resp.get('ResponseMetadata', 'unknown').get('HTTPStatusCode', 'unknown')}"]
                        print(f"terminated:{one_batch_id} with response:{resp}")
            return (command_res)
        # schedule_event={'event':'SOD'}
        event_function_switch = {
            'intraday_start_all': __handle_start_all
            , 'intraday_stop': __handle_stop
            , 'intraday_stop_all': __handle_stop_all
            , 'unknown': lambda x: print(f'unknown event:{x}')
        }
        event_type = system_event.get('Records')[0].get('eventName')
        if event_type != 'REMOVE':
            print(f'responding to new system event:{system_event}')
            event_name = system_event. \
                get('Records', [{}])[0]. \
                get('dynamodb', {}). \
                get('NewImage', {}). \
                get('event_name', {}). \
                get('S', 'unknown')
            apply_func = event_function_switch.get(event_name)
            func_res = apply_func(system_event)
            return_code = 0
        else:
            print(f'recieved REMOVE event:{system_event} - not handled')
            return_code = 0
        return (return_code)
    @staticmethod
    def handle_schedule_event(schedule_event):
        print(f'recieved schedule_event:{schedule_event}')
        #handler_app_config = {'Configuration': 'PortfolioMonitoringConfigProfile',
        #                      'Environment': 'dev',
        #                      'Application': 'PortfolioMonitoring'}
        handler_app_config = schedule_event.get('detail').get('handler')
        env_config,app_config=PortfolioTrackerFactory.get_env_app_config(handler_app_config)
        job_queue_array = app_config.get('portfolio_tracker').get('default_handler').get('deploy').get('job_queue')
        return_code = -1000
        def __handle_sod(sod_event):
            # TODO: get timethreshold and batch size from event payload
            # sod_event={'event': 'SOD', 'config': {'stale_threshold': '110m', 'symbol_stripe_size': '13'}}
            event_type,handler_app_config=PortfolioTrackerFactory.get_handlerconfig_from_event_cloudwatch(sod_event)
            if False: # debugging
                os.environ["SSM_PREFIX"] = "Mvp-"
            app_prefix = f'{os.environ["SSM_PREFIX"]}-'
            env_config,app_config=PortfolioTrackerFactory.get_env_app_config(handler_app_config)
            print(f"working with app_prefix:{app_prefix}  \n\n,env_config:{env_config} \n\n,app_config:{app_config} \n\n")
            portfolio_tracker_factory=PortfolioTrackerFactory(env_config,app_config,app_prefix)
            all_symbols, delta_symbols, delta_symbols_stripes, jobs = portfolio_tracker_factory.subscribe_market_data()
            all_portfolios = portfolio_tracker_factory.all_portfolios
            portfolios = []
            for one_portfolio in all_portfolios.get('Items', []):
                one_portf_batch = PortfolioTracker.create_portfolio_subscription(one_portfolio.get('portf_id', '')
                                                                                 ,config_env=portfolio_tracker_factory.config_dict_app.get('env')
                                                                                 ,job_queue=portfolio_tracker_factory.config_dict_env.get('PortfolioMonitoring-BatchEc2JobQueueName')
                                                                                 ,jobDefinition=portfolio_tracker_factory.config_dict_env.get('PortfolioMonitoring-BatchPortfolioTrackerJobDef') )
                print(f"submitted portfolio:{one_portf_batch}")
                portfolios = portfolios + [one_portf_batch]

            return (all_symbols, delta_symbols, delta_symbols_stripes, jobs, portfolios)

        def __handle_eod(eod_event,env_config,app_config):
            job_queue_array=[]
            job_queue_array=job_queue_array+\
                            [app_config.get('portfolio_tracker').get('default_handler').get('deploy').get('job_queue')]
            job_queue_array=job_queue_array+ \
                            [app_config.get('market_data').get('default_handler').get('deploy').get('job_queue')]
            job_queue_array= list(set(job_queue_array))
            batch_jobs = aqi.get_batch_jobs_by_status_name(job_queue_array)
            term_jobs = []
            batch_client = boto3.client('batch')
            for one_batch_job in batch_jobs:
                jobId = one_batch_job.get('jobId', '')
                resp = batch_client.terminate_job(jobId=jobId, reason=f'EOD')
                # TODO: graceful exit?
                term_jobs = term_jobs + [
                    f"{jobId}:{resp.get('ResponseMetadata', 'unknown').get('HTTPStatusCode', 'unknown')}"]
                print(f"terminated: {one_batch_job}")

        # schedule_event={'event':'SOD'}
        event_type = schedule_event.get('detail').get('event_type')
        if 'SOD' in event_type:
            print(f'recieved SOD event:{schedule_event}')
            all_symbols, delta_symbols, delta_symbols_stripes, jobs, portfolios = __handle_sod(schedule_event)
            return_code = 0
            print(f'submitted jobs:{[response["jobName"] for response in jobs]} for {delta_symbols} '
                  f'out of: {all_symbols} in batches:{delta_symbols_stripes}')
            print(f'submitted portfolios:{[response["jobName"] for response in portfolios]}')
        if 'EOD' in event_type:
            print(f'recieved EOD event:{schedule_event}')
            __handle_eod(schedule_event,env_config,app_config)
            return_code = 0
        return (return_code)

class PortfolioTracker():
    def __init__(self, config_dict_app,config_dict_env,app_prefix, portfolio_id):
        host_name = platform.node()
        print(f'PortfolioTracker configuration \n app:{config_dict_app}\n,env:{config_dict_env}\n,pref:{app_prefix}\n,pid: {portfolio_id}\n,host: {host_name}\n')
        self.exec_monitor = {}
        self.config_dict_app = config_dict_app
        self.config_dict_env = aqi.replace_string_dict_keys(config_dict_env,app_prefix,'')
        self.app_prefix = app_prefix
        self.epoch = datetime.datetime.utcfromtimestamp(0)
        self.raw_hist_data = None
        self.raw_rt_data = None
        self.portfolio_priceline = None
        self.portfolio_update_ts = None
        self.portfolio_alert = {}
        self.dynamodb = boto3.resource('dynamodb')
        self.portfolio_table = self.config_dict_env.get('PortfolioMonitoring-PortfoliosTable')
        self.dynamodb_table = self.dynamodb.Table(self.portfolio_table )
        self.marketdata_source = boto3.client('timestream-query')
        self.marketdata_source_paginator = self.marketdata_source.get_paginator('query')
        self.marketdata_source_price_field = 'measure_value::double'
        self.price_metric = 'latestPrice'
        self.timestream_tables = aqi.try_get_catch_dict(self.config_dict_env, 'PortfolioMonitoring-TimestreamTables')
        self.marketdata_source_db = aqi.try_get_catch_dict(self.config_dict_env, 'PortfolioMonitoring-TimestreamDb') # TODO get from parameter store
        self.marketdata_source_table = aqi.try_get_catch_dict(self.timestream_tables, 'market_data_table')
        self.portfolio_target_table = aqi.try_get_catch_dict(self.timestream_tables, 'portfolio_table')
        # self.marketdata_source_db = self.config_dict_env.get('PortfolioMonitoring-TimestreamDb','MvpPortfolioMonitoringTimestream') # TODO get from parameter store
        # self.marketdata_source_table = self.config_dict_env.get('default','iex_realtime_data') # TODO get from parameter store
        # self.portfolio_target_table = self.config_dict_env.get('default','portfolio_tracker')
        # calculationPrice, lastTradeTime, not a part of normalized dimensions/measures anymore
        self.marketdata_source_query = \
            f"SELECT distinct time,symbol,latestUpdate,measure_value::double  \
            FROM {self.marketdata_source_db}.{self.marketdata_source_table}\
            where measure_name='{self.price_metric}'\
            and latestUpdate >= '%s'  and latestUpdate != 'None' and symbol in (%s)\
                order by time desc"  # TODO: get database name and table name from parameter store
        # self.marketdata_source_query = \
        #     f"SELECT distinct time,symbol,latestUpdate,measure_value::double  \
        #     FROM {self.marketdata_source_db}.{self.marketdata_source_table}\
        #     where measure_name='{self.price_metric}' and calculationPrice = 'tops'\
        #     and lastTradeTime=latestUpdate and openTime = 'None'\
        #     and latestUpdate >= '%s' and symbol in (%s)\
        #         order by time desc"  # TODO: get database name and table name from parameter store
        # self.portfolio_latest_ts_query = \
        #     f"SELECT max(time) time FROM {self.marketdata_source_db}.{self.portfolio_target_table} \
        #     where portf_id = '{portfolio_id}' "  # TODO: get database name and table name from parameter store
        self.portfolio_latest_ts_query = \
               f"select max(latestUpdate) latestUpdate from\
        (select min(latestUpdate) latestUpdate from\
        (SELECT max(latestUpdate) latestUpdate,measure_name\
        FROM {self.marketdata_source_db}.{self.portfolio_target_table} where portf_id = '{portfolio_id}' and latestUpdate != 'None'\
        group by measure_name) t\
            union select ago(10d) latestUpdate) t1 "
          # TODO: get database name and table name from parameter store
        self.marketdata_source_schema = None
        self.marketdata_target = boto3.client(
            'timestream-write')  # ,config=Config(read_timeout=20, max_pool_connections=5000, retries={'max_attempts': 10}))

        self.portfolio = self.__portfolio(portfolio_id)
        self.portfolio_pd = self.__portfolio_pd()
        self.exception_threshold = 20
        self.current_exception_count = 0
        self.debug_pnl_calc=True
    # Can we just use awswrangler instead?
    def __ts_md_to_df(self, ts_md_raw, marketdata_source_schema=None):
        if ts_md_raw.get('QueryStatus').get('CumulativeBytesScanned') > 0:
            if marketdata_source_schema is None:
                marketdata_source_schema = [i['Name'] for i in ts_md_raw['ColumnInfo']]
            ret_val = pd.DataFrame([
                [j['ScalarValue'] for j in i['Data']]
                for i in ts_md_raw['Rows']]
                , columns=marketdata_source_schema)
            if self.marketdata_source_price_field in ret_val:
                ret_val[self.marketdata_source_price_field] = ret_val[self.marketdata_source_price_field].astype(float)
                ret_val = ret_val.rename(columns={self.marketdata_source_price_field:
                                                      self.price_metric})
        else:
            ret_val = pd.DataFrame()
        return (ret_val)
    def __portfolio(self, portfolio_id):
        # portfolio_id='JD2966'
        ret_items = self.dynamodb_table.query(KeyConditionExpression=Key('portf_id').eq(portfolio_id))['Items']
        if len(ret_items) == 0:
            raise RuntimeError(
                f'Unknown portfolio:{portfolio_id}, querying DB:{self.dynamodb}, table:{self.dynamodb_table}')
        else:
            assert len(ret_items) == 1, f"duplicate portfolios for id:{portfolio_id}"
            portf = ret_items[0]
            portf_create_ts = str(portf.get('portf_create_ts'))[0:10]
            portf_create_ts=f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(portf_create_ts)))}.000000000"
            portf_last_update = portf.get('last_tracker_update',portf_create_ts)
        # if there are portfolio updates in TS, set last_tracker_update to max(last_tracker_update,latest_ts)
        try:
            portfolio_update_results=self.marketdata_source.query(QueryString=self.portfolio_latest_ts_query)
            portf_last_update = max(self.__ts_md_to_df(portfolio_update_results).get('latestUpdate')[0],portf_last_update)
        except Exception as cust_exc:
            print(f"Exception {cust_exc} calculating portfolio start time, setting start time to: {portf_last_update}")

        portf['last_tracker_update'] = portf_last_update
        return (portf)
    def __portfolio_pd(self):
        portfolio_pd = pd.DataFrame.from_dict([{'symbol': list(i.keys())[0], 'weight': list(i.values())[0]}
                                               for i in self.portfolio['positions']]).set_index('symbol')
        portfolio_pd['portf_id'] = self.portfolio['portf_id']
        portfolio_pd['weight'] = portfolio_pd['weight'].astype(float)
        gross_weight = portfolio_pd['weight'].abs().sum()
        short_weight = portfolio_pd.query('weight<0')['weight'].abs().sum()
        long_weight = portfolio_pd.query('weight>0')['weight'].abs().sum()
        assert gross_weight != 0 \
            , f"portfolio{self.portfolio['portf_id']} has no positions"
        assert short_weight == 1 or short_weight == 0 \
            , f"sum of short weights are not 1 or 0, portfolio:{self.portfolio['portf_id']}"
        assert long_weight == 1 or long_weight == 0 \
            , f"sum of long weights are not 1 or 0, portfolio:{self.portfolio['portf_id']}"
        return (portfolio_pd)
    def load_portf_market_data(self):
        try:
            symbols = ([list(i.keys())[0] for i in self.portfolio['positions']])
            start_point=self.portfolio['last_tracker_update']
            prep_query = self.marketdata_source_query % (start_point, "'" + "','".join(symbols) + "'")
            page_iterator = self.marketdata_source_paginator.paginate(QueryString=prep_query)
            portfolio_md_pages = []
            for page in page_iterator:
                portfolio_md_pages = portfolio_md_pages + [self.__ts_md_to_df(page)]  # [__ts_md_to_df(self,portf_market_data_raw)]#[self.__ts_md_to_df(portf_market_data_raw)]
            portfolio_md = pd.concat(portfolio_md_pages)
            self.portfolio_md = portfolio_md
            self.portfolio_priceline=None
            self.portfolio_pnl=None
        except Exception as exc:
            print(f'exception [get_portf_market_data]:{exc}')
            self.current_exception_count = self.current_exception_count + 1
            if self.current_exception_count > self.exception_threshold:
                raise
    def calc_portf_pnl(self):
        try:
            port_pnl = pd.pivot_table(self.portfolio_priceline, values='symbol_pnl',index=['time', 'portf_id'], aggfunc=sum,columns=['symbol'])
            port_pnl =port_pnl.sort_index().fillna(value=0)
            port_pnl['port_pnl'] =port_pnl.sum(axis=1)
            port_pnl['latestUpdate'] = max(port_pnl.reset_index().get('time'))
            self.portfolio_pnl = port_pnl[['port_pnl','latestUpdate']]
        except Exception as exc:
            print(f'exception [get_portf_pnl]:{exc}')
            self.current_exception_count = self.current_exception_count + 1
            if self.current_exception_count > self.exception_threshold:
                raise
    def calc_portf_priceline(self):
        try:
            self.portfolio_priceline = self.portfolio_md.set_index(['symbol']).join(self.portfolio_pd)

            def add_pnl(one_group, measure_field):
                one_group.reset_index().set_index(['time']).sort_index(ascending=False)
                one_group['symbol_pct_change'] = one_group[measure_field].pct_change(periods=-1).fillna(0)
                one_group['symbol_pnl'] = one_group['symbol_pct_change'].multiply(one_group['weight'])
                return (one_group)

            self.portfolio_priceline = self.portfolio_priceline.groupby('symbol'). \
                apply(lambda x: add_pnl(x, self.price_metric))
        except Exception as exc:
            print(f'exception [get_portf_priceline]:{exc}')
            self.current_exception_count = self.current_exception_count + 1
            if self.current_exception_count > self.exception_threshold:
                raise
    def save_portf_pnl(self):
        try:
            ts_client = self.marketdata_target
            ts_DatabaseName=self.marketdata_source_db#'AWsomeBuilder_east2',
            ts_TableName=self.portfolio_target_table#'portfolio_tracker',

            def string_to_ts_iso(date_epoch, date_as_string):
                date_as_date = isoparse(date_as_string)
                timestamp = (date_as_date - date_epoch).total_seconds() * 1000
                return (timestamp)

            def write_to_ts(record_batch):
                self.exec_monitor['total_record_count'] += len(record_batch)
                try:  # TODO DatabaseName and TableName get from Parameter Store
                    ts_client.write_records(
                        DatabaseName=ts_DatabaseName,#'AWsomeBuilder_east2',
                        TableName=ts_TableName,#'portfolio_tracker',
                        Records=record_batch
                    )
                    print(f'accepted portfolio pnl batch count:{len(record_batch)}, highwatermakr:{self.exec_monitor["max_time"]}')
                except ts_client.exceptions.ValidationException as ve:
                    self.exec_monitor['error_count'] += len(record_batch)
                    self.exec_monitor['other_exceptions'] = self.exec_monitor['other_exceptions'] + \
                                                            [{'exc': ve, 'raw_record': record_batch}]
                except ts_client.exceptions.RejectedRecordsException as rre:
                    self.exec_monitor['reject_count'] += len(record_batch)
                    rej_record_details = []
                    for one_rec in rre.response['RejectedRecords']:
                        one_rec['raw_record'] = record_batch[one_rec['RecordIndex']]
                        rej_record_details = rej_record_details + [one_rec]
                    self.exec_monitor['rejected_records'] = self.exec_monitor['rejected_records'] + rej_record_details
                    self.exec_monitor['rejected_records_percent']=self.exec_monitor['reject_count']/self.exec_monitor['total_record_count']

            def prep_and_write_to_ts(df_pd, ts_client):
                #
                df_pd = df_pd.reset_index()
                time_f = 'time'
                measure_f = ['port_pnl']
                dim_f = ['symbol', 'latestUpdate', 'weight', 'portf_id']
                record_batch = []
                self.exec_monitor = {}
                self.exec_monitor['error_count'] = 0
                self.exec_monitor['reject_count'] = 0
                self.exec_monitor['rec_count'] = 0
                self.exec_monitor['total_record_count']=0
                self.exec_monitor['rejected_records_percent']=0
                self.exec_monitor['rejected_records'] = []
                self.exec_monitor['other_exceptions'] = []
                self.exec_monitor['max_time'] = ''
                for one_rec in df_pd.iterrows():
                    dimensions = [{'Name': i, 'Value': str(one_rec[1].get(i, i))} for i in dim_f]
                    record_time = int(string_to_ts_iso(self.epoch, one_rec[1][time_f]) * 1)
                    records = [{
                        'Dimensions': dimensions,
                        'MeasureName': i,
                        'MeasureValue': str(one_rec[1].get(i)),
                        'Time': str(record_time)
                    }
                        for i in measure_f]
                    record_batch = record_batch + records
                    self.exec_monitor['rec_count'] += 1
                    self.exec_monitor['max_time'] = max([one_rec[1][time_f],self.exec_monitor['max_time']])

                    if self.exec_monitor['rec_count'] >= int(99 / len(records)):
                        write_to_ts(record_batch)
                        record_batch = []
                        self.exec_monitor['rec_count'] = 0
                if len(record_batch) > 0:
                    write_to_ts(record_batch)

            #
            prep_and_write_to_ts(self.portfolio_pnl, ts_client)
            if self.exec_monitor['max_time'] != float('-inf'):
                self.portfolio['last_tracker_update'] = self.exec_monitor['max_time']
        except Exception as exc:
            print(f'exception:{exc}')
            self.current_exception_count = self.current_exception_count + 1
            if self.current_exception_count > self.exception_threshold:
                raise
        return (self.portfolio['last_tracker_update'])
    def save_portf_priceline(self):
        if (self.debug_pnl_calc):
            try:
                ts_client = self.marketdata_target
                ts_DatabaseName=self.marketdata_source_db#'AWsomeBuilder_east2',
                ts_TableName=self.portfolio_target_table#

                def string_to_ts_iso(date_epoch, date_as_string):
                    date_as_date = isoparse(date_as_string)
                    timestamp = (date_as_date - date_epoch).total_seconds() * 1000
                    return (timestamp)

                def write_to_ts(record_batch):
                    try:  # TODO DatabaseName and TableName get from Parameter Store
                        ts_client.write_records(
                            DatabaseName=ts_DatabaseName,
                            TableName=ts_TableName,
                            Records=record_batch
                        )
                        print(f'accepted priceline data, batch count:{len(record_batch)}, highwatermark:{self.exec_monitor["max_time"]}')
                    except ts_client.exceptions.ValidationException as ve:
                        self.exec_monitor['error_count'] += 1
                        self.exec_monitor['other_exceptions'] = self.exec_monitor['other_exceptions'] + \
                                                                [{'exc': ve, 'raw_record': record_batch}]
                    except ts_client.exceptions.RejectedRecordsException as rre:
                        self.exec_monitor['reject_count'] += 1
                        rej_record_details = []
                        for one_rec in rre.response['RejectedRecords']:
                            one_rec['raw_record'] = record_batch[one_rec['RecordIndex']]
                            rej_record_details = rej_record_details + [one_rec]
                        self.exec_monitor['rejected_records'] = self.exec_monitor['rejected_records'] + rej_record_details

                def prep_and_write_to_ts(df_pd, ts_client):
                    #
                    df_pd = df_pd.reset_index()
                    time_f = 'time'
                    measure_f = ['latestPrice', 'symbol_pct_change', 'symbol_pnl']
                    dim_f = ['symbol', 'latestUpdate', 'weight', 'portf_id']
                    record_batch = []
                    self.exec_monitor = {}
                    self.exec_monitor['error_count'] = 0
                    self.exec_monitor['reject_count'] = 0
                    self.exec_monitor['rec_count'] = 0
                    self.exec_monitor['rejected_records'] = []
                    self.exec_monitor['other_exceptions'] = []
                    self.exec_monitor['max_time'] = ''
                    for one_rec in df_pd.iterrows():
                        dimensions = [{'Name': i, 'Value': str(one_rec[1][i])} for i in dim_f]
                        record_time = int(string_to_ts_iso(self.epoch, one_rec[1][time_f]) * 1)
                        records = [{
                            'Dimensions': dimensions,
                            'MeasureName': i,
                            'MeasureValue': str(one_rec[1][i]),
                            'Time': str(record_time)
                        }
                            for i in measure_f]
                        record_batch = record_batch + records
                        self.exec_monitor['rec_count'] += 1
                        self.exec_monitor['max_time'] = max([one_rec[1][time_f],self.exec_monitor['max_time']])

                        if self.exec_monitor['rec_count'] >= int(99 / len(records)):
                            write_to_ts(record_batch)
                            record_batch = []
                            self.exec_monitor['rec_count'] = 0
                    if len(record_batch) > 0:
                        write_to_ts(record_batch)

                #
                prep_and_write_to_ts(self.portfolio_priceline, ts_client)
                if self.exec_monitor['max_time'] != float('-inf'):
                    self.portfolio['last_tracker_update'] = self.exec_monitor['max_time']
            except Exception as exc:
                print(f'exception [save_portf_priceline]:{exc}')
                self.current_exception_count = self.current_exception_count + 1
                if self.current_exception_count > self.exception_threshold:
                    raise
        else:
            print(f"skipping save portolfio priceline:{self.debug_pnl_calc}")
        return (self.portfolio['last_tracker_update'])
    def save_portf_state(self):
        # TODO: this is depricated but dont delete. state management might become required
        try:
            if len(self.portfolio_pnl) > 0:
                self.portfolio['last_market_data_update'] = (self.portfolio_md['latestUpdate'].max())
                self.portfolio['last_priceline_update'] = (self.portfolio_priceline['latestUpdate'].max())
                self.portfolio['last_pnl_update'] = (self.portfolio_pnl['latestUpdate'].max())
                dynamodb = self.dynamodb
                portf_table = self.dynamodb_table
                portf_table.put_item(
                    TableName=self.portfolio_table,
                    Item=self.portfolio
                )
            else:
                print(
                    f'no new updates as of {self.portfolio["last_tracker_update"]} for portfolio {self.portfolio["portf_id"]}')
        except Exception as exc:
            print(f'exception:{exc}')
            self.current_exception_count = self.current_exception_count + 1
            if self.current_exception_count > self.exception_threshold:
                raise
    def get_hist_data(self, symbols, start_date, end_date=None):
        print(symbols, start_date, end_date)
        # TODO add with (or BY) the customer
    @staticmethod
    def portfolio_tracker_main(config_env,portf_id):
        # portf_id='4f976bb465b9d1963b00d98b135eb373'
        if False: # debugging
            os.environ["SSM_PREFIX"] = "Mvp"
            max_symbols = 1
            config_json= '{"version":"sandbox",' \
                         '"token_secret":"iex_api_token_pk_sandbox",' \
                         '"token_secret_streaming":"iex_api_token_pk",' \
                         '"url":"https://cloud-sse.iexapis.com",' \
                         '"streaming_endpoint_equity":"stocksUSNoUTP"}'
        app_prefix = f"{os.environ['SSM_PREFIX']}-"
        aws_region=os.environ.get('AWS_DEFAULT_REGION',"us-east-2")
        env_config = aqi.get_app_config_from_paramstore(aws_region)
        app_config = (boto3.client('appconfig',region_name=aws_region). \
                      get_configuration(Application='PortfolioMonitoring'
                                        ,Environment=config_env
                                        ,Configuration='PortfolioMonitoringConfigProfile'
                                        , ClientId=f'{random.randint(-sys.maxsize,sys.maxsize)}').get('Content').read())
        app_config=json.loads(app_config.decode('utf-8'))

        one_port = PortfolioTracker( app_config,env_config,app_prefix, portf_id)
        refresh_count=0
        refresh_count_target= int(600/int(one_port.portfolio['handler_info']['refresh_sec']))
        default_handler = {"refresh_sec": "60", "deploy": "lambda"}  # TODO: get it from param store
        deploy_option = one_port.portfolio.get('handler_info', None)
        if deploy_option is None:
            one_port.portfolio['handler_info'] = default_handler

        if one_port.portfolio['handler_info']['deploy'] == 'batch':
            while True:
                print(f"Load porfolio market data======:{datetime.datetime.now(pytz.timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S') }")
                one_port.load_portf_market_data()
                print(f"priceline data======:{datetime.datetime.now(pytz.timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S') }")
                one_port.calc_portf_priceline()
                print(f"calc portfolio_pnl======:{datetime.datetime.now(pytz.timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S') }")
                #one_port.portfolio_priceline.to_csv("priceline.csv")
                one_port.calc_portf_pnl()
                print(f"save_portf_priceline ======:{datetime.datetime.now(pytz.timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S') }")
                one_port.save_portf_priceline()
                print(f"save_portf_pnl ======:{datetime.datetime.now(pytz.timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S') }")
                one_port.save_portf_pnl()
                refresh_count+=1
                print(f"sleeping for:{one_port.portfolio['handler_info']['refresh_sec']}-------:{datetime.datetime.now(pytz.timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S') }")
                #one_port.save_portf_state()
                time.sleep(one_port.portfolio['handler_info']['refresh_sec'])
                #TODO: return if lambda (not batch handler) and get rid of ELSE
                if refresh_count%refresh_count_target==0:
                    print(f"full refresh ---{refresh_count}----:{datetime.datetime.now(pytz.timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S') }")
                    one_port = PortfolioTracker( app_config,env_config,app_prefix, portf_id) #TODO: room for the optimization
                #break
        else:
            one_port.load_portf_market_data()
            one_port.calc_portf_priceline()
            one_port.calc_portf_pnl()
            one_port.save_portf_priceline()
            one_port.save_portf_pnl()
            #one_port.save_portf_state()

    @staticmethod
    def create_portfolio_subscription(port_id,config_env,job_queue,jobDefinition):
        batch_client = boto3.client('batch')
        job_name = f'portf_sub_{port_id}'
        job_queue = job_queue
        response = batch_client.submit_job(
            jobName=job_name,
            jobQueue=job_queue,
            jobDefinition=jobDefinition,
            containerOverrides={
                'command': ["src/portfolio_tracker.py", f"{config_env}",f"{port_id}"]
            },
            timeout={
                'attemptDurationSeconds': 60 * 60 * 24 * 7
            },
        )
        return (response)
    @staticmethod
    def subscribe_portfolios(portfolio_update_event,config_dict_env,config_dict_app):
        portfolio_ids = [i['dynamodb']['NewImage']['portf_id']['S'] for i in portfolio_update_event['Records']]
        portf_batch = []

        for one_portf in portfolio_ids:
            print(f"subscribing portfolio:{one_portf} \n\n, {config_dict_env} \n\n, {config_dict_app}")
            one_portf_batch = PortfolioTracker.create_portfolio_subscription(one_portf
                                                                             ,config_dict_app.get('env')
                                                                             ,config_dict_env.get('PortfolioMonitoring-BatchEc2JobQueueName')
                                                                             ,config_dict_env.get('PortfolioMonitoring-BatchPortfolioTrackerJobDef'))
            portf_batch = portf_batch + [one_portf_batch]
        return (portf_batch)

