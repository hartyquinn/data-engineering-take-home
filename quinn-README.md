# Plan 
## Step 1: Reading Messages from the Queue
    I am going to use the python package Boto3 to receive messages from the queue. Boto3 is an AWS SDK for python, I can use it to interact with services created by localstack. 
    How it will work: I will receive 10 messages at a time from the SQS queue with a python function. The body of the messages will be appended to a list, and the ids will be appended to a lsit for deletion.This function will loop through all the messages in the queue until it no longer receives message JSON. 
## Step 2: Data Structures
    Since we are inserting these messages into a table in postgres, I believe the best way to do that is in a row-based relational data structure. I will normalize the batch of JSON messages using pandas. 
## Step 3: Masking PII so that duplicate messages can be identified 
    I will use pandas to access the columns with PII and then mask it with sha256 encryption, then remove the columns that had the unmasked values. This is my first time encrypting PII data. 
## Step 4: Connecting and writing to psql 
    I am going to use the python package psycopg2 to connect and write to postgres. It is very easy to create a connection to postgres and then insert/update records with this python package. 
    One big issue I ran into is that the app_version field is cast as an integer. I don't see a reason for this, as there is no reason why we would be doing math to the app version that I can think of. I changed the target table DDL to varchar(10) to make this easier. 
## Step 5: Where does the App live? 
    My application will run on my local python machine. I realize that this is not how it will work in production. I was completely unfamiliar with localstack and SQS so I decided that the best use of my time would be to figure out how to use boto3 to process the messages & write them to postgres. I will list further improvements in the Improvements section.

## Improvements 
    Breaking up the one large python script into multiple smaller lambda functions that trigger off each other. Making sure that they all have cloudwatch logging setup so that if anything goes wrong, the problem can easily be addressed. Adding intermediate storage after reading messages from the SQS queue as an s3 bucket so that there is raw data available in case thing go wrong inserting data into postgres. That way we can handle each SQS message batch with intermediate storage. I have used Lambdas on AWS cloud, but I thought that my time would be better spent completing the objectives than learning how to use localstack lambdas and messing with docker. 

    The improved lambda architecture would go something like this:

    SQS Queue Gets Messages -> SQS processing lambda -> S3 bucket with csvs -> S3 to Postgres Lambda -> Rows inserted in Postgres 

    Since we only have 100 messages, this solution is not scalable. Depending on the volume of messages and how often we receive them, we may want to use kinesis to stream the messages in batches directly into redshift as a scalable solution. Depending on how we wanted to store the data and how many backups of the messages we wanted to keep, we could save batches of messages as .csv files in s3 and then perform copy into statements. This would also translate well to redshift, if we wanted to scale our data warehouse up. 

    Kinesis/Redshift Architecture 

    SQS Queue Trigger -> SQS Write to Kinesis Lambda -> Kinesis to Firehose -> Firehose to S3 Bucket -> Copy from S3 to Redshift Table 

## Instructions 
    Navigate to however you execute python code and run process_messages.py, as all requried packages should've been installed by the Makefile command make pip install. 
