import boto3
from os import listdir
from os.path import isfile, join
import time
import argparse

parser = argparse.ArgumentParser(description='Create Amazon Lex bot with intent text files')
parser.add_argument('IntentFolder', metavar='f', type=str, help='Path to folder where the intents are saved')
parser.add_argument('name', metavar='n', type=str, help='Name of the bot to be created')
args = parser.parse_args()

intent_folder = args.IntentFolder
bot_name = args.name

# initialize Lex modelling client
model_client = boto3.client('lex-models')


# parse and create intent from text file
def create_intent(filename):
    code_id = filename.split('_')[0]
    intent_name = filename.split('_')[1].split('.')[0]
    with open(join(intent_folder, filename)) as f:
        sample_utterance = [line.rstrip('\n') for line in f]
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
    return {'intentName': intent_name, 'intentVersion': intent_version}


print('Creating intents...')
intent_files = [f for f in listdir(intent_folder) if isfile(join(intent_folder, f))]
intents = []
for file in intent_files:
    intents.append(create_intent(file))
print('Intents created')


# create new bot
create_bot = model_client.put_bot(
    name=bot_name,
    locale='en-US',
    intents=intents,
    abortStatement={
        'messages': [
            {
                'contentType': 'PlainText',
                'content': 'U',
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
