import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as logs from "aws-cdk-lib/aws-logs";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";
import * as python from "@aws-cdk/aws-lambda-python-alpha";
import { LambdaRestApi } from "aws-cdk-lib/aws-apigateway";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import path = require("path");

interface InfraStackProps extends cdk.StackProps {
  environmentName: string;
}

export class InfraStack extends cdk.Stack {
  public readonly migrationLambda: lambda.Function;
  public readonly housekeepingLambda: lambda.Function;
  public readonly bucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: InfraStackProps) {
    super(scope, id, props);

    const prefix = props.environmentName;

    this.bucket = new s3.Bucket(this, `DjangoBucket`, {
      versioned: true,
    });

    const pythonDependencies = new python.PythonLayerVersion(this, `MyLayer`, {
      entry: "../layer/",
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_9],
    });

    const versionTable = new dynamodb.Table(this, `VersionTable`, {
      partitionKey: { name: "domainName", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "version", type: dynamodb.AttributeType.NUMBER },
    });

    const sessionsTable = new dynamodb.Table(this, `Sessions`, {
      partitionKey: {
        name: "session_key",
        type: dynamodb.AttributeType.STRING,
      },
    });

    const fn = new lambda.Function(this, `DjangoServerless`, {
      tracing: lambda.Tracing.ACTIVE,
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: "mysite.wsgi.lambda_handler",
      code: lambda.Code.fromAsset("../mysite"),
      memorySize: 1024,
      timeout: cdk.Duration.seconds(300),
      layers: [pythonDependencies],
      environment: {
        BUCKET_NAME: this.bucket.bucketName,
        TABLE_NAME: versionTable.tableName,
        DJANGO_LOG_LEVEL: "DEBUG",
        DYNAMODB_SESSIONS_TABLE_NAME: sessionsTable.tableName,
      },
    });

    const accessLogGroup = new logs.LogGroup(this, `AccessLogGroup`, {
      logGroupName: `/aws/api-gateway/cms-${prefix}`,
      retention: logs.RetentionDays.ONE_WEEK,
    });

    const apiGateway = new LambdaRestApi(this, `${prefix}CmsApi`, {
      handler: fn,
      proxy: true,
      deployOptions: {
        stageName: `${prefix}`,
        accessLogFormat: apigateway.AccessLogFormat.custom(
          JSON.stringify({
            requestId: apigateway.AccessLogField.contextRequestId(),
            status: apigateway.AccessLogField.contextStatus(),
            time: apigateway.AccessLogField.contextRequestTime(),
            path: apigateway.AccessLogField.contextResourcePath(),
            protocol: apigateway.AccessLogField.contextProtocol(),
            responseLength: apigateway.AccessLogField.contextResponseLength(),
            sourceIp: apigateway.AccessLogField.contextIdentitySourceIp(),
            error: apigateway.AccessLogField.contextErrorMessageString(),
            method: apigateway.AccessLogField.contextHttpMethod(),
            contextPath: apigateway.AccessLogField.contextPath(),
            errorType:
              apigateway.AccessLogField.contextRequestOverrideHeader.toString(),
            "error.message": "$context.error.message", // The error message returned by API Gateway.
            httpMethod: "$context.httpMethod", // The HTTP method used. Valid values include: DELETE, GET, HEAD, OPTIONS, PATCH, POST, and PUT.
            "identity.sourceIp": "$context.identity.sourceIp", // The IP address of the client that sent the request.
            "integration.error": "$context.integration.error", // The error message returned by the integration.
            "integration.integrationStatus":
              "$context.integration.integrationStatus", // The status code returned by the integration.
            "integration.latency": "$context.integration.latency", // The time between when API Gateway receives a request from a client and when it returns a response to the client. The latency includes the integration latency and other API Gateway overhead.
            "integration.requestId": "$context.integration.requestId", // The ID of the request sent to the integration.
            "integration.status": "$context.integration.status", // The HTTP status code that is returned by the integration back to API Gateway.
            responseLatency: "$context.responseLatency", // The time between when API Gateway receives a request from a client and when it returns a response to the client. The latency does not include the integration latency.
            stage: "$context.stage", // The name of the API Gateway stage that processes the request.
          })
        ),
        accessLogDestination: new apigateway.LogGroupLogDestination(
          accessLogGroup
        ),
      },
      cloudWatchRole: true,
      binaryMediaTypes: [
        "image/*",
        "*font*",
        "application/font-woff",
        "font/woff2",
        "font/*",
        "*/*",
      ],
    });

    versionTable.grantReadWriteData(fn);
    sessionsTable.grantReadWriteData(fn); // todo restrict

    this.bucket.grantReadWrite(fn);

    const origin = new origins.HttpOrigin(
      `${apiGateway.restApiId}.execute-api.${this.region}.${this.urlSuffix}`,
      {
        originPath: `/${prefix}`,
      }
    );

    const originAccessIdentity = new cloudfront.OriginAccessIdentity(
      this,
      `${prefix}OAI`,
      {
        comment: `OAI for ${this.bucket.bucketName}`,
      }
    );

    const media = new origins.S3Origin(this.bucket, {
      originPath: "/media",
      originAccessIdentity: originAccessIdentity,
    });

    this.bucket.grantRead(originAccessIdentity);

    const distribution = new cloudfront.Distribution(this, `MyDist`, {
      defaultBehavior: {
        origin: origin,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
        originRequestPolicy:
          cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        // recommended for api agewatey - tryied all, and  api gateway chokes
        // responseHeadersPolicy:
        //   cloudfront.ResponseHeadersPolicy.CORS_ALLOW_ALL_ORIGINS,
      },
      additionalBehaviors: {
        "/media/*": {
          // Use your own path pattern
          origin: media,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
          cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
          originRequestPolicy:
            cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        },
      },
      enableLogging: true,
    });

    fn.addEnvironment(
      "CLOUDFRONT_DISTRIBUTION_DOMAINNAME",
      distribution.distributionDomainName
    );

    fn.addEnvironment(
      "CLOUDFRONT_DISTRIBUTION_ID",
      distribution.distributionId
    );

    // Attach permissions to Lambda to invalidate CloudFront cache
    const invalidationPolicy = new iam.PolicyStatement({
      actions: ["cloudfront:CreateInvalidation"],
      resources: [
        `arn:aws:cloudfront::${this.account}:distribution/${distribution.distributionId}`,
      ],
    });

    fn.addToRolePolicy(invalidationPolicy);

    // Define the migration Lambda function with the pre-created role
    this.migrationLambda = new lambda.Function(this, "MigrationLambda", {
      tracing: lambda.Tracing.ACTIVE,
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: "migrate_function.handler",
      memorySize: 1024,
      timeout: cdk.Duration.seconds(300),
      code: lambda.Code.fromAsset(path.join(__dirname, "lambda")),
      environment: {
        API_ENDPOINT: `https://${apiGateway.restApiId}.execute-api.${this.region}.amazonaws.com/${prefix}`,
      },
    });

    // housekeeping
    this.housekeepingLambda = new lambda.Function(this, "HousekeepingLambda", {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: "housekeeping.handler",
      memorySize: 1024,
      timeout: cdk.Duration.seconds(300),
      code: lambda.Code.fromAsset(path.join(__dirname, "housekeeping")),
      environment: {
        BUCKET_NAME: this.bucket.bucketName,
        TABLE_NAME: versionTable.tableName,
      },
    });

    versionTable.grantReadWriteData(this.housekeepingLambda);
    this.bucket.grantReadWrite(this.housekeepingLambda);

    const lambda_cw_event = new cdk.aws_events.Rule(this, "HouseKeeping", {
      description: "Clean up data once an hour for django thing",
      enabled: true,
      schedule: cdk.aws_events.Schedule.rate(cdk.Duration.hours(1)),
      targets: [
        new cdk.aws_events_targets.LambdaFunction(this.housekeepingLambda),
      ],
    });

    new cdk.CfnOutput(this, `CloudFrontWWW`, {
      value: `https://` + distribution.distributionDomainName,
    });
  }
}
