import * as cdk from '@aws-cdk/core';
import * as Grafana from '../lib/cdk-grafana-stack';
import '@aws-cdk/assert/jest';


test('Empty Stack', () => {
    const app = new cdk.App( { context: {
            'domainName': 'example.com',
            'hostedZoneId': 'IIDASEED',
            'zoneName': 'example.com'
        }});
    // WHEN
    const stack = new Grafana.CdkGrafanaStack(app, 'MyTestStack');

    // THEN
    expect(stack).toHaveResourceLike('AWS::ECS::Service');
});
