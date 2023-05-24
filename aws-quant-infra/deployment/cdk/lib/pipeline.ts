// import * as cdk from '@aws-cdk/core';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { SsmManager } from './shared/ssm-manager';
// import * as codePipeline from '@aws-cdk/aws-codepipeline';
import { aws_codepipeline as codePipeline } from 'aws-cdk-lib';
// import * as codePipelineActions from '@aws-cdk/aws-codepipeline-actions';
import * as codePipelineActions from 'aws-cdk-lib/aws-codepipeline-actions';
// import * as codeCommit from '@aws-cdk/aws-codecommit';
import { aws_codecommit as codeCommit } from 'aws-cdk-lib';
// import * as codeBuild from '@aws-cdk/aws-codebuild';
import { aws_codebuild as codeBuild } from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';
interface PipelineProps extends cdk.NestedStackProps {
    codecommitRepo: codeCommit.Repository;
}

export class PipelineStack extends cdk.NestedStack {
    private ssm: SsmManager;
    private prefix: string;
    private project: string;
    private projectId: string;

    private codecommitRepo: codeCommit.Repository;

    constructor(scope: Construct, id: string, props: PipelineProps) {
        super(scope, id, props);
        this.project = this.node.tryGetContext('project');
        this.prefix = this.node.tryGetContext('deployment_prefix');
        this.projectId = `${this.prefix}${this.project}`;
        this.ssm = new SsmManager(this, `${this.projectId}PipelineSsmManager`);

        this.codecommitRepo = props.codecommitRepo;

        this.createPipeline();
        NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-IAM4', reason: 'lorem ipsum' }]);
        NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-IAM5', reason: 'lorem ipsum' }]);
    }

    private createPipeline() {
        const sourceOutput = new codePipeline.Artifact();
        const pipeline = new codePipeline.Pipeline(this, `${this.projectId}SdlcPipeline`, {
            pipelineName: `${this.projectId}SDLCPipeline`,
            stages: [
                this.createSourceStage('Source', sourceOutput),
                this.createImageBuildStage('Build', sourceOutput)
            ]
        });
        this.ssm.setParameterValue({
            value: pipeline.pipelineName,
            valueName: 'SDLCPipeline'
        });
    }
    private createSourceStage(stageName: string, output: codePipeline.Artifact): codePipeline.StageProps {
        const codeCommitAction = new codePipelineActions.CodeCommitSourceAction({
            actionName: 'CodeCommit_Source',
            output: output,
            repository: this.codecommitRepo
        });
        return {
            stageName: stageName,
            actions: [ codeCommitAction ]
        };
    }
    private createImageBuildStage(
        stageName: string, 
        input: codePipeline.Artifact
    ): codePipeline.StageProps {
        return {
            stageName: stageName,
            actions: [ 
                this.createLambdaAction(input),
                this.createBatchAction(input)
            ]
        };
    }
    private createLambdaAction(
        input: codePipeline.Artifact
    ): codePipelineActions.CodeBuildAction {
        const output = new codePipeline.Artifact();
        const lambdaProject = new codeBuild.PipelineProject(this, `${this.projectId}LambdaProject`, {
            projectName: `${this.projectId}Lambda`,
            buildSpec: this.buildSpec(),
            environment: {
                buildImage: codeBuild.LinuxBuildImage.AMAZON_LINUX_2,
                privileged: true
            },
            environmentVariables: {
                'DOCKERFILE_PATH': { value: 'lambda/Dockerfile' },
                'SSM_PARAM_NAME': { value: `${this.prefix}-${this.project}-LambdaImageUri` },
                'SSM_PREFIX': { value: this.prefix } 
            }
        });
        const lambdaAction = new codePipelineActions.CodeBuildAction({
            actionName: 'LambdaBuild_Action',
            input: input,
            outputs: [ output ],
            project: lambdaProject
        });
        return lambdaAction;
    }
    private createBatchAction(
        input: codePipeline.Artifact
    ): codePipelineActions.CodeBuildAction {
        const output = new codePipeline.Artifact();
        const batchProject = new codeBuild.PipelineProject(this, `${this.projectId}BatchProject`, {
            projectName: `${this.projectId}Batch`,
            buildSpec: this.buildSpec(),
            environment: {
                buildImage: codeBuild.LinuxBuildImage.AMAZON_LINUX_2,
                privileged: true
            },
            environmentVariables: {
                'DOCKERFILE_PATH': { value: 'batch/Dockerfile' },
                'SSM_PARAM_NAME': { value: `${this.prefix}-${this.project}-BatchImageUri` },
                'SSM_PREFIX': { value: this.prefix } 
            }
        });
        const batchAction = new codePipelineActions.CodeBuildAction({
            actionName: 'BatchBuild_Action',
            input: input,
            outputs: [ output ],
            project: batchProject
        });
        return batchAction;
    }
    private buildSpec(): codeBuild.BuildSpec {
        return codeBuild.BuildSpec.fromObject({
            verion: '0.2',
            phases: {
                pre_build: {
                    commands: [
                        'aws --version',
                        '$(aws ecr get-login --region ${AWS_DEFAULT_REGION} --no-include-email |  sed \'s|https://||\')',
                        'LABEL=(aws ssm get-paramer --name "${SSM_PARAM_NAME}" --query Parameter.Value --output text)'
                    ]
                },
                build: {
                    commands: [
                        'cd src',
                        'docker build -f ${DOCKERFILE_PATH} --build-arg SSM_PREFIX=${SSM_PREFIX}',
                        'docker tag ${LABEL}',
                    ]
                },
                post_build: {
                    commands: [
                        'docker push ${LABEL}',
                    ]
                }
            }
        }); 
         
    }
}