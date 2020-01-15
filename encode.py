import boto3
import time
import json


parser = argparse.ArgumentParser(description='Batch encoding with Lex bot')
parser.add_argument('InputBucket', metavar='in', type=str, help='s3 bucket name with the input audio files')
parser.add_argument('Role', metavar='rl', type=str, help='IAM role name that has the access')
parser.add_argument('BotName', metavar='bn', type=str, help='Name of the Lex bot')
parser.add_argument('BotAlias', metavar='ba', type=str, help='Alias of the Lex bot')
args = parser.parse_args()

input_bucket = args.InputBucket
role_name = args.Role
bot_name = args.BotName
bot_alias = args.BotAlias

''''example inputs
input_bucket = ''
bot_name = ''
bot_alias = ''
role_name = 'LambdaFullAccessRole'
'''

# clients needed
iam_client = boto3.client('iam')
lambda_client = boto3.client('lambda')
s3_client = boto3.client('s3')

# get role
lambda_role = iam_client.get_role(RoleName=role_name)

# create lambda to process files in S3
with open('lambda_function/query_bot.zip', 'rb') as f:
    zipped_code = f.read()  # prepare for code upload
lambda_response = lambda_client.create_function(
    FunctionName='CodeSentence',
    Runtime='python3.7',
    Role=lambda_role['Role']['Arn'],
    Handler='query_bot.lambda_handler',
    Code={
        'ZipFile': zipped_code,
    },
    Timeout=900,
    Layers=['arn:aws:lambda:us-west-2:113088814899:layer:Klayers-python37-pandas:1']
)

# check upload status
while True:
    print('Checking status of Lambda function every 30 seconds...')
    status_response = lambda_client.get_function(FunctionName='CodeSentence')
    if status_response['Configuration']['State'] == 'Failed':
        print('Failed to create Lambda function. ')
        quit()
    elif status_response['Configuration']['State'] == 'Pending':
        time.sleep(30)
    else:
        break
print('Lambda function created, ready to code sentences.')
# quit()  # todo: remove it at the end

# get objects from S3, loop, call Lambda
# otherwise Lambda might timeout if all objects are processed in one call
s3_list = s3_client.list_objects_v2(
    Bucket=input_bucket,
    Delimiter=',',
    EncodingType='url'
)
for file in s3_list['Contents']:
    filename = file['Key']
    # invoke lambda
    if filename.endswith('.csv'):
        print(f"Processing file {filename}...")
        payload = {'bucket': input_bucket, 'file_key': filename, 'output_file': 'coded_'+filename,
                   'bot': {'name': bot_name, 'alias': bot_alias}}
        invoke_response = lambda_client.invoke(
            FunctionName='CodeSentence',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
    else:
        continue

print('Coding completed.')
