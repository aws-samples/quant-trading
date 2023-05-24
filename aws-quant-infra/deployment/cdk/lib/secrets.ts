// import * as cdk from '@aws-cdk/core';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

import { SsmManager } from './shared/ssm-manager';
// import * as iam from '@aws-cdk/aws-iam';
import { aws_iam as iam } from 'aws-cdk-lib';
import { aws_secretsmanager as secretsmanager } from 'aws-cdk-lib';
// import * as secretsmanager from '@aws-cdk/aws-secretsmanager';
import * as appconfigs from '../../../src/config/portfolio_tracker_cfg.json';
import { NagSuppressions } from 'cdk-nag';
interface SecretsProps extends cdk.StackProps {
    computePolicy: iam.ManagedPolicy;
}

export class SecretsStack extends cdk.Stack {
    private ssm: SsmManager;
    private prefix: string;
    private projectId: string;

    private computePolicy: iam.ManagedPolicy;
    constructor(scope: Construct, id: string, props: SecretsProps) {
        super(scope, id, props);
        const project = this.node.tryGetContext('project');
        this.prefix = this.node.tryGetContext('deployment_prefix');
        this.projectId = `${this.prefix}${project}`;
        this.ssm = new SsmManager(this, `${this.projectId}EnvSsmManager`);

        this.computePolicy = props.computePolicy;

        this.createSecrets();
    }

    private createSecrets() {
        const secretNames = appconfigs.secrets;
        secretNames.forEach((name) => {
            const secret = new secretsmanager.Secret(this, `${name}Secret`, {
                // secretName: `${this.projectId}-${name}`
                secretName: `${name}`
            });
            // this.computePolicy.addStatements(
            //     new iam.PolicyStatement({
            //         effect: iam.Effect.ALLOW,
            //         actions:
            //     })
            // )
        });
        this.ssm.setParameterValue({
            value: secretNames,
            valueName: 'SecretNames'
        });
        NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-IAM4', reason: 'secret manager is used to keep 3rd party passwords that have its own rotation schedule "invisioble" to this solution' }]);
        NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-IAM5', reason: 'secret manager is used to keep 3rd party passwords that have its own rotation schedule "invisioble" to this solution' }]);
    }
}