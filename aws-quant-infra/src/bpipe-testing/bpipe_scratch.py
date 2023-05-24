import asyncio
import pandas as pd
import json
import datetime
from xbbg import blp
import awswrangler as wr

host="IP_ADDR"

app='APP_NAME'

port=8194

blp.connect(auth_method='app', server_host=host, app_name=app)

bpipe_info = [
     'OPEN'
    ,'BID'
    ,'ASK'
    ,'PRICE_OPEN_RT'
    ,'CLOSE'
    ,'HIGH'
    ,'LOW'
    ,'LAST_PRICE'
    ,'HIGH_LOCAL_SOURCE_RT'
    ,'TICKER'
    ,'BLOOMBERG_SEND_TIME_RT'
    ,'LAST_TRADE_PRICE_TIME_TODAY_RT'
    ,'CONTINUOUS_VOLUME_RT'
    ,'VOLUME'
    ,'EQY_PRIM_EXCH_SHRT'
    ,'TIME'
    ,'NAME'
]

measures=['TICKER','TIME','EQY_PRIM_EXCH_SHRT']

# data is json
ret=[]
count=0
market_view = {}


def write_marketview_to_ts():
    rr = []
    print
    for one_symbol in market_view.keys():
        mv= pd.DataFrame.from_dict([market_view.get(one_symbol)])
        mv['symbol']=one_symbol
        rr.append(wr.timestream.write(
                    df=mv,
                    database='test',
                    table='bpipe_test',
                    time_col="tick_time",
                    measure_col="OPEN",
                    dimensions_cols=["symbol"]
                ))
    return(rr)

async def sample_data():
    ret_pd = pd.DataFrame.from_dict(ret)
    print(ret_pd)
    write_marketview_to_ts()
    

def market_view_upsert(key):
    if key in market_view.keys():
        pass
    else:
        market_view[key]={}
    

def update_market_view(raw_bpipe_data):
    if "BLOOMBERG_SEND_TIME_RT" in raw_bpipe_data.keys():
         tick_time = datetime.datetime.combine(datetime.datetime.now().date(),raw_bpipe_data['BLOOMBERG_SEND_TIME_RT'])
    else:
        tick_time  =datetime.datetime.now()
    symbol = raw_bpipe_data.get('TICKER')
    field = raw_bpipe_data.get('FIELD')
    market_view_upsert(symbol)
    market_view.get(symbol)['tick_time']=tick_time
    market_view.get(symbol)[field]=raw_bpipe_data.get(field)

async def bad():
    raise Exception()
    
async def not_so_bad():
    try:
        raise Warning("custom warning")
    except:
        print(f"internal exc")
    
async def stream():
    options =[f"interval={7:.1f}"]
    #live_stream=blp.live(["QQQ US Equity"], flds=bpipe_info, info=bpipe_info)
    async for data in blp.live(["QQQ US Equity"], flds=bpipe_info, info=bpipe_info):
    #async for data in blp.live(["AMZN US Equity"],info=['BID','ASK','LAST_PRICE']):
    #async for data in blp.live(["AMZN US Equity","IBM US Equity","import asyncio
import pandas as pd
import json
import datetime
from xbbg import blp
import awswrangler as wr

host="HOST_ADDR"

app='APP_NAME'

port=8194

blp.connect(auth_method='app', server_host=host, app_name=app)

bpipe_info = [
     'OPEN'
    ,'BID'
    ,'ASK'
    ,'PRICE_OPEN_RT'
    ,'CLOSE'
    ,'HIGH'
    ,'LOW'
    ,'LAST_PRICE'
    ,'HIGH_LOCAL_SOURCE_RT'
    ,'TICKER'
    ,'BLOOMBERG_SEND_TIME_RT'
    ,'LAST_TRADE_PRICE_TIME_TODAY_RT'
    ,'CONTINUOUS_VOLUME_RT'
    ,'VOLUME'
    ,'EQY_PRIM_EXCH_SHRT'
    ,'TIME'
    ,'NAME'
]

measures=['TICKER','TIME','EQY_PRIM_EXCH_SHRT']

# data is json
ret=[]
count=0
market_view = {}


def write_marketview_to_ts():
    rr = []
    print
    for one_symbol in market_view.keys():
        mv= pd.DataFrame.from_dict([market_view.get(one_symbol)])
        mv['symbol']=one_symbol
        rr.append(wr.timestream.write(
                    df=mv,
                    database='test',
                    table='bpipe_test',
                    time_col="tick_time",
                    measure_col="OPEN",
                    dimensions_cols=["symbol"]
                ))
    return(rr)

async def sample_data():
    ret_pd = pd.DataFrame.from_dict(ret)
    print(ret_pd)
    write_marketview_to_ts()
    

def market_view_upsert(key):
    if key in market_view.keys():
        pass
    else:
        market_view[key]={}
    

def update_market_view(raw_bpipe_data):
    if "BLOOMBERG_SEND_TIME_RT" in raw_bpipe_data.keys():
         tick_time = datetime.datetime.combine(datetime.datetime.now().date(),raw_bpipe_data['BLOOMBERG_SEND_TIME_RT'])
    else:
        tick_time  =datetime.datetime.now()
    symbol = raw_bpipe_data.get('TICKER')
    field = raw_bpipe_data.get('FIELD')
    market_view_upsert(symbol)
    market_view.get(symbol)['tick_time']=tick_time
    market_view.get(symbol)[field]=raw_bpipe_data.get(field)

