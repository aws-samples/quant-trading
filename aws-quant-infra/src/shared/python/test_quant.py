import unittest
from unittest.mock import MagicMock

from aws_quant_risk import PortfolioTracker

data = []

class TestPortfolioTracker(unittest.TestCase):
    
    def test_calc_portf_pnl(self):
        data_mock = MagicMock()
        # Pass data from the test and pre calculate the result to assert
        pf = PortfolioTracker(data_mock, data_mock, data_mock, data_mock)
        
        #self.assertEqual(pf.calc_portf_pnl(), 4)
        pass
        # pf.exec_monitor = {}
        # pf.config_dict_app = config_dict_app
        # pf.config_dict_env = aqi.replace_string_dict_keys(config_dict_env,app_prefix,'')
        # pf.app_prefix = app_prefix
        # pf.epoch = datetime.datetime.utcfromtimestamp(0)
        # pf.raw_hist_data = None
        # pf.raw_rt_data = None
        # pf.portfolio_priceline = None
        # pf.portfolio_update_ts = None
        # pf.portfolio_alert = {}
        # pf.dynamodb = boto3.resource('dynamodb')
        # pf.portfolio_table = pf.config_dict_env.get('PortfolioMonitoring-PortfoliosTable')
        # pf.dynamodb_table = pf.dynamodb.Table(pf.portfolio_table )
        # pf.marketdata_source = boto3.client('timestream-query')
        # pf.marketdata_source_paginator = pf.marketdata_source.get_paginator('query')
        # pf.marketdata_source_price_field = 'measure_value::double'
        # pf.price_metric = 'latestPrice'
        # pf.timestream_tables = aqi.try_get_catch_dict(pf.config_dict_env, 'PortfolioMonitoring-TimestreamTables')
        # pf.marketdata_source_db = aqi.try_get_catch_dict(pf.config_dict_env, 'PortfolioMonitoring-TimestreamDb') # TODO get from parameter store
        # pf.marketdata_source_table = aqi.try_get_catch_dict(pf.timestream_tables, 'market_data_table')
        # pf.portfolio_target_table = aqi.try_get_catch_dict(pf.timestream_tables, 'portfolio_table')
        # pf.marketdata_source_query = \
        #     f"SELECT distinct time,symbol,latestUpdate,measure_value::double  \
        #     FROM {pf.marketdata_source_db}.{pf.marketdata_source_table}\
        #     where measure_name='{pf.price_metric}'\
        #     and latestUpdate >= '%s'  and latestUpdate != 'None' and symbol in (%s)\
        #         order by time desc"  # TODO: get database name and table name from parameter store
    
        # pf.portfolio_latest_ts_query = \
        #     f"select max(latestUpdate) latestUpdate from \
        #     (SELECT max(latestUpdate) latestUpdate FROM {pf.marketdata_source_db}.{pf.portfolio_target_table} \
        #     where portf_id = '{portfolio_id}' and latestUpdate != 'None' \
        #     union \
        #     SELECT ago(1h) latestUpdate ) t"  # TODO: get database name and table name from parameter store
        # pf.marketdata_source_schema = None
        # pf.marketdata_target = boto3.client(
        #     'timestream-write')  # ,config=Config(read_timeout=20, max_pool_connections=5000, retries={'max_attempts': 10}))
    
        # pf.portfolio = pf.__portfolio(portfolio_id)
        # pf.portfolio_pd = pf.__portfolio_pd()
        # pf.exception_threshold = 20
        # pf.current_exception_count = 0
    
    if __name__ == '__main__':
        unittest.main()