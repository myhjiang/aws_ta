# Simple think-aloud data processing with Amazon Web Services
An almost automated workflow to process think-aloud data powered by Amazon Web Services (S3, Lambda, Transcribe, Lex).


The simple workflow: transcription -> segmentation -> encoding

## Requirements
- AWS account
- Configured AWS CLI 
- [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html)    

## Languages
AWS Transcribe supports multiple languages, but Lex only supports English. Thus this whole workflow onnly works for English (US), while the transcription part can be used for other languages supported by Amazon. 

## Prepare the data
All inputs files should be stored in an S3 with the following structure:   
```
S3 Bucket 
├── intents  
│   └── code_name.txt  
│   └── code_name.txt    
│   └── ...  
├── custom_vocabulary.txt  
├── think_aloud_audio.mp3  
├── another_audio.mp3  
├── ... 
```  
`custom_vocabulary.txt` should be in the [Table Format](https://docs.aws.amazon.com/transcribe/latest/dg/how-vocabulary.html#create-vocabulary-table)  

Audio files can be: `.mp3, .mp4, .wav, .flac` 

`intents` contains the `.txt` files  
**Note:** Intents don't have to be in the same buckets as the audio and vocabulary files, but they should be all stored under the sub-folder of `intents`  
Intents should follow the naming of `code_name.txt`, where `code` is a simple code you want to use for your intent, and `name` is the name of the intent. For example, `I_mapinteraction.txt` represents an intent called "mapinteraction" with the code I.   
The intent file should contain sample utterances separated by line break. 
For example, the `I_mapinteraction.txt` has the following content:  
```
zoom in.
I'll zoom out a little bit more.
I'm click the button to...
...
```

 
## Some AWS access configuration
You will need your AWS region name to run `transcribe.py`  
You will also need a IAM role that has the following policies attached:
- AWSLambdaExecute
- AWSLambdaBasicExecutionRole
- AmazonLexRunBotsOnly  

This can be done via AWS CLI or from the IAM console.  

**Note**: `transcribe.py` will create a temporary data-access-role that allow Transcribe to read and write into your S3 bucket when jobs are queued. This role is attached with [these policies provided by Amazon](https://docs.aws.amazon.com/transcribe/latest/dg/job-queuing.html). This role will be deleted as the script finishes. 

## Run
### transcribe.py
**Arguments:** 
- InputBucket (in): name of the bucket where you store your custom vocabulary and audio files 
- OutputBucket (out): name of the bucket to store transcripts, can be the same with InputBucket  
- Region (rg): the region of your CLI,  **has to be the same with the region of the buckets!**
- Role (rl): the IAM role that has the accesses mentioned above. 

For example: `$ python transcribe.py bucket1 bucket2 us-west-2, FullAccessRole `

### build_bot_s3.py
**Arguments:**  
- Bucket (b): name of the bucket where the intent folder is stored.  
- BotName (n): name of the bot 

For example: `$ python build_bot_s3.py mybucket mybot`  

### encode.py
**Arguments:**  
- InputBucket (in): name of the bucket that stores the transcript segments produced by `transcribe.py`  
- Role (rl): the same role name used for `transcribe.py`  
- BotName (bn): name of the Lex bot
- BotAlias (ba): alias name of the Lex bot. If the bot is created with `build_bot_s3.py`, then the alias is `[botname]_alias`  

For example: `$ python encode.py mybucket FullAccessRole mybot mybot_alias`  

## Outputs and intermediate results 
`transcribe.py` will write transcripts in `.json` as the [AWS default format](https://docs.aws.amazon.com/transcribe/latest/dg/getting-started-cli.html), as well as segmented transcripts (by sentence) in `.tsv` to your output S3 bucket. Segmented transcripts follow the format of:   

| start_time| end_time | content |
| ---------:| --------:|-----|
| 2.11 | 7.17 | and therefore I also need to old map |

`build_bot_s3.py` will create intents and build a Lex chatbot. You can test, modify and rebuild the bot at the Lex Console. 

`encode.py` will write coded transcript sentences to your S3 bucket as `tsv` files. They follow the format of:   

| start_time| end_time | content | BotCode |
| ---------:| --------:|-----|-----|
| 2.11 | 7.17 | and therefore I also need to old map | A |


## Human intervention
Amazon is quite smart but not perfect. Thus human intervention is recommended as intermediate results are produced. 

Modifying the transcripts: you can modify the tsv transcript segments by downloading and editing it in your text/sheet editor, or you can use [this tool](https://github.com/samFredLumley/aws-transcription-editor) to modify the json transcript. Once you upload the modified json to the same bucket, an new segment file will be automatically generated.  

Testing the bot and modifying the intents: this is easiest done through the Lex console. Do not run the build bot script again after you have created intents or bots with the same name.  

## Sources and AWS docs 
- [Amazon Transcribe](https://docs.aws.amazon.com/transcribe/latest/dg/what-is-transcribe.html)  
- [Amazon Lex](https://docs.aws.amazon.com/lex/latest/dg/what-is.html)    
- [Amazon S3 Simple Storage](https://docs.aws.amazon.com/AmazonS3/latest/dev/Welcome.html)  
- [Amazon IAM](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html)  
