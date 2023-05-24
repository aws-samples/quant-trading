curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o Miniconda3-latest-Linux-x86_64.sh
chmod +x Miniconda3-latest-Linux-x86_64.sh
./Miniconda3-latest-Linux-x86_64.sh  -b
PATH=~/miniconda3/bin:${PATH}
# RUN ls -la
# RUN ls -la bin
# RUN conda init bash
# RUN exec bash
conda create --name bpipe python=3.8 -y
conda init bash
# ENV PATH=/root/miniconda3/envs/${PYTHON_ENVS}/bin:${PATH}
source activate bpipe
conda install -c conda-forge blpapi -y
pip install xbbg
pip install awswrangler
pip install sseclient
pip install pyEX

sudo yum install jq -y

cd ~/environment/MvpPortfolioMonitoring-code-repo/aws-quant-infra/deployment/cdk
#npm install
cdk deploy "*"
cd -

source activate bpipe
eval $(aws sts assume-role --role-arn ROLE_ARN_TO_ASSUME --role-session-name test | jq -r '.Credentials | "export AWS_ACCESS_KEY_ID=\(.AccessKeyId)\nexport AWS_SECRET_ACCESS_KEY=\(.SecretAccessKey)\nexport AWS_SESSION_TOKEN=\(.SessionToken)\n"')

#! /bin/bash
for state in SUBMITTED PENDING RUNNABLE STARTING RUNNING
do 
    for job in $(aws batch list-jobs --job-queue MvpPortfolioMonitoring_q_ec2 --job-status $state --output text --query jobSummaryList[*].[jobId])
    do 
        echo -ne "Stopping job $job in state $state\t"
        aws batch terminate-job --reason "Terminating job." --job-id $job && echo "Done." || echo "Failed."
    done
done

cd ~/environment/MvpPortfolioMonitoring-code-repo/aws-quant-infra/src/utils/  &&
python portfolio_generator.py --name test_ptf_50 --filename nyse-ticker-list.csv  --ticker-amount 50 &&
cd -

git config --global user.name $USER
git config --global user.email "email@company.com"