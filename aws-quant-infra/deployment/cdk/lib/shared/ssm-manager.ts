// import * as cdk from '@aws-cdk/core';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { aws_iam as iam } from 'aws-cdk-lib';
import { aws_ssm as ssm } from 'aws-cdk-lib';
// import * as iam from '@aws-cdk/aws-iam';
// import * as ssm from '@aws-cdk/aws-ssm';

export interface setParameterValueProps {
    value: string | string[] | object;
    valueName: string;
    role?: iam.IRole
}

export interface getParameterValueProps {
    valueName: string
}

export class SsmManager extends Construct {
    private projectId: string;

    constructor(scope: Construct, id: string) {
        super(scope, id);
        const project = this.node.tryGetContext('project');
        const prefix = this.node.tryGetContext('deployment_prefix');
        this.projectId = `${prefix}-${project}`;
    }
    public setParameterValue(props: setParameterValueProps) {
        var value = props.value;
        const valueName = props.valueName;
        const role = props.role;
        var param: ssm.StringParameter;
        if ( Array.isArray(value) ) {
            const jsonValue = {
                values: value
            }
            value = JSON.stringify(jsonValue)
        }
        if ( typeof(value) === 'object'){
            value = JSON.stringify(value);
        }
        param = new ssm.StringParameter(this, `set-${valueName}-param`, {
            stringValue: value,
            parameterName: `${this.projectId}-${valueName}`,
            description: `${this.projectId} parameter`
        });    
        
        new cdk.CfnOutput(this, `${valueName}CfnOutput`, {
            value: value,
            exportName: valueName
        });
        if (role){
            param.grantRead(role);
        }
    }
    public getParameterValue(props: getParameterValueProps): string{
        const valueName = props.valueName;
        var value = ssm.StringParameter.fromStringParameterAttributes(this, `get-${valueName}-param`, {
            parameterName: `${this.projectId}-${valueName}`
        }).stringValue;

        // Need to convert if given a json string
        if (value.includes(':')){
            value = JSON.parse(value);
        }
        return value
    }
}