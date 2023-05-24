#!/bin/sh

npm install

#From the CDK folder
#Requirements: have JQ installed: yum install jq -y or apt install jq -y
aws lambda get-layer-version-by-arn  --arn arn:aws:lambda:us-east-2:728743619870:layer:AWS-AppConfig-Extension:77 | jq -r '.Content.Location' | xargs curl -o ../../src/lambda/extension.zip

cdk bootstrap

cdk diff --no-color &> changes.txt

cdk deploy "*" --outputs-file outputs.json

clone_url=$(cat outputs.json | jq 'with_entries( select(.key | contains("SDLCStack")))'[] | jq -r 'with_entries( select(.key | contains("RepoCloneUrl")))'[])

git config --global user.name "AwsQuantInitDeploy"
git config --global user.email ""

git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true

echo $clone_url