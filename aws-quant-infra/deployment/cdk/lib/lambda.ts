// import * as cdk from '@aws-cdk/core';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { SsmManager } from './shared/ssm-manager';
// import * as iam from '@aws-cdk/aws-iam';
import { aws_iam as iam } from 'aws-cdk-lib';
// import * as dynamodb from '@aws-cdk/aws-dynamodb';
import { aws_dynamodb as dynamodb } from 'aws-cdk-lib';

// import * as events from '@aws-cdk/aws-events';
import { aws_events as events } from 'aws-cdk-lib';

import * as targets from 'aws-cdk-lib/aws-events-targets';
// import * as lambda from '@aws-cdk/aws-lambda';
import { aws_lambda as lambda } from 'aws-cdk-lib';

import * as path from 'path';
import { DynamoEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
// import { DockerImageAsset } from '@aws-cdk/aws-ecr-assets';
import { DockerImageAsset } from 'aws-cdk-lib/aws-ecr-assets';
import { NagSuppressions } from 'cdk-nag';

interface LambdaProps extends cdk.StackProps {
    portfoliosTable: dynamodb.ITable;
    portfolioSystemEventsTable: dynamodb.ITable;
    computePolicy: iam.ManagedPolicy;
}

export class LambdaStack extends cdk.Stack {
    private ssm: SsmManager;
    private prefix: string;
    private projectId: string;

    private portfoliosTable: dynamodb.ITable;
    private portfolioSystemEventsTable: dynamodb.ITable;
    private computePolicy: iam.ManagedPolicy;

    private tradingEODEventRule: events.Rule;
    private tradingSODEventRule: events.Rule;
    private intradayEventRule: events.Rule;
    private intradayCloseEventRule: events.Rule;

    private dockerPath = path.join(__dirname, '../../../src');
    public dockerImage: DockerImageAsset;
    private dockerImageTag: string;

    private lambdaRole: iam.Role;

    /**
     * // TODO: comment dispose
     * handler config should be defined once and then just reused vs. hardcoded
     */
    private SOD_RULE_PROPS = {
        event: events.RuleTargetInput.fromObject({
            account: events.EventField.fromPath('$.account'),
            region: events.EventField.fromPath('$.region'),
            detail: {
                event_type:"SOD",
                handler:{'Configuration': 'PortfolioMonitoringConfigProfile',
                    'Environment': 'dev',
                    'Application': 'PortfolioMonitoring'}
            }
        })
    };
    private EOD_RULE_PROPS = {
        event: events.RuleTargetInput.fromObject({
            account: events.EventField.fromPath('$.account'),
            region: events.EventField.fromPath('$.region'),
            detail: {
                event_type:"EOD",
                handler:{'Configuration': 'PortfolioMonitoringConfigProfile',
                    'Environment': 'dev',
                    'Application': 'PortfolioMonitoring'}
            }
        })
    };
    private INTRADAY_RULE_PROPS = {
        event: events.RuleTargetInput.fromObject({
            account: events.EventField.fromPath('$.account'),
            region: events.EventField.fromPath('$.region'),
            detail: {
                event_type:"INTRADAY",
                handler:{'Configuration': 'PortfolioMonitoringConfigProfile',
                    'Environment': 'dev',
                    'Application': 'PortfolioMonitoring'}
            }
        })
    };
    private INTRADAY_CLOSE_RULE_PROPS = {
        event: events.RuleTargetInput.fromObject({
            account: events.EventField.fromPath('$.account'),
            region: events.EventField.fromPath('$.region'),
            detail: {
                event_type:"INTRADAYCLOSE",
                handler:{'Configuration': 'PortfolioMonitoringConfigProfile',
                    'Environment': 'dev',
                    'Application': 'PortfolioMonitoring'}
            }
        })
    };

    constructor(scope: Construct, id: string, props: LambdaProps) {
        super(scope, id, props);
        const project = this.node.tryGetContext('project');
        this.prefix = this.node.tryGetContext('deployment_prefix');
        this.projectId = `${this.prefix}${project}`;
        this.ssm = new SsmManager(this, `${this.projectId}EnvSsmManager`);
        this.portfoliosTable = props.portfoliosTable;
        this.portfolioSystemEventsTable = props.portfolioSystemEventsTable;
        this.computePolicy = props.computePolicy;

        this.createEvents();
        this.dockerImage = this.createDockerImage();
        this.lambdaRole = this.createLambaRole();
        this.tradingStartStopFunction();
        this.portfolioUpdateFunction();
        this.systemEventsFunction();
        this.testDockerFunction();
        this.intradayMomentumFunction();
        this.intradayCloseFunction();
        NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-IAM4', reason: 'uses AWS managed role - nothing to do' }]);
        NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-IAM5', reason: 'uses AWS managed role - nothing to do' }]);
    }
    

    private createEvents() {
        this.tradingEODEventRule = new events.Rule(this, `${this.projectId}TradingEODRule`, {
            ruleName: `trading_EOD`,
            description: 'trading_EOD_cron(05 20 * * ? *)',
            enabled: true,
            schedule: events.Schedule.expression('cron(05 20 * * ? *)'),
        });
        this.ssm.setParameterValue({
            value: this.tradingEODEventRule.ruleName,
            valueName: 'TradingEODEventRule'
        });
        this.tradingSODEventRule = new events.Rule(this, `${this.projectId}TradingSODRule`, {
            ruleName: `trading_SOD`,
            description: 'trading_SOD_cron(25 13 * * ? *)',
            enabled: true,
            schedule: events.Schedule.expression('cron(25 13 * * ? *)'),
        });
        this.ssm.setParameterValue({
            value: this.tradingSODEventRule.ruleName,
            valueName: 'TradingSODEventRule'
        });
        this.intradayEventRule = new events.Rule(this, `${this.projectId}intradayRule`, {
            ruleName: `IntradayMomentum`,
            description: 'intraday_cron(00 14 ? * MON-FRI *)',
            enabled: true,
            schedule: events.Schedule.expression('cron(00 14 ? * MON-FRI *)'),
        });
        this.ssm.setParameterValue({
            value: this.intradayEventRule.ruleName,
            valueName: 'intradayEventRule'
        });
        this.intradayCloseEventRule = new events.Rule(this, `${this.projectId}intradayCloseRule`, {
            ruleName: `IntradayMomentumClose`,
            description: 'intraday_close_cron(00 20 ? * MON-FRI *)',
            enabled: true,
            schedule: events.Schedule.expression('cron(00 20 ? * MON-FRI *)'),
        });
        this.ssm.setParameterValue({
            value: this.intradayCloseEventRule.ruleName,
            valueName: 'intradayCloseEventRule'
        });
    }

    private createLambaRole(): iam.Role {
        const role = new iam.Role(this, `${this.projectId}LambaRole`, {
            assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
            roleName: `${this.projectId}LambaRole`,
            managedPolicies: [
                this.computePolicy,
                iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
            ]
        });
        this.ssm.setParameterValue({
            value: role.roleName,
            valueName: 'LambdaRoleName'
        });
        return role;
    }

    private createDockerImage(): DockerImageAsset {
        const image = new DockerImageAsset(this, `${this.projectId}LambdaImage`, {
            directory: path.join(this.dockerPath),
            buildArgs: {
                SSM_PREFIX: this.prefix,
                AWS_REGION: this.region
            },
            file: 'lambda/Dockerfile'
        });
        this.ssm.setParameterValue({
            value: image.imageUri,
            valueName: 'LambdaImageUri'
        });
        this.dockerImageTag = image.assetHash;
        return image;
    }

    private tradingStartStopFunction() {
        const lambdaFunction = new lambda.DockerImageFunction(this, `${this.projectId}TradingStartStopLambda`, {
            functionName: `${this.projectId}_trading_start_stop`,
            code: lambda.DockerImageCode.fromEcr(this.dockerImage.repository, {
                cmd: [ '/var/task/schedule_listener/lambda_function.lambda_handler' ],
                tag: this.dockerImageTag
            }),
            role: this.lambdaRole,
            memorySize: 128,
            timeout: cdk.Duration.minutes(15)
        });
        this.tradingEODEventRule.addTarget(new targets.LambdaFunction(lambdaFunction, this.EOD_RULE_PROPS));
        this.tradingSODEventRule.addTarget(new targets.LambdaFunction(lambdaFunction, this.SOD_RULE_PROPS));
        this.ssm.setParameterValue({
            value: lambdaFunction.functionName,
            valueName: 'TradingStartStopLambdaName'
        });
    
    }
    private portfolioUpdateFunction() {
        const lambdaFunction = new lambda.DockerImageFunction(this, `${this.projectId}PortfolioUpdateLambda`, {
            functionName: `${this.projectId}_portfolio_update`,
            code: lambda.DockerImageCode.fromEcr(this.dockerImage.repository, {
                cmd: [ '/var/task/handle_portfolio_update/lambda_function.lambda_handler' ],
                tag: this.dockerImageTag
            }),
            role: this.lambdaRole,
            memorySize: 128,
            timeout: cdk.Duration.minutes(15)
        });
        lambdaFunction.addEventSource(new DynamoEventSource(this.portfoliosTable, {
            startingPosition: lambda.StartingPosition.TRIM_HORIZON,
            batchSize: 1,
            bisectBatchOnError: false,
            enabled: true,
            retryAttempts: 0
        }));
        this.ssm.setParameterValue({
            value: lambdaFunction.functionName,
            valueName: 'PortfolioUpdateLambdaName'
        });
  
    }
    private intradayMomentumFunction() {
        const lambdaFunction = new lambda.DockerImageFunction(this, `${this.projectId}IntradayMomentumLambda`, {
            functionName: `${this.projectId}_intraday_momentum`,
            code: lambda.DockerImageCode.fromEcr(this.dockerImage.repository, {
                cmd: [ '/var/task/intraday_momentum/lambda_function.lambda_handler' ],
                tag: this.dockerImageTag
            }),
            role: this.lambdaRole,
            memorySize: 128,
            timeout: cdk.Duration.minutes(15)
        });
        this.intradayEventRule.addTarget(new targets.LambdaFunction(lambdaFunction, this.INTRADAY_RULE_PROPS));
        this.ssm.setParameterValue({
            value: lambdaFunction.functionName,
            valueName: 'IntradayMomentumLambdaName'
        });
    
    }
    private intradayCloseFunction() {
        const lambdaFunction = new lambda.DockerImageFunction(this, `${this.projectId}IntradayCloseLambda`, {
            functionName: `${this.projectId}_intraday_close`,
            code: lambda.DockerImageCode.fromEcr(this.dockerImage.repository, {
                cmd: [ '/var/task/intraday_close/lambda_function.lambda_handler' ],
                tag: this.dockerImageTag
            }),
            role: this.lambdaRole,
            memorySize: 128,
            timeout: cdk.Duration.minutes(15)
        });
        this.intradayCloseEventRule.addTarget(new targets.LambdaFunction(lambdaFunction, this.INTRADAY_CLOSE_RULE_PROPS));
        this.ssm.setParameterValue({
            value: lambdaFunction.functionName,
            valueName: 'IntradayCloseLambdaName'
        });
    
    }
    private systemEventsFunction() {
        const lambdaFunction = new lambda.DockerImageFunction(this, `${this.projectId}PortfolioSystemEventsLambda`, {
            functionName: `${this.projectId}_system_events_handler`,
            code: lambda.DockerImageCode.fromEcr(this.dockerImage.repository, {
                cmd: [ '/var/task/system_event_listener/lambda_function.lambda_handler' ],
                tag: this.dockerImageTag
            }),
            role: this.lambdaRole,
            memorySize: 128,
            timeout: cdk.Duration.minutes(15)
        });
        lambdaFunction.addEventSource(new DynamoEventSource(this.portfolioSystemEventsTable, {
            startingPosition: lambda.StartingPosition.TRIM_HORIZON,
            batchSize: 1,
            bisectBatchOnError: false,
            enabled: true,
            retryAttempts: 0

        }));
        this.ssm.setParameterValue({
            value: lambdaFunction.functionName,
            valueName: 'SystemEventsLambdaName'
        });

    }
    private testDockerFunction() {
        const lambdaFunction = new lambda.DockerImageFunction(this, `${this.projectId}TestDockerLambda`, {
            functionName: `${this.projectId}_test_docker_handler`,
            code: lambda.DockerImageCode.fromEcr(this.dockerImage.repository, {
                cmd: [ '/var/task/test_custom_layer/lambda_function.lambda_handler' ],
                tag: this.dockerImageTag
            }),
            role: this.lambdaRole,
            memorySize: 128,
            timeout: cdk.Duration.minutes(15)
        });
        lambdaFunction.addEventSource(new DynamoEventSource(this.portfolioSystemEventsTable, {
            startingPosition: lambda.StartingPosition.TRIM_HORIZON,
            batchSize: 1,
            bisectBatchOnError: false,
            enabled: true,
            retryAttempts: 0

        }));
        lambdaFunction.addEventSource(new DynamoEventSource(this.portfoliosTable, {
            startingPosition: lambda.StartingPosition.TRIM_HORIZON,
            batchSize: 1,
            bisectBatchOnError: false,
            enabled: true,
            retryAttempts: 0

        }));
        this.tradingEODEventRule.addTarget(new targets.LambdaFunction(lambdaFunction, this.EOD_RULE_PROPS));
        this.tradingSODEventRule.addTarget(new targets.LambdaFunction(lambdaFunction, this.SOD_RULE_PROPS));
        this.ssm.setParameterValue({
            value: lambdaFunction.functionName,
            valueName: 'TestDockerLambdaName'
        });
        
    }
}