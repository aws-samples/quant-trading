// import * as cdk from '@aws-cdk/core';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

// import * as ec2 from '@aws-cdk/aws-ec2';
import { aws_ec2 as ec2 } from 'aws-cdk-lib';
// import { DockerImageAsset } from '@aws-cdk/aws-ecr-assets';
import { DockerImageAsset } from 'aws-cdk-lib/aws-ecr-assets';
// import * as batch from '@aws-cdk/aws-batch';
import { aws_batch as batch } from 'aws-cdk-lib';
import { SsmManager } from './shared/ssm-manager';
// import * as iam from '@aws-cdk/aws-iam';
import { aws_iam as iam } from 'aws-cdk-lib';
import * as path from 'path';
import { NagSuppressions } from 'cdk-nag';
interface BatchProps extends cdk.StackProps {
    vpc: ec2.IVpc;
    computePolicy: iam.ManagedPolicy;
}

export class BatchStack extends cdk.Stack {
    private ssm: SsmManager;
    private prefix: string;
    private projectId: string;

    private vpc: ec2.IVpc;
    private computePolicy: iam.ManagedPolicy;

    public dockerImage: DockerImageAsset;
    private computeEnvironments: batch.CfnComputeEnvironment[] = [];
    constructor(scope: Construct, id: string, props: BatchProps) {
        super(scope, id, props);
        const project = this.node.tryGetContext('project');
        this.prefix = this.node.tryGetContext('deployment_prefix');
        this.projectId = `${this.prefix}${project}`;
        this.ssm = new SsmManager(this, `${this.projectId}EnvSsmManager`);
        this.vpc = props.vpc;
        this.computePolicy = props.computePolicy;

        this.dockerImage = this.createDockerImage();
        this.createComputeEnvironments();
        this.createJobQueues();
        this.createJobDefinitions();
        NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-IAM4', reason: 'uses AWS managed role - nothing to do' }]);
        NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-IAM5', reason: 'uses AWS managed role - nothing to do' }]);
    }

    private createDockerImage(): DockerImageAsset {
        const image = new DockerImageAsset(this, `${this.projectId}BatchImage`, {
            directory: path.join(__dirname, '../../../src'),
            buildArgs: {
                SSM_PREFIX: this.prefix,
                AWS_REGION: this.region
            },
            file: 'batch/Dockerfile'
        });
        this.ssm.setParameterValue({
            value: image.imageUri,
            valueName: 'BatchImageUri'
        });
        return image;
    }

