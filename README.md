# Think-aloud data processing with Amazon Web Services
An almost automated workflow to process think-aloud data powered by Amazon Web Services (S3, Lambda, Transcribe, Lex)

## Requirements
- AWS account, apparently 
- Configured AWS CLI 
- Boto3  

## Languages

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
`custom_vocabulary.txt` should be in the Table Format  
Audio files can be: `.mp3, .mp4, .wav, .flac`  
`intents` contains the `.txt` files  
**Note:** Intents don't have to be in the same buckets as the audio and vocabulary files, but they should be all stored under the sub-folder of `intents`  
 


## Some AWS access configuration
You will need your AWS region name to run `transcribe.py`  
You will also need a IAM role that has the following policies attached:
- AWSLambdaExecute
- AWSLambdaBasicExecutionRole
- AmazonLexRunBotsOnly  

This can be done via AWS CLI or from the IAM console.  
**Note**: `transcribe.py` will create a temporary data-access-role that allow Transcribe to read and write into your S3 bucket when jobs are queued. This role will be deleted as the script finishes. 

## Run


## Outputs  


## Human intervention
Amazon is quite smart but not perfect. 
