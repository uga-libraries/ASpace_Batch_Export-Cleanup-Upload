import sys
import paramiko
from os import system
from pathlib import Path

from loguru import logger
from paramiko import SSHClient, AutoAddPolicy, RSAKey, SFTPClient
from paramiko.auth_handler import AuthenticationException, SSHException
from scp import SCPClient, SCPException

# source code found here: https://hackersandslackers.com/automate-ssh-scp-python-paramiko/

logger.add(sys.stderr,
           format="{time} {level} {message}",
           filter="client",
           level="INFO")
logger.add(str(Path('logs', 'log_{time:YYYY-MM-DD}.log')),
           format="{time} {level} {message}",
           filter="client",
           level="ERROR")


class RemoteClient:
    def __init__(self, xtf_host, xtf_username, xtf_password, xtf_remote_path, xtf_index_path, xtf_lazy_path,
                 xtf_ssh_key=None):
        self.host = xtf_host
        self.user = xtf_username
        self.password = xtf_password
        self.ssh_key_filepath = xtf_ssh_key
        self.remote_path = xtf_remote_path
        self.index_path = xtf_index_path
        self.lazy_path = xtf_lazy_path
        self.client = None
        self.scp = None
        self.__upload_ssh_key()

    def __get_ssh_key(self):
        # fetch locally stored SSH key
        try:
            self.ssh_key = RSAKey.from_private_key_file(self.ssh_key_filepath)
            logger.info(f'Found SSH key at self {self.ssh_key_filepath}')
        except SSHException as error:
            logger.error(error)
        return self.ssh_key

    def __upload_ssh_key(self):
        try:
            system(f'ssh-copy-id -i {self.ssh_key_filepath} {self.user}@{self.host}>/dev/null 2>&1')
            system(f'ssh-copy-id -i {self.ssh_key_filepath}.pub {self.user}@{self.host}>/dev/null 2>&1')
            logger.info(f'{self.ssh_key_filepath} uploaded to {self.host}')
        except FileNotFoundError as error:
            logger.error(error)

    def connect_remote(self):
        # open connection to remote host
        try:
            self.client = SSHClient()
            self.client.load_system_host_keys()
            self.client.set_missing_host_key_policy(AutoAddPolicy())
            self.client.connect(self.host,
                                port=22,
                                username=self.user,
                                password=self.password,
                                # key_filename=self.ssh_key_filepath,
                                # look_for_keys=False,
                                # allow_agent=False,
                                timeout=10)
            self.scp = SCPClient(self.client.get_transport())
            sftp = SFTPClient.from_transport(self.client.get_transport())
            try:
                sftp.stat(self.remote_path)
            except FileNotFoundError:
                raise AuthenticationException("Remote path does not exist")
            try:
                sftp.stat(self.index_path)
            except FileNotFoundError:
                raise AuthenticationException("Index path does not exist")
            try:
                sftp.stat(self.lazy_path)
            except FileNotFoundError:
                raise AuthenticationException("Lazy index path does not exist")
            return self.client
        except AuthenticationException as error:
            logger.info('Authentication failed: did you enter the correct username and password?')
            logger.error(error)
            self.scp = None
            return error

    def disconnect(self):
        # close ssh connection
        self.client.close()
        self.scp.close()

    def execute_commands(self, commands):
        # execute multiple commands in succession
        if self.client is None:
            self.client = self.connect_remote()
        output_string = ""
        for cmd in commands:
            stdin, stdout, stderr = self.client.exec_command(cmd)
            stdout.channel.recv_exit_status()
            response = stdout.readlines()
            for line in response:
                output_string += f'{line}'
                logger.info(f'INPUT: {cmd} | OUTPUT: {line}')
        return output_string

    def bulk_upload(self, files):
        # upload multiple files to a remote directory
        if self.client is None:
            self.client = self.connect_remote()
        uploads = [self.__upload_single_file(file) for file in files]
        logger.info(f'Uploaded {len(uploads)} files to {self.remote_path} on {self.host}')
        output_upload = f'Uploaded {len(uploads)} files to {self.remote_path} on {self.host}'
        return output_upload

    def __upload_single_file(self, file):
        # upload a single file to a remote directory
        try:
            self.scp.put(file,
                         recursive=True,
                         remote_path=self.remote_path)
        except SCPException as error:
            logger.error(error)
            raise error
        finally:
            return file
