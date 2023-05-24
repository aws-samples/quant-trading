import os
# import boto3
# import requests
# import zipfile
# import io
import subprocess
# import shutil
# import urllib3

# CLONE_REPO = os.environ['CLONE_REPO']
CC_REPO_NAME = os.environ['DEST_REPO']
# KEY = os.environ['AWS_ACCESS_KEY_ID']
# SECRET_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
REGION = os.environ['REPO_REGION']
CC_REPO = f'codecommit::{REGION}://{CC_REPO_NAME}'
# TMP_PATH = "aws-quant-tmp"

def handler(event, context):
    if event['RequestType'] == 'Create':
        # Clone empty code commit...
        print('cloning empty repo...')
        res = subprocess.run(["git", "clone", CC_REPO, "/tmp/aws-quant"], capture_output=True)
        print(res.stdout)
        print(res.stderr)
        # copy baseline repo to code commit dir...
        print('moving baseline repo to code commit git...')
        res = subprocess.run(["cp", "-a", "/var/task/base/.", "/tmp/aws-quant/"], capture_output=True)
        print(res.stdout)
        print(res.stderr)
        # Push to private repo...
        print('pushing changes to code commit...')
        res = subprocess.run(["git", "push", CC_REPO, "--all"], cwd='/tmp/aws-quant', capture_output=True)
        print(res.stdout)
        print(res.stderr)


def configureCli():
    print(f'running aws configure commands... {REGION} {KEY} {SECRET_KEY}')
    subprocess.run(["aws", "configure", "set", "region" , REGION])
    subprocess.run(["aws", "configure", "set", "aws_access_key_id" , KEY])
    subprocess.run(["aws", "configure", "set", "aws_secret_access_key" , SECRET_KEY])
    print('aws cli configured')

# def downloadRepo():
    # subprocess.run(["rm", "-rf", "/tmp/*"])
    # subprocess.run(["cd", "/tmp"])
    # subprocess.run(["git", "clone", CLONE_REPO, TMP_PATH])
    # r = requests.get(CLONE_REPO)
    # z = zipfile.ZipFile(io.BytesIO(r.content))
    # z.extractall(TMP_PATH)
    # zip = '/tmp/tmp.zip'
    # http = urllib3.PoolManager()
    # r = http.request('GET', CLONE_REPO)
    # with open(zip, 'wb') as out:
    #     while True:
    #         data = r.read(64)
    #         if not data:
    #             break
    #         out.write(data)
    # shutil.unpack_archive(zip, TMP_PATH)

# def create_codecommit_repo_commit(repo_name, branch_name, code_folder):
#     client = boto3.client('codecommit')
#     parent_folder = os.path.join(code_folder, repo_name)
#     putFilesList = []
#     for (root, folders, files) in os.walk(parent_folder):
#         for file in files:
#             print(f'Making entry for file: ${file}')
#             file_path = os.path.join(root, file)
#             with open(file_path, mode='r+b') as file_obj:
#                 file_content = file_obj.read()
#             putFileEntry = {'filePath': str(file_path).replace(parent_folder, ''),
#                             'fileContent': file_content}
#             putFilesList.append(putFileEntry)

#     response = client.create_commit(repositoryName=repo_name, branchName=branch_name, putFiles=putFilesList)
#     print(response)