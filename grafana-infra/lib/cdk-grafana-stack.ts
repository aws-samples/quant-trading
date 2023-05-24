import * as cdk from '@aws-cdk/core';
import * as ec2 from '@aws-cdk/aws-ec2';
import * as ecs from '@aws-cdk/aws-ecs';
import * as ecs_patterns from '@aws-cdk/aws-ecs-patterns';
import * as efs from '@aws-cdk/aws-efs';
import * as iam from '@aws-cdk/aws-iam';
import * as logs from '@aws-cdk/aws-logs';
import * as r53 from '@aws-cdk/aws-route53';
import * as secretsmanager from '@aws-cdk/aws-secretsmanager';
import {ApplicationProtocol} from "@aws-cdk/aws-elasticloadbalancingv2";

export class CdkGrafanaStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Get Context Values
    // const domainName = this.node.tryGetContext('domainName');
    // const hostedZoneId = this.node.tryGetContext('hostedZoneId');
    // const zoneName = this.node.tryGetContext('zoneName');

    // if (!domainName || !hostedZoneId || !zoneName) {
    //   throw new Error('Please provide required parameters domainName, hostedZoneId, zoneName via context variables');
    // }

    const enablePrivateLink = this.node.tryGetContext('enablePrivateLink');
    // const domainZone = r53.PublicHostedZone.fromHostedZoneAttributes( this, "MyHostedZone", {
    //   hostedZoneId: hostedZoneId,
    //   zoneName: zoneName
    // });
    // vpc
    const vpc = new ec2.Vpc(this, "MyVpc", {
      maxAzs: 2 // Default is all AZs in region
    });

    if (enablePrivateLink == 'true') {
      vpc.addInterfaceEndpoint('CWEndpoint',  {service: ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH});
      vpc.addInterfaceEndpoint('EFSEndpoint', {service: ec2.InterfaceVpcEndpointAwsService.ELASTIC_FILESYSTEM});
      vpc.addInterfaceEndpoint('SMEndpoint',  {service: ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER});
    }

    const cluster = new ecs.Cluster(this, "MyCluster", {
      vpc: vpc
    });

    // EFS
    const fileSystem = new efs.FileSystem(this, 'EfsFileSystem', {
      vpc: vpc,
      encrypted: true,
      lifecyclePolicy: efs.LifecyclePolicy.AFTER_14_DAYS,
      performanceMode: efs.PerformanceMode.GENERAL_PURPOSE,
      throughputMode: efs.ThroughputMode.BURSTING
    });

    const accessPoint = new efs.AccessPoint(this, 'EfsAccessPoint', {
      fileSystem: fileSystem,
      path: '/var/lib/grafana',
      posixUser: {
        gid: '1000',
        uid: '1000'
      },
      createAcl: {
        ownerGid: '1000',
        ownerUid: '1000',
        permissions: '755'
      }
    });

    // task log group
    const logGroup = new logs.LogGroup(this, 'taskLogGroup', {
      retention: logs.RetentionDays.ONE_MONTH
    });

    // container log driver
    const containerLogDriver = ecs.LogDrivers.awsLogs({
      streamPrefix: 'fargate-grafana', //cdk.Stack.stackName,
      logGroup: logGroup
    });
    
    // Use customer provided Grafana Role
    const grafanaRole = iam.Role.fromRoleArn(this, 'Role','ROLE_ARN')
    // // Grafana service task Role
    // const taskRole = new iam.Role(this, 'taskRole', {
    //   assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    // });

    //   taskRole.addToPolicy(new iam.PolicyStatement({
    //   effect: iam.Effect.ALLOW,
    //   actions: [
    //     'cloudwatch:DescribeAlarmsForMetric',
    //     'cloudwatch:DescribeAlarmHistory',
    //     'cloudwatch:DescribeAlarms',
    //     'cloudwatch:ListMetrics',
    //     'cloudwatch:GetMetricStatistics',
    //     'cloudwatch:GetMetricData',
    //     'ec2:DescribeTags',
    //     'ec2:DescribeInstances',
    //     'ec2:DescribeRegions',
    //     'tag:GetResources',
    //     "timestream:CancelQuery",
    //     'timestream:DescribeEndpoints',
    //     "timestream:DescribeTable",
    //     "timestream:ListTables",
    //     "timestream:ListDatabases",
    //     "timestream:ListMeasures",
    //     'timestream:SelectValues',
    //     "timestream:Select"
    //   ],
    //   resources: ['*']
    // }));

    // // execution Role
    // const executionRole = new iam.Role(this, 'executionRole', {
    //   assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    // });

    // executionRole.addToPolicy(new iam.PolicyStatement({
    //   effect: iam.Effect.ALLOW,
    //   actions: [
    //     'logs:CreateLogStream',
    //     'logs:PutLogEvents',
    //   ],
    //   resources: [
    //     logGroup.logGroupArn
    //   ]
    // }));

    // Create Task Definition - # EFS integration currently uses escape hatches until native CDK support is added #
    const volumeName = 'efsGrafanaVolume';

    const volumeConfig: ecs.Volume = {
      name: volumeName,
      efsVolumeConfiguration: {
        fileSystemId: fileSystem.fileSystemId,
        transitEncryption: 'ENABLED',
        authorizationConfig: { accessPointId: accessPoint.accessPointId}
      },
    };

    // https://aws.amazon.com/blogs/aws/amazon-ecs-supports-efs/
    const task_definition = new ecs.FargateTaskDefinition(this, "TaskDef",{
      taskRole: grafanaRole,
      executionRole: grafanaRole,
      volumes: [volumeConfig]
    });

    // Grafana Admin Password
    const grafanaAdminPassword = new secretsmanager.Secret(this, 'grafanaAdminPassword');
    // Allow Task to access Grafana Admin Password
    grafanaAdminPassword.grantRead(grafanaRole);

    // Web Container
    const container_web = task_definition.addContainer("web", {
          image: ecs.ContainerImage.fromRegistry('grafana/grafana'),
          logging: containerLogDriver,
          secrets: {
            GF_SECURITY_ADMIN_PASSWORD: ecs.Secret.fromSecretsManager(grafanaAdminPassword)
          },
          // environment: {
          //   'GF_SERVER_ROOT_URL' : `https://${domainZone.zoneName}`,
          // }

        }
    );
    // set port mapping
    container_web.addPortMappings({
      containerPort: 3000
    });
    container_web.addMountPoints({
      sourceVolume: volumeConfig.name,
      containerPath: '/var/lib/grafana',
      readOnly: false
    });

    // Create a load-balanced Fargate service and make it public
    const fargateService = new ecs_patterns.ApplicationLoadBalancedFargateService(this, "MyFargateService", {
      // domainName: domainName,
      // domainZone: domainZone,
      cluster: cluster, // Required
      cpu: 1024, // https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html
      desiredCount: 1, // Should be set to 1 to prevent multiple tasks attempting to write to EFS volume concurrently
      taskDefinition: task_definition,
      memoryLimitMiB: 2048, // https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html
      // protocol: ApplicationProtocol.HTTPS,
      platformVersion: ecs.FargatePlatformVersion.VERSION1_4
    });

    fargateService.targetGroup.configureHealthCheck({
      path: '/api/health'
    });

    // Allow Task to access EFS
    fileSystem.connections.allowDefaultPortFrom(fargateService.service.connections);

  }
}
