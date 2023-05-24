#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
// import * as cdk from '@aws-cdk/core';
import { EnvironmentStack } from '../lib/environment';
import { DatabaseStack } from '../lib/database';
import { BatchStack } from '../lib/batch';
import { LambdaStack } from '../lib/lambda';
import { AppConfigStack } from '../lib/appConfig';
import { SecretsStack } from '../lib/secrets';

import { AwsSolutionsChecks } from 'cdk-nag'
import { Aspects } from 'aws-cdk-lib';

const app = new cdk.App();
//Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));

const env = {
    // account: process.env.CDK_DEFAULT_ACCOUNT,
    // region: app.node.tryGetContext('us-west-2')
    region: 'us-west-2'
};

const envStack = new EnvironmentStack(app, 'EnvStack', {
    env: env
});
const dbStack = new DatabaseStack(app, 'DbStack', {
    env: env
});
const appConfigStack = new AppConfigStack(app, 'AppConfigStack', {
    env: env
});
const secretsStack = new SecretsStack(app, 'SecretsStack', {
    env: env,
    computePolicy: envStack.computePolicy
});
const batchStack = new BatchStack(app, 'BatchStack', {
    env: env,
    vpc: envStack.vpc,
    computePolicy: envStack.computePolicy
});
batchStack.addDependency(appConfigStack);
batchStack.addDependency(secretsStack);
const lambdaStack = new LambdaStack(app, 'LambdaStack', {
    env: env,
    portfoliosTable: dbStack.portfolioTable,
    portfolioSystemEventsTable: dbStack.systemEventsTable,
    computePolicy: envStack.computePolicy
});
lambdaStack.addDependency(appConfigStack);
lambdaStack.addDependency(secretsStack);