async def bad():
    raise Exception()
    
async def not_so_bad():
    try:
        raise Warning("custom warning")
    except:
        print(f"internal exc")
    
async def stream():
    options =[f"interval={7:.1f}"]
    #live_stream=blp.live(["QQQ US Equity"], flds=bpipe_info, info=bpipe_info)
    async for data in blp.live(["import asyncio
import pandas as pd
import json
import datetime
from xbbg import blp
import awswrangler as wr

host="HOST_ADDR"

app='APP_NAME'

port=8194

blp.connect(auth_method='app', server_host=host, app_name=app)

bpipe_info = [
     'OPEN'
    ,'BID'
    ,'ASK'
    ,'PRICE_OPEN_RT'
    ,'CLOSE'
    ,'HIGH'
    ,'LOW'
    ,'LAST_PRICE'
    ,'HIGH_LOCAL_SOURCE_RT'
    ,'TICKER'
    ,'BLOOMBERG_SEND_TIME_RT'
    ,'LAST_TRADE_PRICE_TIME_TODAY_RT'
    ,'CONTINUOUS_VOLUME_RT'
    ,'VOLUME'
    ,'EQY_PRIM_EXCH_SHRT'
    ,'TIME'
    ,'NAME'
]

measures=['TICKER','TIME','EQY_PRIM_EXCH_SHRT']

# data is json
ret=[]
count=0
market_view = {}


def write_marketview_to_ts():
    rr = []
    print
    for one_symbol in market_view.keys():
        mv= pd.DataFrame.from_dict([market_view.get(one_symbol)])
        mv['symbol']=one_symbol
        rr.append(wr.timestream.write(
                    df=mv,
                    database='test',
                    table='bpipe_test',
                    time_col="tick_time",
                    measure_col="OPEN",
                    dimensions_cols=["symbol"]
                ))
    return(rr)

async def sample_data():
    ret_pd = pd.DataFrame.from_dict(ret)
    print(ret_pd)
    write_marketview_to_ts()
    

def market_view_upsert(key):
    if key in market_view.keys():
        pass
    else:
        market_view[key]={}
    

def update_market_view(raw_bpipe_data):
    if "BLOOMBERG_SEND_TIME_RT" in raw_bpipe_data.keys():
         tick_time = datetime.datetime.combine(datetime.datetime.now().date(),raw_bpipe_data['BLOOMBERG_SEND_TIME_RT'])
    else:
        tick_time  =datetime.datetime.now()
    symbol = raw_bpipe_data.get('TICKER')
    field = raw_bpipe_data.get('FIELD')
    market_view_upsert(symbol)
    market_view.get(symbol)['tick_time']=tick_time
    market_view.get(symbol)[field]=raw_bpipe_data.get(field)

async def bad():
    raise Exception()
    
async def not_so_bad():
    try:
        raise Warning("custom warning")
    except:
        print(f"internal exc")
    
async def stream():
    options =[f"interval={10:.1f}"]
    #live_stream=blp.live(["QQQ US Equity"], flds=bpipe_info, info=bpipe_info)
    async for data in blp.live(["AMZN US Equity"], flds=bpipe_info, info=bpipe_info,options=options):
    #async for data in blp.live(["AMZN US Equity"],info=['BID','ASK','LAST_PRICE']):
    #async for data in blp.live(["AMZN US Equity","IBM US Equity","EURUSD BGN Curncy"],info=['BID','ASK','LAST_PRICE']):
        print(data)
        #ret.append(data)
        #update_market_view(data)
        #print(len(ret))
        #if len(ret)>0 and len(ret)%100==0:
        #    await sample_data()
        #    #ret=[]
        #    #break
try:
    asyncio.run(stream())
except Exception:
    print(f'EXC!!!:{Exception}')


try:
    asyncio.run(not_so_bad())
except Warning as warn:
    print(f'EXC!!!:{warn}')"], flds=bpipe_info, info=bpipe_info):
    #async for data in blp.live(["AMZN US Equity"],info=['BID','ASK','LAST_PRICE']):
    #async for data in blp.live(["AMZN US Equity","IBM US Equity","EURUSD BGN Curncy"],info=['BID','ASK','LAST_PRICE']):
        print(data)
        #ret.append(data)
        #update_market_view(data)
        #print(len(ret))
        #if len(ret)>0 and len(ret)%100==0:
        #    await sample_data()
        #    #ret=[]
        #    #break

try:
    asyncio.run(stream())
except Exception:
    print(f'EXC!!!:{Exception}')


try:
    asyncio.run(not_so_bad())
except Warning as warn:
    print(f'EXC!!!:{warn}')"],info=['BID','ASK','LAST_PRICE']):
        print(data)
        #ret.append(data)
        #update_market_view(data)
        #print(len(ret))
        #if len(ret)>0 and len(ret)%100==0:
        #    await sample_data()
        #    #ret=[]
        #    #break

try:
    asyncio.run(stream())
except Exception:
    print(f'EXC!!!:{Exception}')


try:
    asyncio.run(not_so_bad())
except Warning as warn:
    print(f'EXC!!!:{warn}')