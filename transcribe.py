import boto3
import time
import argparse


parser = argparse.ArgumentParser(description='Batch transcription for files Amazon S3')
parser.add_argument('InputBucket', metavar='in', type=str, help='s3 bucket name with the input audio files')
parser.add_argument('OutputBucket', metavar='out', type=str, help='s3 bucket name to store your output')
parser.add_argument('Region', metavar='rg', type=str, help='region of your AWS configuration')
parser.add_argument('Role', metavar='rl', type=str, help='IAM role name that has the access')
args = parser.parse_args()

input_bucket = args.InputBucket
output_bucket = args.OutputBucket
region = args.Region
role_name = args.Role

''' example inputs
input_bucket = 'elasticbeanstalk-us-west-2-534322506468'
output_bucket = 'testprocessta'
region = 'us-west-2'
role_name = 'TestFullAccessRole'
'''

# clients to be used
iam_client = boto3.client('iam')
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')
transcribe_client = boto3.client('transcribe')

# set up IAM roles
role = iam_client.get_role(RoleName=role_name)
# set up the role specifically for transcribe
transcribe_input_policy = iam_client.create_policy(
    PolicyName='TranscribeInput',
    PolicyDocument="""{
    "Version": "2012-10-17",
    "Statement": {
        "Effect": "Allow",
        "Action": [
            "s3:GetObject",
            "s3:ListBucket"
        ],
        "Resource": [
            "arn:aws:s3:::%s",
            "arn:aws:s3:::%s/*"
        ]
    }
}""" %(input_bucket, input_bucket)
)
input_policy_arn = transcribe_input_policy['Policy']['Arn']
transcribe_output_policy = iam_client.create_policy(
    PolicyName='TranscribeOutput',
    PolicyDocument="""{
    "Version": "2012-10-17",
    "Statement": {
        "Effect": "Allow",
        "Action": [
            "s3:PutObject"
        ],
        "Resource": [
            "arn:aws:s3:::%s/*"
        ]
    }
}""" %(output_bucket)
)
output_policy_arn = transcribe_output_policy['Policy']['Arn']
data_role = iam_client.create_role(
    RoleName='DataAccessRole',
    AssumeRolePolicyDocument="""{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "transcribe.amazonaws.com"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}"""
)
attach_input = iam_client.attach_role_policy(
    RoleName='DataAccessRole',
    PolicyArn=input_policy_arn
)
attach_output = iam_client.attach_role_policy(
    RoleName='DataAccessRole',
    PolicyArn=output_policy_arn
)

# create a lambda to process the transcripts once they are put into the s3 bucket
with open('lambda_function/sentences.zip', 'rb') as f:
    zipped_code = f.read()  # prepare for code upload
lambda_response = lambda_client.create_function(
    FunctionName='ProcessTranscript',
    Runtime='python3.7',
    Role=role['Role']['Arn'],
    Handler='sentences.lambda_handler',
    Code={
        'ZipFile': zipped_code,
    },
    Timeout=200,  # should be enough...
    Layers=['arn:aws:lambda:us-west-2:113088814899:layer:Klayers-python37-pandas:1']
)
lambda_arn = lambda_response['FunctionArn']

# configure Lambda to allow s3 to invoke it
lambda_config = lambda_client.add_permission(
    FunctionName='ProcessTranscript',
    StatementId='AllowS3invoke',
    Action="lambda:InvokeFunction",
    Principal='s3.amazonaws.com',
    SourceArn='arn:aws:s3:::' + output_bucket
)

# configure s3 bucket to send event to fire lambda whenever a json is created
config = s3_client.put_bucket_notification_configuration(
    Bucket=output_bucket,
    NotificationConfiguration={
        'LambdaFunctionConfigurations': [{
            'LambdaFunctionArn': lambda_arn,
            'Events': ['s3:ObjectCreated:*'],
            'Filter': {'Key': {
                'FilterRules': [{'Name': 'suffix', 'Value': '.json'}]
            }}
        }]
    }
)


# prepare for transcription
# read media / vocab files from s3
s3_list = s3_client.list_objects_v2(
    Bucket=input_bucket,
    Delimiter=',',
    EncodingType='url'
)

media_list = []
vocab_file = ()
media_suffix = ('mp3', 'mp4', 'wav', 'flac')
for file in s3_list['Contents']:
    filename = file['Key']
    url = 'https://' + input_bucket + '.amazonaws.com/' + filename
    uri = 'https://s3.' + region + '.amazonaws.com/' + input_bucket + '/' + filename
    if filename.endswith(media_suffix):
        media_list.append((url,uri))
    if filename.endswith('.txt'):
        vocab_file = (url, uri)
print(media_list, vocab_file)


# batch transcribe
# create vocabulary and wait till it's ready
create_response = transcribe_client.create_vocabulary(
    VocabularyName=vocab_file[0].split('.')[-2].split('/')[-1],
    LanguageCode='en-US',
    VocabularyFileUri=vocab_file[1]
)
print('Preparing vocabulary, check update every 30 seconds...')
while True:
    status_response = transcribe_client.get_vocabulary(VocabularyName=vocab_file[0].split('.')[-2].split('/')[-1])
    status = status_response['VocabularyState']
    if status == 'READY':
        print('Vocabulary ready.')
        break
    elif status == 'FAILED':
        print(status['FailureReason'])
        break
    else:
        print('checked update, vocabulary pending...')
        time.sleep(30)


# do transcribe
print('Start transcription jobs...')
job_list = []
for media in media_list:
    job_list.append(media[0].split('.')[-2].split('/')[-1])
    transcribe_response = transcribe_client.start_transcription_job(
        TranscriptionJobName=media[0].split('.')[-2].split('/')[-1],
        LanguageCode='en-US',
        Media={
            'MediaFileUri': media[1]
        },
        OutputBucketName=output_bucket,
        Settings={
            'VocabularyName': vocab_file[0].split('.')[-2].split('/')[-1],
            'ShowSpeakerLabels': False,
            'ShowAlternatives': False
        },
        JobExecutionSettings={
            'AllowDeferredExecution': True,  # probably will not queue but set true anyhow
            'DataAccessRoleArn': data_role['Role']['Arn']
        }
    )

# report transcription status
finished = 0
job_count = len(media_list)
while True:
    print('checking transcription status every 2 minutes...')
    queueing = len(transcribe_client.list_transcription_jobs(Status='QUEUED')['TranscriptionJobSummaries'])
    failed = len(transcribe_client.list_transcription_jobs(Status='FAILED')['TranscriptionJobSummaries'])
    running = len(transcribe_client.list_transcription_jobs(Status='IN_PROGRESS')['TranscriptionJobSummaries'])
    finished = job_count - queueing - failed - running
    print(f"Current status: {finished} finished, {running} in progress, {queueing} in queue, {failed} failed")
    if finished == job_count:
        break
    time.sleep(120)
print('Transcription finished, all transcripts stored in output bucket.')


# clean up temporary access roles and policies
# detach policies with data access role
detach_input_policy = iam_client.detach_role_policy(
    RoleName='DataAccessRole',
    PolicyArn=input_policy_arn
)
detach_output_policy = iam_client.detach_role_policy(
    RoleName='DataAccessRole',
    PolicyArn=output_policy_arn
)
# delete role
delete_role = iam_client.delete_role(
    RoleName='DataAccessRole'
)
# delete policy
delete_input_policy = iam_client.delete_policy(
    PolicyArn=input_policy_arn
)
delete_output_policy = iam_client.delete_policy(
    PolicyArn=output_policy_arn
)

# finished
