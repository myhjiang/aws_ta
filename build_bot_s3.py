import boto3
import time
import argparse

parser = argparse.ArgumentParser(description='Create Amazon Lex bot with intent text files')
parser.add_argument('Bucket', metavar='b', type=str, help='bucket name where the intents are stored')
parse.add_argument('BotName', metvar='n', type=str, help="Name of the bot to be built")
args = parser.parse_args()
input_bucket = args.Bucket
bot_name = args.BotName

'''sample input
input_bucket = 'testprocessta'
'''

# client needed: s3 and Lex modelling
s3_client = boto3.client('s3')
model_client = boto3.client('lex-models')


# read intent files from s3
s3_list = s3_client.list_objects_v2(
    Bucket=input_bucket,
    Delimiter=',',
    EncodingType='url',
    Prefix='intents/'
)

print('Creating intents...')
intent_list = []
for file in s3_list['Contents']:
    filename = file['Key'].split('/')[-1]
    if filename.endswith('.txt'):
        code_id = filename.split('_')[0]
        intent_name = filename.split('_')[1].split('.')[0]
        get_intent = s3_client.get_object(Bucket=input_bucket, Key=file['Key'])
        intents = get_intent['Body'].iter_lines()  # Stream byte
        sample_utterance = [line.decode('utf-8') for line in intents]

        # put intent
        put_intent = model_client.put_intent(
            name=intent_name,
            sampleUtterances=sample_utterance,
            conclusionStatement={
                'messages': [
                    {
                        'contentType': 'PlainText',
                        'content': code_id,
                        'groupNumber': 1
                    }
                ]
            },
            fulfillmentActivity={'type': 'ReturnIntent'}
        )
        intent_version = put_intent['version']
        intent_list.append({'intentName': intent_name, 'intentVersion': intent_version})
print('Intents created')


# create new bot
create_bot = model_client.put_bot(
    name=bot_name,
    locale='en-US',
    intents=intent_list,
    abortStatement={
        'messages': [
            {
                'contentType': 'PlainText',
                'content': '   ',
            }
        ]
    },
    processBehavior='BUILD',
    childDirected=False
)
print('Building the bot... Check update every 30 seconds...')
while True:
    bot_status = model_client.get_bot(
        name=bot_name,
        versionOrAlias='$LATEST'
    )
    if bot_status['status'] == 'READY':
        print('Bot successfully built and is now ready.')
        break
    if bot_status['status'] == 'BUILDING':
        print('Bot is being built...')
        time.sleep(30)
    if bot_status['status'] == 'FAILED':
        print('Failed to build bot.')
        print(bot_status['failureReason'])
    else:
        print('Something went wrong while building bot. Check out at AWS Console')

# create bot alias and publish bot
print('Creating alias for bot...')
create_alias = model_client.put_bot_alias(
    name=bot_name + '_alias',
    botVersion='$LATEST',
    botName=bot_name,
)
print('Alias created and Lex bot is now ready to use.')
print(f"Bot information: bot name: {bot_name}, alias name: {bot_name+'_alias'}")
