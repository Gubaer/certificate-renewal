#!/usr/bin/env python3
#
# login uses credentials in the env variables AWS_ACCESS_KEY_ID and
# AWS_SECRET_ACCESS_KEY
#
import os
import sys
from time import gmtime, strftime
import boto3
import subprocess
import shutil
import argparse
import pprint
import json
import tempfile
import yaml

DEFAULT_CONFIG_FILENAME="renew-certificate.conf"

def is_file_readable(file):
    return os.path.isfile(file) or not os.access(file, os.R_OK)

def first_not_none(list):
    try:
        return next(value for value in list if value is not None)
    except StopIteration:
        return None

class ConfigError(Exception):
    """Represents a configuration exception"""
    pass

class Config:
    """Represents the configuration parameters for the renew task"""

    @staticmethod
    def default_config_file_path():
        """Replies the full path to the default location of the config file"""
        return os.path.join(os.getcwd(), DEFAULT_CONFIG_FILENAME)

    @staticmethod
    def ensure_config_file_readable(config_file_path=None):
        if config_file_path != None:
            path = config.config_file
            if not is_file_readable(path):
                raise ConfigError(
                    "FATAL: config file '{0}' doesn't exist or isn't readable. Aborting."
                    .format(path)
                )

    # the config dict loaded from the config YAML file
    config_file_entries = None
    # the command line arguments
    args = None

    def config_entry(self, *keys):
        value = self.config_file_entries
        if value == None:
            return None
        for key in keys:
            try:
                value = value[key]
            except KeyError:
                return None
        return value

    def load_config_file(self, config_file):
        with open(config_file, "r") as stream:
            self.config_file_entries = yaml.load(stream)

    def __init__(self, args):
        self.args = args
        config_file_path = args.config_file_path
        if config_file_path == None:
            config_file_path = Config.default_config_file_path()
            print("INFO: trying to read config file from default" + 
                " location '{0}'".format(config_file_path))

        if not is_file_readable(config_file_path):
            print(("WARNING: config file at location '{0}'" + 
                " doesn't exist or isn't readable. Ignoring config file.")
                .format(config_file_path))
            return

        try:
            self.load_config_file(config_file_path)
        except  (yaml.YAMLError, IOError) as e:
            raise IOError(
                "failed to read config file '{0}".format(config_file_path)
            ) from e

    _certbot_dir = None
    @property
    def certbot_dir(self):
        """Replies the full path to the certbot working directory."""
        config_values = [
            self._certbot_dir,
            self.args.certbot_dir,
            self.config_entry("certbot", "dir")
        ]
        value = first_not_none(config_values)
        if value:
            self._certbot_dir = value
            return value
        value = tempfile.mkdtemp(suffix=".certbot")
        self._certbot_dir = value
        return value

    @property
    def certbot_domain(self):
        """Replies the domain for which a certificate is renewed"""
        config_values = [
            self.args.certbot_domain,
            self.config_entry("certbot","domain")
        ]
        value = first_not_none(config_values)
        if value:
            return value
        raise ConfigError(
            """certbot domain is not configured. Either configure it in the 
            config file or use the command line argument --certbot-domain.
            """)

    @property
    def certbot_email(self):
        """Replies the email address used to renew the certificate"""
        config_values = [
            self.args.certbot_email,
            self.config_entry("certbot","email")
        ]
        value = first_not_none(config_values)
        if value:
            return value
        raise ConfigError(
            """certbot email is not configured. Either configure it in the 
            config file or use the command line argument --certbot-email.
            """
        )

    @property
    def s3_bucket(self):
        """Replies the name of the S3 bucket where the website is hosted"""
        # possible values, from highest to lowest priority
        config_values = [
            self.args.s3_bucket,
            self.config_entry("s3","bucket"),
            self.certbot_domain
            ]
        # find the non-null value with highest priority
        return first_not_none(config_values)

    @property
    def cloudfront_distribution_id(self):
        """Replies the id of the cloudfront distribution whose server 
        certificate is updated"""
        config_values = [
            self.args.cloudfront_distribution_id,
            self.config_entry("cloudfront","distribution_id")
        ]
        value = first_not_none(config_values)
        if value:
            return value
        raise ConfigError(
            """cloudfront distribution is is not configured. Either configure 
            it in the config file or use the command line argument 
            --cloudfront-distribution-id.
            """
        )

