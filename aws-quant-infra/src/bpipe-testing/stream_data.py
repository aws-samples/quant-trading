import asyncio
from xbbg import blp
import bpipe

blp.connect(auth_method='app', server_host=bpipe.host, app_name=bpipe.app)

bpipe_info = [
    'LAST_PRICE'
    , 'open'
    , 'close'
    , 'high'
    , 'low'
    , 'PRICE_EARNINGS_RATIO_RT'
    , 'VOLUME'
]

bpipe_points=[]
count=0
# data is json
async def stream():
    async for data in blp.live(["AMZN US Equity"], flds=bpipe_info, info=bpipe_info):
    #async for data in blp.live(["AMZN US Equity"],info=['BID','ASK','LAST_PRICE']):
    #async for data in blp.live(["AMZN US Equity","IBM US Equity","EURUSD BGN Curncy"],info=['BID','ASK','LAST_PRICE']):
        bpipe_points.append(data)
        if count%10==0:
            print(bpipe_points)
            break

asyncio.run(stream())
