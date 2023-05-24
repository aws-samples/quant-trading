import json
import boto3
import datetime
import time
import random
import sys
import os
import itertools   

# IEX
from sseclient import SSEClient
import pandas as pd
# BPIPE
# TODO add logic to dockerfiles
import asyncio
from xbbg import blp
import copy

sys.path.append('/var/task/shared/python')
sys.path.append('/src/shared/python/')
sys.path.append('/home/ec2-user/environment/AWSQuant/aws-quant-infra/src/shared/python')
import aws_quant_infra as aq_i
if False:# for debugging
    import src.shared.python.aws_quant_infra as aq_i
    import imp
    imp.reload(aq_i)

class MarketDataProvider(object):
    def __init__(self, env_config,app_config,app_prefix):
        if False: # debugging info
            config_json='{"Mvp-version":"sandbox","Mvp-token_secret":"iex_api_token_pk_sandbox" \
                 ,"Mvp-token_secret_streaming":"iex_api_token_pk" \
                 ,"Mvp-url":"https://cloud-sse.iexapis.com","Mvp-streaming_endpoint_equity":"stocksUSNoUTP"}'
        # config_dict_app = app_config
        # config_dict_env=aq_i.replace_string_dict_keys(env_config, app_prefix, '')
        self.config_dict_app = app_config
        self.config_dict_env = aq_i.replace_string_dict_keys(env_config, app_prefix, '')
        self.app_prefix = app_prefix
        self.aws_deploy_region = aq_i.try_get_catch_dict(self.config_dict_app, 'AWS_REGION') # self.config_dict_app.get('AWS_REGION')
        
        self.market_data = aq_i.try_get_catch_dict(self.config_dict_app, 'market_data')
        self.version = aq_i.try_get_catch_dict(self.market_data, 'version') # .get('version', 'sandbox')
        token_secret = aq_i.try_get_catch_dict(self.market_data, 'token_secret')
        token_secret_streaming = aq_i.try_get_catch_dict(self.market_data, 'token_secret_streaming')
        self.token = ''
        if self.version == 'sandbox':
            assert 'sandbox' in token_secret, "Use sandbox token in sandbox environment"
            self.token = aq_i.get_secret(token_secret, self.aws_deploy_region)[token_secret]
        else:
            assert 'sandbox' not in token_secret, "Use non-sandbox token in non-sandbox environment"
            self.token = aq_i.get_secret(token_secret, self.aws_deploy_region)[token_secret]

        self.url = aq_i.try_get_catch_dict(self.market_data, 'url')
        #self.token_streaming = json.loads(aq_i.get_secret(token_secret_streaming, self.aws_deploy_region).get(token_secret_streaming)).get(token_secret_streaming)
        self.token_streaming = aq_i.get_secret(token_secret_streaming, self.aws_deploy_region).get(token_secret_streaming)
        self.streaming_end_point_equity = aq_i.try_get_catch_dict(self.market_data, 'streaming_endpoint_equity')
        self.timestream_tables = aq_i.try_get_catch_dict(self.config_dict_env, 'PortfolioMonitoring-TimestreamTables')
        self.timestream_config = {'db_name':aq_i.try_get_catch_dict(self.config_dict_env, 'PortfolioMonitoring-TimestreamDb')
            ,'table_name':aq_i.try_get_catch_dict(self.timestream_tables, 'market_data_table')
            ,'ts_write_client':boto3.client('timestream-write', self.aws_deploy_region)
                                  }
        delim = "'"
        self.start_epochtime_sql_template = f'select min(latestUpdate) latestUpdate from ' \
                                            f'(select max(latestUpdate) latestUpdate,symbol ' \
                                            f'FROM {self.timestream_config.get("db_name")}.{self.timestream_config.get("table_name")} ' \
                                            f'where symbol in ({delim}%s{delim}) group by symbol) t'
    
    # properties
    @property
    def version(self):
        return self.__version__

    @property
    def token(self):
        return self.__token__

    @property
    def url(self):
        return self.__url__

    @property
    def streaming_end_point_equity(self):
        return self.__streaming_end_point_equity__

    @property
    def streaming_url_template(self):
        return self.__streaming_url_template__

    # setters
    @version.setter
    def version(self, var):
        self.__version__ = var

    @token.setter
    def token(self, var):
        self.__token__ = var

    @url.setter
    def url(self, var):
        self.__url__ = var

    @streaming_end_point_equity.setter
    def streaming_end_point_equity(self, var):
        self.__streaming_end_point_equity__ = var

    @streaming_url_template.setter
    def streaming_url_template(self, var):
        self.__streaming_url_template__ = var

    def get_start_epoch_time(self, symbols):
        query = self.start_epochtime_sql_template % ("','".join(symbols))
        ts_db_query = boto3.client('timestream-query', self.aws_deploy_region)
        try:
            raw_data = ts_db_query.query(QueryString=query)
            default_start = int((datetime.datetime.now() - datetime.timedelta(minutes=60)).timestamp() * 1000)
            epoch_start = raw_data.get('Rows', [])[0].get('Data', [])[0].get('ScalarValue', default_start)
        except:
            default_start = int((datetime.datetime.now() - datetime.timedelta(minutes=60)).timestamp() * 1000)
            epoch_start = default_start
        return epoch_start

    @staticmethod
    def get_data_provider_inits(config_env,symbols):
        if False: # debugging
            os.environ["SSM_PREFIX"] = "Mvp"
            os.environ["AWS_REGION"] = "us-east-1" #TODO: move into separate debug settings and use MODE (deploy/local...) in code
        app_prefix = f"{os.environ['SSM_PREFIX']}-"
        aws_region=os.environ.get('AWS_DEFAULT_REGION',"us-east-1")
        env_config = aq_i.replace_string_dict_keys(aq_i.get_app_config_from_paramstore(aws_region),app_prefix,'')
        hosted_config_details = json.loads(env_config.get('PortfolioMonitoring-AppConfigDetails'))
        app_config = (boto3.client('appconfig',region_name=aws_region).\
            get_configuration(Application=hosted_config_details.get('Application')
                              ,Environment=config_env
                              ,Configuration=hosted_config_details.get('Configuration')
                              , ClientId=f'{random.randint(-sys.maxsize,sys.maxsize)}'
                              #,ClientConfigurationVersion=hosted_config_details.get(config_env)
                              ).get('Content').read())
        app_config=json.loads(app_config.decode('utf-8'))
        app_config['AWS_REGION']=aws_region
        if type(symbols) == str:
            symbol_list = symbols.split(',')
        else:
            symbol_list = symbols
        print(f"working with: {symbol_list}\n\n")
        print(f"app_prefix: {app_prefix}\n\n")
        print(f"aws_region: {aws_region}\n\n")
        print(f"hosted_config_details: {hosted_config_details}\n\n")
        print(f"APP CONFIG: {app_config}\n\n")
        print(f"ENV CONFIG: {env_config}\n\n")
        
        return (env_config, app_config, app_prefix, symbol_list)

    @staticmethod
    def subscribe_main(config_env,symbols,seconds): # TODO: generate config off parameter store created during deploy
        env_config, app_config, app_prefix, symbol_list = MarketDataProvider.get_data_provider_inits(config_env, symbols)
        market_data_source = app_config.get("market_data",{}).get("source",None)
        print(f'using {market_data_source} for market data, refresh interval: {seconds}')
        if market_data_source == 'IEX':
            IexDataProvider.subscribe_main(env_config, app_config, app_prefix, symbol_list)
        elif market_data_source == 'BPIPE':
            BloombergDataProvider.subscribe_main(env_config, app_config, app_prefix, symbol_list,seconds)
        else:
            print(f'Unsupported market data source found! Source {market_data_source} is not supported!')
            sys.exit(1)
    
