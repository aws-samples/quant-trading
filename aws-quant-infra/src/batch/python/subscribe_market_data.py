import pyEX
print("import pyEX:",pyEX.__file__)
import sys
print("sys.path:",'\n'.join(sys.path))
from xbbg import blp
print("import xbbg.blp:",blp.__file__)

sys.path.append('/src/shared/python')
sys.path.append('/Users/blitvin/IdeaProjects/aws-quant-infra/src/shared/python')
sys.path.append('/var/task/shared/python')
sys.path.append('/src/shared/python/')
sys.path.append(('/home/ec2-user/environment/MvpPortfolioMonitoring-code-repo/aws-quant-infra'))
sys.path.append(('/home/ec2-user/environment/MvpPortfolioMonitoring-code-repo/aws-quant-infra/src/shared/python'))

import aws_quant_infra as aq_i
print(f"import aws_quant_infra is done!")
print(aq_i.__file__)
import aws_quant_risk as aq_r
print(f"import aws_quant_risk is done!")
print(aq_r.__file__)
import aws_quant_market_data as aq_md
print(f"import aws_quant_market_data is done!")
print(aq_md.__file__)

print (f'Number of arguments:{len(sys.argv)} arguments.')
print (f'Argument List:{str(sys.argv)}')
print (f'function call:{str(sys.argv[0])}')
print (f'config_env:{str(sys.argv[1])}')
print (f'symbols:{str(sys.argv[2])}')
if False:# for debugging
    import imp
    imp.reload(aq_md)

#aq_md.IEX_data_provider.iex_subscribe_main(str(sys.argv[1]),str(sys.argv[2]))
if False:
    #DEBUG
    import os
    os.environ["SSM_PREFIX"] = "Mvp"
    os.environ["AWS_REGION"] = "us-east-1"
    aq_md.MarketDataProvider.subscribe_main('dev','EURUSD,USDJPY')
else:
    aq_md.MarketDataProvider.subscribe_main(str(sys.argv[1]),str(sys.argv[2]),str(sys.argv[3]))
#aq_md.IEX_data_provider.iex_subscribe_main('dev','GS,AMZN')
