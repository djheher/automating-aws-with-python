#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Webotron: deploy websites with AWS

Webotron automates the prcess of deploying static web websites
-Configures AWS S3 list_buckets
 - Create them
 - Set them up for static hosting
 - deploy local files to them
 - configure DNS with AWS Route 53
 - Configure a content delivery network and SSL with AWS
 """
from pathlib import Path
from botocore.exceptions import ClientError
import boto3
import click
import mimetypes

session = boto3.Session(profile_name='pythonAutomation')
s3 = session.resource('s3')


@click.group()
def cli():
    """Webotron deploys websites to AWS."""
    pass


@cli.command('list-buckets')
def list_buckets():
    """list all buckets."""
    for bucket in s3.buckets.all():
        print(bucket)


@cli.command('list-bucket-objects')
@click.argument('bucket')
def list_bucket_objects(bucket):
    """List objects in s3 bucket"""
    for obj in s3.Bucket(bucket).objects.all():
        print(obj)


@cli.command('setup-bucket')
@click.argument('bucket')
def setup_bucket(bucket):
    """create and configure s3 bucket"""
    s3_bucket = None
    # try:
    #    s3_bucket = s3.create_bucket(Bucket=bucket)
    # except ClientError as e:
    #    if e.response['Error']['Code'] == 'BucketAlreadyExists':
    #        s3_bucket = s3.Bucket(bucket)
    # else:
    #    raise e
    try:
        s3_bucket = s3.create_bucket(
            Bucket=bucket
        )
    except ClientError as error:
        if error.response['Error']['Code'] == 'BucketAlreadyExists':
            s3_bucket = s3.Bucket(bucket)
        else:
            raise error

    policy = """
    {
      "Version":"2012-10-17",
      "Statement":[{
      "Sid":"PublicReadGetObject",
      "Effect":"Allow",
      "Principal": "*",
          "Action":["s3:GetObject"],
          "Resource":["arn:aws:s3:::%s/*"]
        }
      ]
    }
    """ % s3_bucket.name
    policy = policy.strip()
    pol = s3_bucket.Policy()
    pol.put(Policy=policy)

    # ws = s3_bucket.Website()
    s3_bucket.Website().put(WebsiteConfiguration={
        'ErrorDocument': {
            'Key': 'error.html'
        },
        'IndexDocument': {
            'Suffix': 'index.html'
        }
    })

    return


def upload_file(s3_bucket, path, key):
    """Upload a file."""
    content_type = mimetypes.guess_type(key)[0] or 'text/plain'
    s3_bucket.upload_file(
        path,
        key,
        ExtraArgs={
            'ContentType': content_type
        })


@cli.command('sync')
@click.argument('pathname', type=click.Path(exists=True))
@click.argument('bucket')
def sync(pathname, bucket):
    """Sync contents of pathname ot Bucket."""
    s3_bucket = s3.Bucket(bucket)

    root = Path(pathname).expanduser().resolve()

    def handle_directory(target):
        for p in target.iterdir():
            if p.is_dir(): handle_directory(p)
            if p.is_file(): upload_file(s3_bucket, str(p), str(p.relative_to(root)))

    handle_directory(root)

if __name__ == '__main__':
    cli()
