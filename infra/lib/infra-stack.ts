import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as cf from "aws-cdk-lib/aws-cloudfront";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";

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

    const distribution = new cloudfront.Distribution(this, "MyDist", {
      defaultBehavior: {
        origin: new origins.HttpOrigin(
          `${api.restApiId}.execute-api.${this.region}.${this.urlSuffix}`,
          {
            originPath: "/prod",
          }
        ),
        allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
        originRequestPolicy:
          cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
      },
      additionalBehaviors: {
        "/admin/*": {
          origin: new origins.HttpOrigin(
            `${api.restApiId}.execute-api.${this.region}.${this.urlSuffix}`,
            {
              originPath: "/prod",
            }
          ),
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
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

    new cdk.CfnOutput(this, "CloudFrontWWW", {
      value: `https://` + distribution.distributionDomainName,
    });
  }
}
