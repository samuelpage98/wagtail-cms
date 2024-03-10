import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { Construct } from "constructs";
import * as python from "@aws-cdk/aws-lambda-python-alpha";

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
      layers: [pythonDependencies],
      environment: {
        BUCKET_NAME: bucket.bucketName,
      },
    });

    const api = new LambdaRestApi(this, "cms", {
      handler: fn,
      proxy: true,
    });
  }
}