class IexDataProvider(MarketDataProvider):
    def __init__(self, env_config,app_config,app_prefix):
        MarketDataProvider.__init__(self, env_config,app_config,app_prefix)
        self.streaming_url_template = f'{self.url}/stable/{self.streaming_end_point_equity}?symbols=%s' \
                                      f'&token={self.token_streaming}&snapshotAsOf=%s'
        self.timestream_adapter = aq_i.TimestreamAdapter(
            ts_config=self.timestream_config,
            source='IEX',
            region=self.aws_deploy_region
        )
        print(f"connecting to: {self.streaming_url_template}")
    
    def get_iex_sse_stream(self, symbols):
        # symbols=['amzn','gs']
        epoch_start = self.get_start_epoch_time(symbols)
        sse_url = self.streaming_url_template % (','.join(symbols), epoch_start)
        print(f"starting market data {sse_url}")
        messages = SSEClient(sse_url)
        return messages

    @staticmethod
    def test_harness():
        dynamodb = boto3.resource('dynamodb')
        symbol_table_name = 'symbol_portfolio_map'
        symbol_table = dynamodb.Table(symbol_table_name)
        create_ts = int(time.time() * 1000000)
        portf_item = [{
            'symbol': 'GS'
            , 'symbol_init_ts': create_ts
            , 'symbol_last_update': create_ts
            , 'portfolios': ['6984271344a47c16d3c5f3f11f09ae14']
            , 'handler_info': {'deploy': 'batch', 'refresh_sec': 0}
        }
            , {
                'symbol': 'AMZN'
                , 'symbol_init_ts': create_ts
                , 'symbol_last_update': create_ts
                , 'portfolios': ['3122865dbdfc83f3a839be2c671bd93d', '6984271344a47c16d3c5f3f11f09ae14']
                , 'handler_info': {'deploy': 'batch', 'refresh_sec': 0}}]
        for one_item in portf_item:
            symbol_table.put_item(
                TableName=symbol_table_name,
                Item=one_item
            )
        return portf_item

    @staticmethod
    def subscribe_main(env_config,app_config,app_prefix,symbols): # TODO: generate config off parameter store created during deploy
        iex_dp = IexDataProvider(env_config,app_config,app_prefix)
        price_stream = iex_dp.get_iex_sse_stream(symbols)
        iex_dp.timestream_adapter.write_iex_data(price_stream, 1)
        