class CertificateRenewTask:
    config = None

    def __init__(self, config):
        self.config = config

    @property
    def certbot_dir(self):
        return self.config.certbot_dir

    def remove_certbot_dir(self):
        """removes the certbot directory"""
        print("info: removing certbot directory '{0}'".format(self.certbot_dir))
        shutil.rmtree(self.certbot_dir)

    def init_certbotdir(self):
        """creates the three subdirectories in the certbot directory,
        unless they already exist"""
        if not os.path.isdir(self.certbot_dir):
            os.makedirs(self.certbot_dir)

        print("Using certbot directory '{0}'".format(self.certbot_dir))
        for subdir in ["config", "work", "logs"]:
            dir = os.path.join(self.certbot_dir, subdir)
            if not os.path.isdir(dir):
                os.makedirs(dir)

    def build_certbot_command(self):
        return [
            "/usr/bin/certbot", "certonly",
            "--manual",
            "--domains", self.config.certbot_domain,
            "--email", self.config.certbot_email,
            "--preferred-challenges", "http",
            "--force-renew",
            "--manual-public-ip-logging-ok",
            "--no-eff-email",
            "--agree-tos",
            "--config-dir", os.path.join(self.certbot_dir, "config"),
            "--work-dir", os.path.join(self.certbot_dir, "work"),
            "--logs-dir", os.path.join(self.certbot_dir, "logs")
        ]

    def next_line(self, certbot_process):
        """Replies the next non-empty line from the output of certbot. 
        Raises an IOError if no such line is available."""
        while True:
            line = certbot_process.stdout.readline()
            if line == "":
                raise IOError("unexpected end of output from certbot")
            line = line.strip()
            if line == b"":
                continue
            return line

    def publish_challenge(self, challenge_info):
        """Published the challenge info in the S3 bucket hosting the website"""
        print("publishing challenge to {0}".format(challenge_info["challenge_url"]))
        s3 = boto3.client("s3")
        # the url withouth the leading http://www.kacon.ch/
        file = challenge_info["challenge_url"][20:]
        s3.put_object(
            Bucket = "www.kacon.ch",
            Key = file,
            Body = challenge_info["challenge_content"])
        print("challenge successfully published")

    def wait_for_challenge_info(self, certbot_process):
        while True:
            line = self.next_line(certbot_process)
            #if line.startswith("Cert not yet due for renewal"):
                # if we try to renew too often, certbot repots this line in the
                # output
                #raise RuntimeException("certificate not yet due for rnewal")
            if line.startswith(b"Create a file containing just this data"):
                challenge_content = self.next_line(certbot_process).decode("utf-8")
            if line.startswith(b"And make it available on your web server at this URL"):
                challenge_url = self.next_line(certbot_process).decode("utf-8")
                return {
                    "challenge_content": challenge_content, 
                    "challenge_url": challenge_url
                }

    def build_certificate_name(self):
        date_tag = strftime("%Y_%m_%d_%H_%M_%S", gmtime())
        certificate_name = self.config.certbot_domain.replace(".", "_")
        certificate_name = "{0}_{1}".format(certificate_name, date_tag)
        return certificate_name

    def read_text_file(self, path):
        """replies the content of the text file given by path"""
        with  open(path, "r") as file:
            return "".join(file.readlines())

    def read_public_key(self):
        """reads the content of the public key in 'cert.pem'
        and replies it as string"""
        return self.read_text_file(
            os.path.join(
                self.certbot_dir, "config", "live", self.config.certbot_domain,
                "cert.pem")
        )

    def read_private_key(self):
        """reads the content of the private key in 'privkey.pem' and
        replies it as string"""
        return self.read_text_file(
            os.path.join(
                self.certbot_dir, "config", "live", self.config.certbot_domain,
                "privkey.pem")
        )

    def read_certificate_chain(self):
        """reads the content of the certificate chain in 'fullchain.pem'
        and replies it as string"""
        return self.read_text_file(
            os.path.join(
                self.certbot_dir, "config", "live", self.config.certbot_domain,
                "chain.pem")
        )

    def upload_certificate(self):
        """uploads the server certificate to AWS IAM"""
        iam = boto3.client("iam")
        response = iam.upload_server_certificate(
            Path="/cloudfront/certs/",
            ServerCertificateName = self.build_certificate_name(),
            CertificateBody = self.read_public_key(),
            PrivateKey = self.read_private_key(),
            CertificateChain = self.read_certificate_chain()
        )
        return response["ServerCertificateMetadata"]["ServerCertificateId"]

    def renew(self):
        certbot_cmd = self.build_certbot_command()
        certbot_process = subprocess.Popen(certbot_cmd,
            stdout = subprocess.PIPE,
            stdin = subprocess.PIPE)
        challenge_info = self.wait_for_challenge_info(certbot_process)
        self.publish_challenge(challenge_info)
        certbot_process.communicate(b"\n")

    def get_cloudfront_distribution(self, id):
        cloudfront = boto3.client('cloudfront')
        return cloudfront.get_distribution(Id=id)

    def update_cloudfront_distribution(self, id, distribution_config, etag):
        cloudfront = boto3.client('cloudfront')
        cloudfront.update_distribution(
            Id=id,
            DistributionConfig=distribution_config,
            IfMatch=etag)

