#!/usr/bin/env python3
#
# Script does
# * download a backup of existing content
# * generates new content locally using [Hugo](https://gohugo.io/)
# * uploads generated content to S3

from pprint import pprint as pp
from subprocess import Popen

import os
import sys
import json
import shutil
import logging
import mimetypes

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)
# https://stackoverflow.com/questions/1661275/disable-boto-logging-without-modifying-the-boto-files
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('nose').setLevel(logging.CRITICAL)
logging.getLogger('s3transfer').setLevel(logging.CRITICAL)

import boto3
import boto3.session

import botocore.config


REGION = "eu-west-1"
BUCKET_NAME = "getgoetz.com"
JSON_CONFIG_FILE = "aws-credentials.json"


# https://stackoverflow.com/questions/31918960/boto3-to-download-all-files-from-a-s3-bucket
def download_bucket_content(resource, path_from, dir_to, bucket):
    paginator = resource.meta.client.get_paginator('list_objects')
    for result in paginator.paginate(Bucket=bucket, Delimiter='/', Prefix=path_from):
        if result.get('CommonPrefixes') is not None:
            for subdir in result.get('CommonPrefixes'):
                download_bucket_content(resource, subdir.get('Prefix'), dir_to, bucket)
        if result.get('Contents') is not None:
            for file in result.get('Contents'):
                if not os.path.exists(os.path.dirname(dir_to + os.sep + file.get('Key'))):
                     os.makedirs(os.path.dirname(dir_to + os.sep + file.get('Key')))

                logger.info('\tDownload from S3: {} -> {}'.format(
                  os.path.join(bucket, file.get('Key')),
                  os.path.join(dir_to, file.get('Key'))
                ))
                resource.meta.client.download_file(bucket, file.get('Key'), dir_to + os.sep + file.get('Key'))


# https://stackoverflow.com/questions/43326493/what-is-the-fastest-way-to-empty-s3-bucket-using-boto3
def delete_bucket_content(resource, bucket):
  bucket = resource.Bucket(bucket)
  bucket.objects.all().delete()


# https://stackoverflow.com/questions/43580/how-to-find-the-mime-type-of-a-file-in-python
# https://docs.python.org/3.7/library/mimetypes.html
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types
def content_type_get(file_path):
  content_type = mimetypes.MimeTypes().guess_type(file_path)[0]

  if content_type is None:
    return 'application/octet-stream' # boto3 aka AWS uses 'binary/octet-stream' for this type

  else:

    list_of_text_types = [
      'text/html',
      'text/plain',
      'text/css',
      'application/xml',
      'application/javascript',
      'application/json',
    ]

    if content_type in list_of_text_types:
      content_type += '; charset=utf-8'

    return content_type


# https://gist.github.com/feelinc/d1f541af4f31d09a2ec3
# https://boto3.readthedocs.io/en/latest/reference/services/s3.html#S3.Object.put
def upload_to_bucket(resource, source_dir, bucket):
    if not os.path.isdir(source_dir):
        raise ValueError('source_dir %r not found.' % source_dir)

    for root, _, files in os.walk(source_dir):
        for file_name in files:
          file_path = os.path.join(root, file_name)
          s3_path = os.path.relpath(file_path, source_dir)
          content_type = content_type_get(file_path)

          logger.info('\tUploading to S3: {} -> {} [{}]'.format(file_path, s3_path, content_type))
          resource.Object(bucket, s3_path).put(
            Body=open(os.path.join(source_dir, file_path), 'rb'),
            ContentType=content_type
          )


path_blog_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
path_config = os.path.abspath(os.path.join(os.path.dirname(__file__), JSON_CONFIG_FILE))
path_blog_public_folder = os.path.abspath(os.path.join(path_blog_root, "public"))
path_blog_public_prior_folder = os.path.abspath(os.path.join(path_blog_root, "public_prior"))

logger.info("+ Local LOAD credentials for AWS: {}".format(path_config))
with open(path_config) as json_config_file:
    data = json.load(json_config_file)

boto3.setup_default_session(
    aws_access_key_id=data["aws_access_key_id"],
    aws_secret_access_key=data["aws_secret_access_key"],
)

# https://stackoverflow.com/questions/39272744/when-to-use-a-boto3-client-and-when-to-use-a-boto3-resource
resource = boto3.resource('s3', region_name=REGION)

logger.info("+ Local DELETE backup content: {}".format(path_blog_public_prior_folder))
shutil.rmtree(path_blog_public_prior_folder, ignore_errors=True)
os.mkdir(path_blog_public_prior_folder)

logger.info("+ Local BACKUP content from S3: {}".format(path_blog_public_prior_folder))
download_bucket_content(resource, "", path_blog_public_prior_folder, BUCKET_NAME)

logger.info("+ Local DELETE old content: {}".format(path_blog_public_folder))
shutil.rmtree(path_blog_public_folder, ignore_errors=True)

logger.info("+ Local BUILD site: {}".format(path_blog_public_folder))
Popen(["hugo", "--minify"], shell=True, cwd=path_blog_root)

logger.info("+ Remote DELETE bucket content: {}".format(BUCKET_NAME))
delete_bucket_content(resource, BUCKET_NAME)

logger.info("+ Remote UPLOAD new content to S3: {}".format(BUCKET_NAME))
upload_to_bucket(resource, path_blog_public_folder, BUCKET_NAME)
