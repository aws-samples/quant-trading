// import * as cdk from '@aws-cdk/core';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

import { SsmManager } from './shared/ssm-manager';
// import * as dynamodb from '@aws-cdk/aws-dynamodb';
import { aws_dynamodb as dynamodb } from 'aws-cdk-lib';
// import * as timestream from '@aws-cdk/aws-timestream';
import { aws_timestream as timestream } from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';
export class DatabaseStack extends cdk.Stack {
  private ssm: SsmManager;
  private projectId: string;
  private timestreamTables = {
    'market_data_table': 'realtime_data',
    'portfolio_table':  'portfolio_tracker'
  };
  
  
  private removalPolicy: cdk.RemovalPolicy;

  public readonly portfolioTable: dynamodb.ITable;
  public readonly systemEventsTable: dynamodb.ITable;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    const project = this.node.tryGetContext('project');
    const prefix = this.node.tryGetContext('deployment_prefix');
    this.projectId = `${prefix}${project}`;
    this.ssm = new SsmManager(this, `${this.projectId}DbSsmManager`);

    this.removalPolicy = this.node.tryGetContext('remove_tables') === true ? cdk.RemovalPolicy.DESTROY : cdk.RemovalPolicy.RETAIN;

    this.createPortfolioMapTable();
    this.portfolioTable = this.createPortfoliosTable();
    this.systemEventsTable = this.createPortfolioSystemEventsTable();
    this.createTimestream();
    NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-IAM4', reason: 'uses AWS managed role - nothing to do' }]);
    NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-IAM5', reason: 'uses AWS managed role - nothing to do' }]);
    NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-DDB3', reason: 'uses AWS managed role - nothing to do' }]);
    NagSuppressions.addStackSuppressions(this, [ { id: 'AwsSolutions-TS3', reason: 'uses AWS managed role - nothing to do' }]);
    
    
  }

  private createPortfolioMapTable() {
      const table = new dynamodb.Table(this, `${this.projectId}PortfolioMap`, {
          tableName: `${this.projectId}SymbolTable`,
          partitionKey: { name: 'symbol', type: dynamodb.AttributeType.STRING },
          billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
          removalPolicy: this.removalPolicy,
      });
      this.ssm.setParameterValue({
          value: table.tableName,
          valueName: 'PortfolioMapTable'
      });
  }

  private createPortfoliosTable(): dynamodb.Table {
    const replicaRegions = this.node.tryGetContext('portfolio_table_replica_regions');
    const table = new dynamodb.Table(this, `${this.projectId}Portfolios`, {
        tableName: `${this.projectId}PortfolioTable`,
        partitionKey: { name: 'portf_id', type: dynamodb.AttributeType.STRING },
        sortKey: {name: 'portf_create_ts', type: dynamodb.AttributeType.NUMBER },
        stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        replicationRegions: replicaRegions,
        removalPolicy: this.removalPolicy,
    });
    this.ssm.setParameterValue({
        value: table.tableName,
        valueName: 'PortfoliosTable'
    });
    return table;
  }
  private createPortfolioSystemEventsTable(): dynamodb.Table {
    const replicaRegions = this.node.tryGetContext('portfolio_table_replica_regions');
    const table = new dynamodb.Table(this, `${this.projectId}SystemEventTable`, {
        tableName: `${this.projectId}SystemEventTable`,
        partitionKey: { name: 'event_id', type: dynamodb.AttributeType.STRING },
        stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        replicationRegions: replicaRegions,
        removalPolicy: this.removalPolicy,
    });
    this.ssm.setParameterValue({
        value: table.tableName,
        valueName: 'SystemEventTable'
    });
    return table;
  }

  private createTimestreamDb(): timestream.CfnDatabase {
      const db = new timestream.CfnDatabase(this, `${this.projectId}TimestreamDb`, {
          databaseName: `${this.projectId}Timestream`,
      });
      this.ssm.setParameterValue({
          value: db.databaseName!,
          valueName: 'TimestreamDb'
      });
      return db
  }
  private createTimestreamTable(db: string, table: string): timestream.CfnTable {
      const timestreamTable = new timestream.CfnTable(this, `${this.projectId}TimestreamTable${table}`, {
          databaseName: db,
          tableName: table,
      });
      return timestreamTable;
  }
  private createTimestream() {
    const timestreamDb = this.createTimestreamDb();
    for ( const [_, value] of Object.entries(this.timestreamTables)) {
        let timestreamTable = this.createTimestreamTable(timestreamDb.databaseName!, value);
        timestreamTable.node.addDependency(timestreamDb);
    }
    this.ssm.setParameterValue({
        value: this.timestreamTables,
        valueName: 'TimestreamTables'
    });
    
  }
  
}