def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="renews and publishes a letsencrypt certificate")
    parser.add_argument("--certbot-dir", dest="certbot_dir", 
        metavar="DIR", 
        help="the directory where the script creates the config, work, " +
            "and logs directory for certbot\n" +
            "If missing, creates a new temporary directory.")
    parser.add_argument("--remove-certbot-dir", 
        action="store_true",
        help="if set, removes the certbot directory after the script is run.\n" +
            "This deletes the certificates, including the private keys from \n" +
            "the local filesystem.")
    parser.add_argument("-c", "--config-file",
        dest="config_file_path",
        metavar="PATH",
        help="the path to the config file")
    parser.add_argument("--certbot-domain",
        dest="certbot_domain",
        metavar="DOMAIN",
        help="the domain for which we renew a certificate, i.e. www.kacon.ch")
    parser.add_argument("--certbot-email",
        dest="certbot_email",
        metavar="EMAIL_ADDRESS",
        help="the email address used to renew the certificate, " + 
             " i.e. user@a-domain.com")
    parser.add_argument("--s3-bucket",
        dest="s3_bucket",
        metavar="BUCKET_NAME",
        help="the name of the S3 bucket where the website is hosted")
    parser.add_argument("--cloudfront-distribution-id",
        metavar="ID",
        help="the id of the cloudfront distribution whose server certifiate" +
            " we update with the renewed certificate")
    return parser

def main():
    parser = build_argument_parser()
    args = parser.parse_args()
    config = Config(args)

    # if a config file is passed in, make sure it exists and is readable
    Config.ensure_config_file_readable(args.config_file_path)

    task = CertificateRenewTask(config)
    task.init_certbotdir()

    # renew certificate
    print("renewing certificate: starting ...")
    task.renew()
    print("renewing certificate: DONE")
    
    # upload the new certificate
    server_certificate_id = task.upload_certificate()
    print("uploaded server certificate with id {0}"
        .format(server_certificate_id))

    # update cloudfront distribution with the certificate
    reply = task.get_cloudfront_distribution(
            config.cloudfront_distribution_id
        )
    etag = reply["ETag"]
    distribution_config = reply["Distribution"]["DistributionConfig"]

    distribution_config["ViewerCertificate"] = {
        "SSLSupportMethod": "sni-only",
        "MinimumProtocolVersion": "TLSv1.1_2016", 
        "IAMCertificateId": server_certificate_id, 
        "Certificate": server_certificate_id, 
        "CertificateSource": "iam"
    }
    task.update_cloudfront_distribution(
        id=config.cloudfront_distribution_id,
        distribution_config=distribution_config,
        etag=etag)

    print("assigned server certificate {0} to cloudfront distribution {1}"
        .format(server_certificate_id, config.cloudfront_distribution_id))

    if args.remove_certbot_dir:
        task.remove_certbot_dir()

if __name__ == "__main__":
    main()