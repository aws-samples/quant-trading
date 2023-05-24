// import * as cdk from '@aws-cdk/core';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

import { SsmManager } from './shared/ssm-manager';
// import * as ec2 from '@aws-cdk/aws-ec2';
import { aws_ec2 as ec2 } from 'aws-cdk-lib';
// import * as ecr from '@aws-cdk/aws-ecr';
import { aws_ecr as ecr } from 'aws-cdk-lib';
import { aws_codecommit as codeCommit } from 'aws-cdk-lib';
// import * as codeCommit from '@aws-cdk/aws-codecommit';
// import * as iam from '@aws-cdk/aws-iam';
import { aws_iam as iam } from 'aws-cdk-lib';
// import * as lambda from '@aws-cdk/aws-lambda';
import { aws_lambda as lambda } from 'aws-cdk-lib';
// import { PythonFunction } from "@aws-cdk/aws-lambda-python";
import { PythonFunction } from '@aws-cdk/aws-lambda-python-alpha';
// import { AwsCliLayer } from '@aws-cdk/lambda-layer-awscli'
import { AwsCliLayer } from 'aws-cdk-lib/lambda-layer-awscli';
// import * as cr from '@aws-cdk/custom-resources';
import * as cr from 'aws-cdk-lib/custom-resources';
// import * as logs from '@aws-cdk/aws-logs';
import { aws_logs as logs } from 'aws-cdk-lib';
import * as path from 'path';
import { PipelineStack } from './pipeline';
import { NagSuppressions } from 'cdk-nag';

export class EnvironmentStack extends cdk.Stack {
  private ssm: SsmManager;
  private projectId: string;
  private project: string;
  private prefix: string;

  public readonly vpc: ec2.IVpc;
  public readonly codeRepo: codeCommit.Repository;
  public readonly repo: ecr.IRepository;
  public readonly computePolicy: iam.ManagedPolicy;

  // constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    this.project = this.node.tryGetContext('project');
    this.prefix = this.node.tryGetContext('deployment_prefix');
    this.projectId = `${this.prefix}${this.project}`;
    this.ssm = new SsmManager(this, `${this.projectId}EnvSsmManager`);

    this.vpc = this.createVpc();
    this.computePolicy = this.createComputePolicy();
    this.codeRepo = this.createCodeCommit();
    
    NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-IAM4', reason: 'uses AWS managed role - nothing to do' }]);
    NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-IAM5', reason: 'uses AWS managed role - nothing to do' }]);
    NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-CB3', reason: 'uses AWS managed role - nothing to do' }]);
    NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-KMS5', reason: 'uses AWS managed role - nothing to do' }]);
    NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-S1', reason: 'uses AWS managed role - nothing to do' }]);
    
    
    new PipelineStack(this, 'SdlcStack', {
      codecommitRepo: this.codeRepo
    });
  }

  private createVpc() {
    const vpc_id = this.node.tryGetContext('custom_vpc_id');
    const subnet_id = this.node.tryGetContext('custom_subnet_id');
    var vpc;
    if (vpc_id !== undefined){
      vpc = ec2.Vpc.fromLookup(this, `${this.projectId}Vpc` , {
        isDefault: false,
        vpcId: vpc_id
      });
    } 
    else {
      const cidr = this.node.tryGetContext('cidr_range');
      const cidrMask = this.node.tryGetContext('cidr_subnet_mask');
      vpc = new ec2.Vpc(this, `${this.projectId}Vpc`, {
        maxAzs: 2,
        cidr: cidr,
        subnetConfiguration: [
          {
            name: `${this.projectId}-public`,
            subnetType: ec2.SubnetType.PUBLIC,
            cidrMask: cidrMask
          },
          {
            name: `${this.projectId}-private`,
            subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
            cidrMask: cidrMask
          }
        ],
        natGateways: 2,
        gatewayEndpoints: {
          S3: {
            service: ec2.GatewayVpcEndpointAwsService.S3
          },
          DynamoDB: {
            service: ec2.GatewayVpcEndpointAwsService.DYNAMODB
          } 
        }
      });
    }
    this.ssm.setParameterValue({
      value: vpc.vpcId,
      valueName: 'VpcId',
    });
    return vpc;
  }

  private createEcr() {
    const repo = new ecr.Repository(this, `${this.projectId}Ecr`, {
      repositoryName: `${this.projectId}-ecr-repo`.toLowerCase()
    });
    this.ssm.setParameterValue({
      value: repo.repositoryName,
      valueName: 'EcrRepoName'
    });
    return repo;
  }
  
  private createCodeCommit(): codeCommit.Repository {
    const repo = new codeCommit.Repository(this, `${this.projectId}CodeCommitRepo`, {
      repositoryName: `${this.projectId}-code-repo`,
      description: `CodeCommit repository for all ${this.projectId} code`
    });
    //TODO: Write bootstrap lambda function
    // this.bootstrapCodeCommit(repo);
    this.ssm.setParameterValue({
      value: repo.repositoryName,
      valueName: 'CodecommitRepoName'
    });
    this.ssm.setParameterValue({
      value: repo.repositoryCloneUrlHttp,
      valueName: 'CodecommitRepoCloneUrl'
    });
    return repo; 
  }

  private bootstrapCodeCommit(repo: codeCommit.Repository) {
    const lambdaFunction = new lambda.DockerImageFunction(this, `${this.projectId}CodeCommitBootstrap`, {
      functionName: `${this.projectId}_codecommit_bootstrap`,
      code: lambda.DockerImageCode.fromImageAsset('../../../aws-quant-infra', {
        file: 'deployment/cdk/lib/shared/custom-resources/codecommit-bootstrap/Dockerfile'
      }),
      environment: {
        REPO_REGION: this.region,
        DEST_REPO: repo.repositoryName
      },
      timeout: cdk.Duration.minutes(15)
    });
    repo.grantPullPush(lambdaFunction.role!);
    const provider = new cr.Provider(this, `${this.projectId}CodeCommitBootstrapProvider`, {
      onEventHandler: lambdaFunction,
      logRetention: logs.RetentionDays.ONE_DAY
    });
    new cdk.CustomResource(this, `${this.projectId}CodeCommitBootstrapCR`, { serviceToken: provider.serviceToken });
  }

  private createComputePolicy() {
    const regionAccount = `${this.region}:${this.account}`;
    const resourcePrefix = `${this.prefix}*${this.project}`;
    const policyDocument = {
      "Version": "2012-10-17",
      "Statement": [
        // {
        //   "Effect": "Allow",
        //   "Action": [
        //     // Parameter store
        //     "ssm:DescribeParameters",
        //     "ssm:GetParameter",
        //     // Secrets Manager
        //     "secretsmanager:GetSecretValue",
        //     // TimeStream
        //     "timestream:*",
        //     // Batch
        //     "batch:*",
        //     // Events
        //     "events:*",
        //     // AppConfig
        //     "appconfig:*",
        //     // DynamoDb
        //     "dynamodb:*"
        //   ],
        //   "Resource": "*",
        // },
        // WIP scoping down calls to resources created by cdk 
        {
          "Effect": "Allow",
          "Action": [ 
            "ssm:DescribeParameters",
            "events:*",
            "appconfig:*",
            "secretsmanager:GetSecretValue" // TODO integrate with python
          ],
          "Resource": "*"
        },
        {
          "Effect": "Allow",
          "Action": [ 
            "ssm:GetParameter",
            "ssm:PutParameter"
          ],
          "Resource": `arn:aws:ssm:${regionAccount}:parameter/${resourcePrefix}*`
        },
        // {
        //   "Effect": "Allow",
        //   "Action": [ 
        //     "secretsmanager:GetSecretValue"
        //   ],
        //   "Resource": `arn:aws:secretsmanager:${regionAccount}:secret:${resourcePrefix}*`
        // },
        {
          "Effect": "Allow",
          "Action": [ 
            "timestream:*"
          ],
          "Resource": `arn:aws:timestream:${regionAccount}:database/${resourcePrefix}*`
        },
        {
          "Effect": "Allow",
          "Action": [
            "timestream:DescribeEndpoints",
            "timestream:SelectValues",
            "timestream:CancelQuery"
          ],
          "Resource": "*"
        },
        {
          "Effect": "Allow",
          "Action": [ 
            "batch:CancelJob",
            "batch:SubmitJob",
          ],
          "Resource": [
            `arn:aws:batch:${regionAccount}:job-definition/${resourcePrefix}*`,
            `arn:aws:batch:${regionAccount}:job-queue/${resourcePrefix}*`
          ]
        },
        {
          "Effect": "Allow",
          "Action": [
            "batch:ListJobs",
            "batch:TerminateJob",
          ],
          "Resource": "*"
        },
        {
          "Effect": "Allow",
          "Action": [ 
            "dynamodb:*"
          ],
          "Resource": `arn:aws:dynamodb:${regionAccount}:table/${resourcePrefix}*`
        }
      ]
    };
    const policy = new iam.ManagedPolicy(this, `${this.projectId}ComputePolicy`, {
      managedPolicyName: `${this.projectId}ComputePolicy`,
      description: `Policy attached to ${this.projectId} compute resources`,
      document: iam.PolicyDocument.fromJson(policyDocument)
    });
    this.ssm.setParameterValue({
      value: policy.managedPolicyName,
      valueName: 'ComputeIamPolicyName'
    });
    return policy;
  }
  //TODO: Needs to be scoped to least privilege - use ml_infra as baseline for now
  private createIamRoles() {
    const batchRole = new iam.Role(this, `${this.projectId}BatchRole`, {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com')
    });
  }
}
