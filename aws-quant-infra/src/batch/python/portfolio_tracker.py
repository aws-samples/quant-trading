import pyEX
print("import pyEX:",pyEX.__file__)
import binance
print("import pyEX:",binance.__file__)
import sys
print("sys.path:",'\n'.join(sys.path))

sys.path.append('/src/shared/python')
sys.path.append('/Users/samfarbe/Documents/SA/Initiatives/AWSQuant/aws-quant-infra/src/shared/python')

sys.path.append('/src/shared/python/')
sys.path.append(('/home/ec2-user/environment/MvpPortfolioMonitoring-code-repo/aws-quant-infra'))
sys.path.append(('/home/ec2-user/environment/MvpPortfolioMonitoring-code-repo/aws-quant-infra/src/shared/python'))

import aws_quant_infra as aq_i
print(f"import aws_quant_infra is done!")
print(aq_i.__file__)
import aws_quant_risk as aq_r
print(f"import aws_quant_risk is done!")
print(aq_r.__file__)

import sys
print (f'Number of arguments:{len(sys.argv)} arguments.')
print (f'Argument List:{str(sys.argv)}')
print (f'function call:{str(sys.argv[0])}')
print (f'config environment:{str(sys.argv[1])}')
print (f'portfolio id:{str(sys.argv[2])}')
# TODO: think through unified logging, print and combing through logs is NOT the right thing to-do. since everything is one giant distributed dependency, Neptune DB seems the right thing to do???

if False:
    #DEBUG
    import os
    os.environ["SSM_PREFIX"] = "Mvp"
    os.environ["AWS_REGION"] = "us-east-1"
    aq_r.PortfolioTracker.portfolio_tracker_main("dev",'7af1fa7c6b01edd3826c880082270775')
else:
    aq_r.PortfolioTracker.portfolio_tracker_main(sys.argv[1],sys.argv[2])


