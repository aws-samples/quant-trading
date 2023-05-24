#!/usr/bin/env node
import * as cdk from '@aws-cdk/core';
import { CdkGrafanaStack } from '../lib/cdk-grafana-stack';

const app = new cdk.App();
new CdkGrafanaStack(app, 'CdkGrafanaStack');
