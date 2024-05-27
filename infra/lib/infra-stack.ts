import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as cf from "aws-cdk-lib/aws-cloudfront";
import { Construct } from "constructs";
import * as python from "@aws-cdk/aws-lambda-python-alpha";
import { execSync } from "child_process";
import path = require("path");
import { LambdaRestApi } from "aws-cdk-lib/aws-apigateway";
import * as s3 from "aws-cdk-lib/aws-s3";

export class InfraStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const bucket = new s3.Bucket(this, "django_bucket", {});

    const pythonDependencies = new python.PythonLayerVersion(this, "MyLayer", {
      entry: "../layer/", // point this to your library's directory
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_8],
    });
    const fn = new lambda.Function(this, "DjangoServerless", {
      runtime: lambda.Runtime.PYTHON_3_8,
      handler: "mysite.wsgi.lambda_handler",
      code: lambda.Code.fromAsset("../mysite"),
      memorySize: 512,
      timeout: cdk.Duration.seconds(300),
      layers: [pythonDependencies],
      environment: {
        BUCKET_NAME: bucket.bucketName,
        DJANGO_LOG_LEVEL: "DEBUG",
      },
    });

    const api = new LambdaRestApi(this, "cms", {
      handler: fn,
      proxy: true,
    });

    bucket.grantReadWrite(fn);
    const dist = new cf.CloudFrontWebDistribution(this, "Distribution", {
      defaultRootObject: "",
      originConfigs: [
        {
          customOriginSource: {
            domainName: `${api.restApiId}.execute-api.${this.region}.${this.urlSuffix}`,
            // the properties below are optional
            allowedOriginSSLVersions: [cf.OriginSslPolicy.TLS_V1_2],
            originHeaders: {
              originHeadersKey: "originHeaders",
            },
            originPath: `/prod`,
            originProtocolPolicy: cf.OriginProtocolPolicy.HTTPS_ONLY,
            originShieldRegion: "eu-west-2",
          },

          behaviors: [
            {
              isDefaultBehavior: true,
              allowedMethods: cf.CloudFrontAllowedMethods.GET_HEAD_OPTIONS,
              forwardedValues: {
                queryString: true,
                cookies: { forward: "none" },
              },
              minTtl: cdk.Duration.seconds(0),
              defaultTtl: cdk.Duration.seconds(300),
              maxTtl: cdk.Duration.seconds(1200),
            },
            {
              pathPattern: "/admin*",
              allowedMethods: cf.CloudFrontAllowedMethods.ALL,
              forwardedValues: {
                queryString: true,
                cookies: { forward: "all" },
              },
              minTtl: cdk.Duration.seconds(0),
              defaultTtl: cdk.Duration.seconds(0),
              maxTtl: cdk.Duration.seconds(0),
            },
          ],
        },
      ],
    });
  }
}
