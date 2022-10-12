"""A Python Pulumi program"""

import pulumi
import pulumi_aws as aws
import mimetypes
import os
import json

bucket = aws.s3.Bucket(
    "my-website-bucket",
    aws.s3.BucketArgs(
        website=aws.s3.BucketWebsiteArgs(
            index_document="index.html"
        )
    )
)

content_dir = "www"
for file in os.listdir(content_dir):
    filepath = os.path.join(content_dir, file)
    mime_type, _ = mimetypes.guess_type(filepath)
    obj = aws.s3.BucketObject(
        file,
        bucket=bucket.id,
        source=pulumi.FileAsset(filepath),
        content_type=mime_type,
    )

pulumi.export("bucket_name", bucket.bucket)

bucket_policy = aws.s3.BucketPolicy(
    "my-website-bucket-policy",
    bucket=bucket.id,
    policy=bucket.arn.apply(
        lambda arn: json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": "*",
                "Action": [
                    "s3:GetObject"
                ],
                "Resource": [
                    f"{arn}/*"
                ]
            }]
        })),
)

pulumi.export("website_url", pulumi.Output.concat(
    "http://", bucket.website_endpoint))