    private createComputeEnvironments() {
        const securityGroup = new ec2.SecurityGroup(this, `${this.projectId}BatchSecurityGroup`, {
            vpc: this.vpc,
            allowAllOutbound: true,
            description: `${this.projectId} Batch Security Group`,
            securityGroupName: `${this.projectId}BatchSecurityGroup`
        });
        const serviceRole = new iam.Role(this, `${this.projectId}BatchServiceRole`, {
            roleName: `${this.projectId}BatchServiceRole`,
            assumedBy: new iam.ServicePrincipal('batch.amazonaws.com'),
        })
        serviceRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSBatchServiceRole"));
        const instanceRole = new iam.Role(this, `${this.projectId}BatchInstanceRole`, {
            roleName: `${this.projectId}BatchInstanceRole`,
            assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
            managedPolicies: [
                iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonEC2ContainerServiceforEC2Role'),
                this.computePolicy
            ]
        });
        instanceRole.addToPolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: ['sts:AssumeRole'],
            resources: ['*']
        }));
        const instanceProfile = new iam.CfnInstanceProfile(this, `${this.projectId}BatchInstanceProfile`, {
            instanceProfileName: `${this.projectId}BatchInstanceProfile`,
            roles: [ instanceRole.roleName]
        });
        const customSubnet = this.node.tryGetContext('custom_subnet_id');
        const ec2Od = new batch.CfnComputeEnvironment(this, `${this.projectId}BatchComputeEc2OD`, {
            type: 'MANAGED',
            state: 'ENABLED',
            computeEnvironmentName: `${this.projectId}_ec2_od`,
            serviceRole: serviceRole.roleArn,
            computeResources: {
                minvCpus: 0,
                desiredvCpus: 0,
                maxvCpus: 128,
                instanceTypes: [
                    "optimal"
                ],
                type: "EC2",
                subnets: customSubnet !== undefined ? [ customSubnet ] : this.vpc.privateSubnets.map(x=>x.subnetId),
                allocationStrategy: 'BEST_FIT',
                securityGroupIds: [ securityGroup.securityGroupId ],
                instanceRole: instanceProfile.attrArn
            }
        });
        const ec2Spot = new batch.CfnComputeEnvironment(this, `${this.projectId}BatchComputeEc2Spot`, {
            type: 'MANAGED',
            state: 'ENABLED',
            computeEnvironmentName: `${this.projectId}_ec2_spot`,
            serviceRole: serviceRole.roleArn,
            computeResources: {
                minvCpus: 0,
                desiredvCpus: 0,
                maxvCpus: 128,
                bidPercentage: 100,
                instanceTypes: [
                    "optimal"
                ],
                type: "SPOT",
                subnets: customSubnet !== undefined ? [ customSubnet ] : this.vpc.privateSubnets.map(x=>x.subnetId),
                allocationStrategy: 'SPOT_CAPACITY_OPTIMIZED',
                securityGroupIds: [ securityGroup.securityGroupId ],
                instanceRole: instanceProfile.attrArn
            }
        });
        const fargate = new batch.CfnComputeEnvironment(this, `${this.projectId}BatchComputeFargate`, {
            type: 'MANAGED',
            state: 'ENABLED',
            computeEnvironmentName: `${this.projectId}_fargate`,
            serviceRole: serviceRole.roleArn,
            computeResources: {
                maxvCpus: 256,
                type: "FARGATE",
                subnets: customSubnet !== undefined ? [ customSubnet ] : this.vpc.privateSubnets.map(x=>x.subnetId),
                securityGroupIds: [ securityGroup.securityGroupId ],
                instanceRole: 'dummy-instance-role',
                instanceTypes: [ 'dummy-instance-type']
            }
        });

        fargate.addPropertyDeletionOverride('ComputeResources.InstanceRole');
        fargate.addPropertyDeletionOverride('ComputeResources.InstanceTypes');
        const fargateSpot = new batch.CfnComputeEnvironment(this, `${this.projectId}BatchComputeFargateSpot`, {
            type: 'MANAGED',
            state: 'ENABLED',
            computeEnvironmentName: `${this.projectId}_fargate_spot`,
            serviceRole: serviceRole.roleArn,
            computeResources: {
                maxvCpus: 256,
                type: "FARGATE_SPOT",
                subnets: customSubnet !== undefined ? [ customSubnet ] : this.vpc.privateSubnets.map(x=>x.subnetId),
                securityGroupIds: [ securityGroup.securityGroupId ],
                instanceRole: 'dummy-instance-role',
                instanceTypes: [ 'dummy-instance-type']
            }
        });
        fargateSpot.addPropertyDeletionOverride('ComputeResources.InstanceRole');
        fargateSpot.addPropertyDeletionOverride('ComputeResources.InstanceTypes');
        this.computeEnvironments.push(ec2Od, ec2Spot, fargate, fargateSpot);
        this.ssm.setParameterValue({
            value:  {
                'ec2_od': ec2Od.computeEnvironmentName,
                'ec2_spot': ec2Spot.computeEnvironmentName,
                'fargate_od': fargate.computeEnvironmentName,
                'fargate_spot': fargateSpot.computeEnvironmentName
            },
            valueName: 'BatchComputeEnvironments'
        });
    }
    private createJobQueues() {
        const qEc2 = new batch.CfnJobQueue(this, `${this.projectId}BatchEc2JobQueue`, {
            jobQueueName: `${this.projectId}_q_ec2`,
            priority: 1,
            state: 'ENABLED',
            computeEnvironmentOrder: [
                {
                    order: 1, 
                    computeEnvironment: this.computeEnvironments[0].computeEnvironmentName!
                },
                {
                    order: 2, 
                    computeEnvironment: this.computeEnvironments[1].computeEnvironmentName!
                }
            ]
        });
        qEc2.addDependsOn(this.computeEnvironments[0]);
        qEc2.addDependsOn(this.computeEnvironments[1]);
        const qFargate = new batch.CfnJobQueue(this, `${this.projectId}BatchFargateJobQueue`, {
            jobQueueName: `${this.projectId}_q_fargate`,
            priority: 1,
            state: 'ENABLED',
            computeEnvironmentOrder: [
                {
                    order: 1, 
                    computeEnvironment: this.computeEnvironments[2].computeEnvironmentName!
                },
                {
                    order: 2, 
                    computeEnvironment: this.computeEnvironments[3].computeEnvironmentName!
                }
            ]
        });
        qFargate.addDependsOn(this.computeEnvironments[2]);
        qFargate.addDependsOn(this.computeEnvironments[3]);
        this.ssm.setParameterValue({
            value: qEc2.jobQueueName!,
            valueName: 'BatchEc2JobQueueName'
        });
        this.ssm.setParameterValue({
            value: qFargate.jobQueueName!,
            valueName: 'BatchFargateJobQueueName'
        });
    }
    private createJobDefinitions() {
        //portfolio_tracker
        const portfolioTrackerJob = new batch.CfnJobDefinition(this, `${this.projectId}BatchPortfolioTrackerJobDef`, {
            jobDefinitionName: `${this.projectId}_portfolio_tracker`,
            type: 'Container',
            timeout: {
                attemptDurationSeconds: 600000
            },
            platformCapabilities: [
                'EC2'
            ],
            containerProperties: {
                command: ["/src/portfolio_tracker.py '4cc2ab26e6f7997a5d362bb1ce193005'"],
                vcpus: 2,
                memory: 8192,
                image: this.dockerImage.imageUri
            }
        });
        this.ssm.setParameterValue({
            value: portfolioTrackerJob.jobDefinitionName!,
            valueName: 'BatchPortfolioTrackerJobDef'
        });
        //get_market_data_test
        const getMarketData = new batch.CfnJobDefinition(this, `${this.projectId}BatchGetMarketDataJobDef`, {
            jobDefinitionName: `${this.projectId}_get_market_data`,
            type: 'Container',
            platformCapabilities: [
                'EC2'
            ],
            containerProperties: {
                command: ["/src/subscribe_market_data.py"],
                vcpus: 1,
                memory: 4096,
                image: this.dockerImage.imageUri
            }
        });
        this.ssm.setParameterValue({
            value: getMarketData.jobDefinitionName!,
            valueName: 'BatchGetMarketDataJobDef'
        });
        //test_batch_docker
        const testBatchDocker = new batch.CfnJobDefinition(this, `${this.projectId}BatchTestBatchDockerJobDef`, {
            jobDefinitionName: `${this.projectId}_test_docker`,
            type: 'Container',
            platformCapabilities: [
                'EC2'
            ],
            containerProperties: {
                command: ["/src/test_docker.py"],
                vcpus: 1,
                memory: 2048,
                image: this.dockerImage.imageUri
            }
        });
        this.ssm.setParameterValue({
            value: testBatchDocker.jobDefinitionName!,
            valueName: 'BatchTestBatchDockerJobDef'
        });
    }
}