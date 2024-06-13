import * as cdk from 'aws-cdk-lib';
import { CodePipeline, CodePipelineSource, ShellStep } from 'aws-cdk-lib/pipelines';
import { Construct } from 'constructs';
import { InfraStack } from './infra-stack';

interface InfraStackProps extends cdk.StackProps {
  environmentName: string;
}

export class PipelineStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Define the pipeline
    const pipeline = new CodePipeline(this, 'Pipeline', {
      pipelineName: 'InfraPipeline',
      synth: new ShellStep('Synth', {
        input: CodePipelineSource.gitHub('johnemcbride/johntechhome', 'main', {
          authentication: cdk.SecretValue.secretsManager('github-token'),
        }),
        commands: []
      }),
    });

    // Add development stage
    pipeline.addStage(new InfraStage(this, 'Dev', {
      environmentName: 'dev',
      env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: process.env.CDK_DEFAULT_REGION }
    }));

    // Add production stage
    pipeline.addStage(new InfraStage(this, 'Prod', {
      environmentName: 'prod',
      env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: process.env.CDK_DEFAULT_REGION }
    }));
  }
}

class InfraStage extends cdk.Stage {
  constructor(scope: Construct, id: string, props: InfraStackProps) {
    super(scope, id, props);

    new InfraStack(this, `InfraStack-${props.environmentName}`, props);
  }
}
