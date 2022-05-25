from as_xtf_GUI import logger
from paramiko import SSHClient, AutoAddPolicy, SFTPClient
from paramiko.ssh_exception import AuthenticationException
from scp import SCPClient, SCPException

# source code found here: https://hackersandslackers.com/automate-ssh-scp-python-paramiko/


@logger.catch
class RemoteClient:
    def __init__(self, xtf_host, xtf_username, xtf_password, xtf_remote_path, xtf_index_path, xtf_lazy_path):
        self.host = xtf_host
        self.user = xtf_username
        self.password = xtf_password
        self.remote_path = xtf_remote_path
        self.index_path = xtf_index_path
        self.lazy_path = xtf_lazy_path
        self.client = None
        self.scp = None

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
                                look_for_keys=False,
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
                # logger.info(f'INPUT: {cmd} | OUTPUT: {line}')  # This generates a lot of lines in the log file
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
