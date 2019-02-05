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

CERTBOT_DOMAIN="www.kacon.ch"
CERTBOT_EMAIL="karl.guggisberg@kacon.ch"
# test distribution
CLOUDFRONT_DISTRIBUTION_ID="E2GEKJ7CN252O3"
# production distribution
#CLOUDFRONT_DISTRIBUTION_ID="E2WVJ7WJ8MF8SC"

class CertificateRenewTask:
    certbot_dir = None

    def create_temp_certbot_dir(self):
        """creates a tempory certbot directory"""
        self.certbot_dir = tempfile.mkdtemp(suffix=".certbot")

    def remove_certbot_dir(self):
        """removes the certbot directory"""
        print("info: removing certbot directory '{0}'".format(self.certbot_dir))
        shutil.rmtree(self.certbot_dir)

    def init_certbotdir(self):
        """creates the three subdirectories in the certbot directory,
        unless they already exist"""
        if self.certbot_dir == None:
            self.create_temp_certbot_dir()
        elif not os.path.isdir(self.certbot_dir):
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
            "--domains", CERTBOT_DOMAIN,
            "--email", CERTBOT_EMAIL,
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
        certificate_name = "www_kacon_ch_{0}".format(date_tag)
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
                self.certbot_dir, "config", "live", CERTBOT_DOMAIN,
                "cert.pem")
        )

    def read_private_key(self):
        """reads the content of the private key in 'privkey.pem' and
        replies it as string"""
        return self.read_text_file(
            os.path.join(
                self.certbot_dir, "config", "live", CERTBOT_DOMAIN,
                "privkey.pem")
        )

    def read_certificate_chain(self):
        """reads the content of the certificate chain in 'fullchain.pem'
        and replies it as string"""
        return self.read_text_file(
            os.path.join(
                self.certbot_dir, "config", "live", CERTBOT_DOMAIN,
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

    def publish_certificate(self):
        cloud_front = boto3.client("cloudfront")

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

def test_publish_challenge():
    task = CertificateRenewTask()
    task.init_certbotdir()

    challenge_info = {
        "challenge_content": "SYfYtzd440O2T0TH2RK-FPbHyXm8207nfQ_Prv9Ry1A.BJSMLJWW-Rr-xCmq_ejfXRmwBEY2KDY6nxY8dl5NIpM",
        "challenge_url": "http://www.kacon.ch/.well-known/acme-challenge/SYfYtzd440O2T0TH2RK-FPbHyXm8207nfQ_Prv9Ry1A"
    }
    task.publish_challenge(challenge_info)

def test_cloudfront_distribution():
    task = CertificateRenewTask()
    reply = task.get_cloudfront_distribution(CLOUDFRONT_DISTRIBUTION_ID)
    print(json.dumps(reply, indent=2, default=str))
    etag = reply["ETag"]
    distribution_config = reply["Distribution"]["DistributionConfig"]

    certificate_id="ASCAJDFKBC7RGTX2YGBCQ"
    distribution_config["ViewerCertificate"] = {
        "SSLSupportMethod": "sni-only",
        "MinimumProtocolVersion": "TLSv1.1_2016", 
        "IAMCertificateId": certificate_id, 
        "Certificate": certificate_id, 
        "CertificateSource": "iam"
    }
    task.update_cloudfront_distribution(
        id=CLOUDFRONT_DISTRIBUTION_ID,
        distribution_config=distribution_config,
        etag=etag)

def main():
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

    args = parser.parse_args()

    task = CertificateRenewTask()
    task.certbot_dir = args.certbot_dir
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
    reply = task.get_cloudfront_distribution(CLOUDFRONT_DISTRIBUTION_ID)
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
        id=CLOUDFRONT_DISTRIBUTION_ID,
        distribution_config=distribution_config,
        etag=etag)

    print("assigned server certificate {0} to cloudfront distribution {1}"
        .format(server_certificate_id, CLOUDFRONT_DISTRIBUTION_ID))

    if args.remove_certbot_dir:
        task.remove_certbot_dir()

if __name__ == "__main__":
    main()