class BloombergDataProvider(MarketDataProvider):
    bpipe_info = [
         'OPEN'
        ,'BID'
        ,'ASK'
        ,'PRICE_OPEN_RT'
        ,'CLOSE'
        ,'HIGH'
        ,'LOW'
        ,'LAST_PRICE'
        ,'OPEN_LOCAL_SOURCE_RT'
        ,'HIGH_LOCAL_SOURCE_RT'
        ,'LOW_LOCAL_SOURCE_RT'
        ,'CLOSE_LOCAL_SOURCE_RT'
        ,'TICKER'
        ,'BLOOMBERG_SEND_TIME_RT'
        ,'LAST_TRADE_PRICE_TIME_TODAY_RT'
        ,'CONTINUOUS_VOLUME_RT'
        ,'VOLUME'
        ,'EQY_PRIM_EXCH_SHRT'
        ,'TIME'
        ,'NAME'
        ,'CRNCY'
    ]
    market_view_columns=bpipe_info+['primaryExchange', 'openTime', 'openSource', 'closeTime', 'closeSource', 
    'highTime', 'highSource', 'lowTime', 'lowSource', 'latestSource', 'latestTime', 'currency', 'marketCap', 'peRatio']
    def __init__(self, env_config,app_config,app_prefix):
        MarketDataProvider.__init__(self, env_config,app_config,app_prefix)
        self.timestream_adapter = aq_i.TimestreamAdapter(
            ts_config=self.timestream_config,
            source='BPIPE',
            region=self.aws_deploy_region
        )
        self.market_view_batch = []
        self.count = 0
        self.market_view = {}
        self.bpipe_connect =  self.config_dict_app.get('market_data',{}).get('bpipe_connect',None)
        
        print(f"connecting to:{self.bpipe_connect}")

    def _market_view_upsert(self, key):
        if key in self.market_view.keys():
            pass
        else:
            self.market_view[key]=dict(zip(iter(self.market_view_columns),itertools.repeat(float('nan'), len(self.market_view_columns))))

    def _update_market_view(self, raw_bpipe_data):
                
        now_time = datetime.datetime.now(datetime.timezone.utc)
        #DEBUG
        # if False:
        #     with open(f'raw_bpipe_data_{now_time.strftime("%m_%d_%Y_%H_%M_%S")}.pickle', 'wb') as handle:
        #         pickle.dump(raw_bpipe_data, handle, protocol=pickle.HIGHEST_PROTOCOL)
                
        if "BLOOMBERG_SEND_TIME_RT" in raw_bpipe_data.keys():
            tick_time = datetime.datetime.combine(now_time.date(),raw_bpipe_data['BLOOMBERG_SEND_TIME_RT']).replace(tzinfo=datetime.timezone.utc)
        elif "LAST_TRADE_PRICE_TIME_TODAY_RT" in raw_bpipe_data.keys():
            tick_time = datetime.datetime.combine(now_time.date(),raw_bpipe_data['LAST_TRADE_PRICE_TIME_TODAY_RT']).replace(tzinfo=datetime.timezone.utc)
        else:
            tick_time  =now_time
        symbol = raw_bpipe_data.get('TICKER')
        #field = raw_bpipe_data.get('FIELD')
        self._market_view_upsert(symbol)
        current_tick_time = self.market_view.get(symbol).get('tick_time',datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
        is_updated = False
        if tick_time>current_tick_time:
            self.market_view.get(symbol)['tick_time']=tick_time
            self.market_view.get(symbol)['latestTime']=tick_time
            self.market_view.get(symbol)['LAST_TRADE_PRICE_TIME_TODAY_RT']=tick_time
            is_updated = True
            #print(f"tick_time:{tick_time},current_tick_time:{current_tick_time}")
        for field,new_field_value in [ i for i in raw_bpipe_data.items() if i[0] not in ["FIELD"] ] :
            #current_field_value = self.market_view.get(symbol).get(field,None)
            current_field_value = self.market_view.get(symbol).get(field,None)
            #new_field_value=raw_bpipe_data.get(field)
            if current_field_value != new_field_value:
                self.market_view.get(symbol)[field]=new_field_value
                is_updated = True
                #print(f"symbol:{symbol},field:{field},current_field_value:{current_field_value},new_field_value:{new_field_value},\n mv:{self.market_view}")
        if is_updated:
            self.market_view_batch.append(copy.deepcopy(self.market_view))
    
    def _market_view_to_pd(self):
        pd_data=[]
        for one_market_view in  self.market_view_batch:
            for one_symbol,one_symbol_data in one_market_view.items():
                one_symbol_pd = pd.DataFrame([one_symbol_data])
                #print(f"one symbol PD:{one_symbol_pd}")
                one_symbol_pd['TICKER']=one_symbol
                pd_data=pd_data+[one_symbol_pd]
        mv_pd = pd.concat(pd_data)
        return(mv_pd)
        
    async def get_stream(self, symbols, write_marketview_func,seconds):#asset_class='US Equity'):='BGN Curncy'
        options =[f"interval={int(seconds):.1f}"]
        async for data in blp.live([ f'{s}' for s in symbols], flds=self.bpipe_info, info=self.bpipe_info,options=options):
            self._update_market_view(data)
            # Is this akin to buffer_size check for write_iex?
            if len(self.market_view_batch)>0 :#and len(self.market_view_batch)==500: 
                #assert len(self.market_view_batch)==len(self._market_view_to_pd().drop_duplicates()), f'unequal array:{(self._market_view_to_pd())} and pd:{(self._market_view_to_pd().drop_duplicates())}'
                #print(self.market_view)
                #print(f"unique mv:{len(self.market_view_batch)}")
                #print(f"unique mv:\n {(self.market_view_batch)}")
                #print(f"_market_view_to_pd:{self._market_view_to_pd()}")
                #self._market_view_to_pd().to_csv('bpipe_pd.csv')
                #break
                #if len(self._market_view_to_pd())%100==0:
                 #   print(f"size of market view array: {[i for i in self.market_view_batch]} \n")
                #print(f"market_data: {(self.market_view)} \n")
                #print(f"market_view_batch: {self._market_view_to_pd().to_csv()} \n")
                #self._market_view_to_pd().to_csv('bpipe_pd.csv')
                write_marketview_func(self._market_view_to_pd().drop_duplicates())
                self.market_view_batch = []
            
    @staticmethod
    def subscribe_main(env_config,app_config,app_prefix,symbols,seconds): # TODO: generate config off parameter store created during deploy
        bpipe_dp = BloombergDataProvider(env_config,app_config,app_prefix)
        # TODO add logic for handling ALL connection options (port, tls, existing session)
        blp.connect(auth_method='app', server_host=bpipe_dp.bpipe_connect.get('host', None), app_name=bpipe_dp.bpipe_connect.get('app', None))
        asyncio.run(bpipe_dp.get_stream(symbols, bpipe_dp.timestream_adapter.write_bpipe_data,seconds))
