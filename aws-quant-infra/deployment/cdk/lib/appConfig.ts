// import * as cdk from '@aws-cdk/core';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { Stack, App } from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';
import {aws_appconfig as appconfig} from 'aws-cdk-lib';
// import * as appconfig from '@aws-cdk/aws-appconfig';
import * as appconfigs from '../../../src/config/portfolio_tracker_cfg.json';
import { SsmManager } from './shared/ssm-manager';

export class AppConfigStack extends cdk.Stack {
    private projectId: string;
    private project: string;

    public appConfig: appconfig.CfnApplication;

    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);
        
        this.project = this.node.tryGetContext('project');
        const prefix = this.node.tryGetContext('deployment_prefix');
        this.projectId = `${prefix}${this.project}`;

        this.appConfig = this.createAppConfig();
        NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-IAM4', reason: 'lorem ipsum' }]);
        NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-IAM5', reason: 'lorem ipsum' }]);
    }

    private createAppConfig(): appconfig.CfnApplication{
        const app = this.createApp();
        const env = this.createEnvironment(app);
        const profile = this.createConfigProfile(app);
        const hostedProfile = this.createHostedConfigProfile(app, profile);
        const deploymentStrat = this.createDeploymentStrategy();
        const deployment = this.createDeployment(app, profile, env, deploymentStrat, hostedProfile.ref);
        deployment.addDependsOn(hostedProfile);
        new SsmManager(this, `${this.projectId}AppConfigSsmManager`).setParameterValue({
            value: this.toJsonString({
                Application: app.name,
                Configuration: profile.name,
                [env.name]: hostedProfile.ref
            }),
            valueName: 'AppConfigDetails'
        });
        return app;
    }
    private createApp(): appconfig.CfnApplication {
        return new appconfig.CfnApplication(this, `${this.projectId}AppConfigApp`, {
            name: this.project,
            description: `${this.project} App configurations`
        });
    }
    private createEnvironment(app: appconfig.CfnApplication): appconfig.CfnEnvironment {
        const env = appconfigs.env;

        return new appconfig.CfnEnvironment(this, `${this.projectId}${env}`, {
            applicationId: app.ref,
            name: `${env}`,
            description: `${this.project} ${env} Environment`
        });
    }
    private createConfigProfile(app: appconfig.CfnApplication): appconfig.CfnConfigurationProfile {
        return new appconfig.CfnConfigurationProfile(this, `${this.projectId}ConfigProfile`, {
            applicationId: app.ref,
            name: `${this.project}ConfigProfile`,
            locationUri: 'hosted',
            description: `${this.project} configuration profile`
        });
    }
    private createHostedConfigProfile(app: appconfig.CfnApplication, configProfile: appconfig.CfnConfigurationProfile): appconfig.CfnHostedConfigurationVersion {
        return new appconfig.CfnHostedConfigurationVersion(this, `${this.projectId}HostedConfigProfile`, {
            applicationId: app.ref,
            configurationProfileId: configProfile.ref,
            contentType: 'application/json',
			content: this.toJsonString(appconfigs),
        });
    }
    private createDeploymentStrategy(): appconfig.CfnDeploymentStrategy {
        const env = appconfigs.env;

        return new appconfig.CfnDeploymentStrategy(this, `${this.projectId}DeploymentStrategy`, {
			name: 'Custom.AllAtOnce',
			deploymentDurationInMinutes: 0,
			growthFactor: 100,
			finalBakeTimeInMinutes: 0,
			replicateTo: 'NONE',
			growthType: 'LINEAR',
			description: `${this.project} ${env} configs deployment strategy - All at once deployment (i.e., immediate)`
		});
    }
    private createDeployment(app: appconfig.CfnApplication, configProfile: appconfig.CfnConfigurationProfile, configEnv: appconfig.CfnEnvironment, configDeploymentStrat: appconfig.CfnDeploymentStrategy, version: string): appconfig.CfnDeployment {
        return new appconfig.CfnDeployment(this, `${this.projectId}Deployment`, {
            applicationId: app.ref,
            configurationProfileId: configProfile.ref,
            configurationVersion: version,
            deploymentStrategyId: configDeploymentStrat.ref,
            environmentId: configEnv.ref,
        });
    }
}