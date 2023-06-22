
#!/bin/bash


current_region=`aws configure get region`
declare -A arn_region

arn_region["us-east-1"]="arn:aws:lambda:us-east-1:027255383542:layer:AWS-AppConfig-Extension:110"
arn_region["us-east-2"]="arn:aws:lambda:us-east-2:728743619870:layer:AWS-AppConfig-Extension:79"
arn_region["us-west-1"]="arn:aws:lambda:us-west-1:958113053741:layer:AWS-AppConfig-Extension:121"
arn_region["us-west-2"]="arn:aws:lambda:us-west-2:359756378197:layer:AWS-AppConfig-Extension:143"
arn_region["ca-central-1"]="arn:aws:lambda:ca-central-1:039592058896:layer:AWS-AppConfig-Extension:79"
arn_region["eu-central-1"]="arn:aws:lambda:eu-central-1:066940009817:layer:AWS-AppConfig-Extension:91"
arn_region["eu-central-2"]="arn:aws:lambda:eu-central-2:758369105281:layer:AWS-AppConfig-Extension:29"
arn_region["eu-west-1"]="arn:aws:lambda:eu-west-1:434848589818:layer:AWS-AppConfig-Extension:108"
arn_region["eu-west-2"]="arn:aws:lambda:eu-west-2:282860088358:layer:AWS-AppConfig-Extension:79"
arn_region["eu-west-3"]="arn:aws:lambda:eu-west-3:493207061005:layer:AWS-AppConfig-Extension:80"
arn_region["eu-north-1"]="arn:aws:lambda:eu-north-1:646970417810:layer:AWS-AppConfig-Extension:139"
arn_region["eu-south-1"]="arn:aws:lambda:eu-south-1:203683718741:layer:AWS-AppConfig-Extension:71"
arn_region["eu-south-2"]="arn:aws:lambda:eu-south-2:586093569114:layer:AWS-AppConfig-Extension:26"
arn_region["cn-north-1"]="arn:aws-cn:lambda:cn-north-1:615057806174:layer:AWS-AppConfig-Extension:66"
arn_region["cn-northwest-1"]="arn:aws-cn:lambda:cn-northwest-1:615084187847:layer:AWS-AppConfig-Extension:66"
arn_region["ap-east-1"]="arn:aws:lambda:ap-east-1:630222743974:layer:AWS-AppConfig-Extension:71"
arn_region["ap-northeast-1"]="arn:aws:lambda:ap-northeast-1:980059726660:layer:AWS-AppConfig-Extension:82"
arn_region["ap-northeast-2"]="arn:aws:lambda:ap-northeast-2:826293736237:layer:AWS-AppConfig-Extension:91"
arn_region["ap-northeast-3"]="arn:aws:lambda:ap-northeast-3:706869817123:layer:AWS-AppConfig-Extension:84"
arn_region["ap-southeast-1"]="arn:aws:lambda:ap-southeast-1:421114256042:layer:AWS-AppConfig-Extension:89"
arn_region["ap-southeast-2"]="arn:aws:lambda:ap-southeast-2:080788657173:layer:AWS-AppConfig-Extension:91"
arn_region["ap-southeast-3"]="arn:aws:lambda:ap-southeast-3:418787028745:layer:AWS-AppConfig-Extension:60"
arn_region["ap-southeast-4"]="arn:aws:lambda:ap-southeast-4:307021474294:layer:AWS-AppConfig-Extension:2"
arn_region["ap-south-1"]="arn:aws:lambda:ap-south-1:554480029851:layer:AWS-AppConfig-Extension:92"
arn_region["ap-south-2"]=" arn:aws:lambda:ap-south-2:489524808438:layer:AWS-AppConfig-Extension:29"
arn_region["sa-east-1"]="arn:aws:lambda:sa-east-1:000010852771:layer:AWS-AppConfig-Extension:110"
arn_region["af-south-1"]="arn:aws:lambda:af-south-1:574348263942:layer:AWS-AppConfig-Extension:71"
arn_region["me-central-1"]="arn:aws:lambda:me-central-1:662846165436:layer:AWS-AppConfig-Extension:31"
arn_region["me-south-1"]="arn:aws:lambda:me-south-1:559955524753:layer:AWS-AppConfig-Extension:71"



echo "******** Checking if JQ is installed ********"
if ! command -v jq &> /dev/null
then
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "******** Installing JQ on linux ********"
        sudo yum install jq -y
   
    else
           echo "Please make sure you have installed the JQ binary and is on the path to continue"
           exit 1
    fi
fi
echo "******** Done ********"

echo "******** Downloading AppConfig for lambda ********"
aws lambda get-layer-version-by-arn  --arn ${arn_region[$current_region]} | jq -r '.Content.Location' | xargs curl -o aws-quant-infra/src/lambda/extension.zip
echo "******** Done ********"

echo "******** Installing NPM packages ********"
cd aws-quant-infra/deployment/cdk && npm install
echo "******** Done ********"


echo "******** CDK Bootstrap ********"
pwd
cdk bootstrap
echo "******** Done ********"

echo "******** CDK Checking drift ********"
pwd
cdk diff --no-color &> changes.txt
echo "******** Done ********"

echo "******** CDK Deploy ********"
cdk deploy "*" --outputs-file outputs.json --require-approval never
echo "******** Done ********"

echo "******** Checking if Terraform is installed ********"
#From the CDK folder
if ! command -v terraform &> /dev/null
then
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "******** Installing Terraform on linux ********"
        yum install terraform -y
    else
           echo "Please make sure you have installed the Terraform binary and is on the path to continue"
           exit 1
    fi
fi
echo "******** Done ********"

echo "******** Initializing terraform ********"
cd ../grafana 
terraform init 
terraform plan -var-file=grafana.tfvars -out=plan.tfx
terraform apply plan.tfx

echo "*****************************************************************"
echo "Deployment completed"
echo "*****************************************************************"
echo " ~ Next Steps ~ "
echo " Reset the password for user grafana_admin in the IAM Identity Center"
echo " Add Timestream data source to Grafana"
