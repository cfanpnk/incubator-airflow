# -*- coding: utf-8 -*-
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.


import boto3
import configparser
import logging

from airflow.exceptions import AirflowException
from airflow.hooks.base_hook import BaseHook


def _parse_s3_config(config_file_name, config_format='boto', profile=None):
    """
    Parses a config file for s3 credentials. Can currently
    parse boto, s3cmd.conf and AWS SDK config formats

    :param config_file_name: path to the config file
    :type config_file_name: str
    :param config_format: config type. One of "boto", "s3cmd" or "aws".
        Defaults to "boto"
    :type config_format: str
    :param profile: profile name in AWS type config file
    :type profile: str
    """
    config = configparser.ConfigParser()
    if config.read(config_file_name):  # pragma: no cover
        sections = config.sections()
    else:
        raise AirflowException("Couldn't read {0}".format(config_file_name))
    # Setting option names depending on file format
    if config_format is None:
        config_format = 'boto'
    conf_format = config_format.lower()
    if conf_format == 'boto':  # pragma: no cover
        if profile is not None and 'profile ' + profile in sections:
            cred_section = 'profile ' + profile
        else:
            cred_section = 'Credentials'
    elif conf_format == 'aws' and profile is not None:
        cred_section = profile
    else:
        cred_section = 'default'
    # Option names
    if conf_format in ('boto', 'aws'):  # pragma: no cover
        key_id_option = 'aws_access_key_id'
        secret_key_option = 'aws_secret_access_key'
        # security_token_option = 'aws_security_token'
    else:
        key_id_option = 'access_key'
        secret_key_option = 'secret_key'
    # Actual Parsing
    if cred_section not in sections:
        raise AirflowException("This config file format is not recognized")
    else:
        try:
            access_key = config.get(cred_section, key_id_option)
            secret_key = config.get(cred_section, secret_key_option)
        except:
            logging.warning("Option Error in parsing s3 config file")
            raise
        return access_key, secret_key


class AwsHook(BaseHook):
    """
    Interact with AWS.
    This class is a thin wrapper around the boto3 python library.
    """

    def __init__(self, aws_conn_id='aws_default'):
        self.aws_conn_id = aws_conn_id

    def _get_credentials(self, region_name):
        config = ConfigParser.RawConfigParser()
        config.read(os.path.expanduser('~/.aws/credentials'))
        aws_access_key_id = config.get('dev', 'aws_access_key_id')
        aws_secret_access_key = config.get('dev', 'aws_secret_access_key')
        aws_session_token = config.get('dev', 'aws_session_token')
        region_name = config.get('dev', 'region')
        endpoint_url = None

        return boto3.session.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=region_name), endpoint_url

    def get_client_type(self, client_type, region_name=None):
        session, endpoint_url = self._get_credentials(region_name)

        return session.client(client_type, endpoint_url=endpoint_url)

    def get_resource_type(self, resource_type, region_name=None):
        session, endpoint_url = self._get_credentials(region_name)

        return session.resource(resource_type, endpoint_url=endpoint_url)

    def get_session(self, region_name=None):
        """Get the underlying boto3.session."""
        session, _ = self._get_credentials(region_name)
        return session

    def get_credentials(self, region_name=None):
        """Get the underlying `botocore.Credentials` object.

        This contains the attributes: access_key, secret_key and token.
        """
        session, _ = self._get_credentials(region_name)
        # Credentials are refreshable, so accessing your access key / secret key
        # separately can lead to a race condition.
        # See https://stackoverflow.com/a/36291428/8283373
        return session.get_credentials().get_frozen_credentials()
