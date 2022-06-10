from ast import Break
import json
import boto3 
import pandas as pd
import psycopg2
import hashlib
from io import StringIO

queue_url = "http://localhost:4566/000000000000/login-queue"
sqs = boto3.client('sqs', endpoint_url = queue_url)

def receive_sqs_messages(sqs):
    # Creates the list of sqs messages that we want to insert into postgres
    message_list = []
    # This true condition means that as long as there are messages in teh queue we will process them 
    while True:
        delete_list = []
        response = sqs.receive_message(
            QueueUrl=queue_url,MaxNumberOfMessages=10)
        try:
            for message in response["Messages"]:
                body = message["Body"]
                message_list.append(body) # Appends the Body of the sqs message that we actually want
                delete_list.append({ 
                    'Id': message["MessageId"],
                    'ReceiptHandle': message["ReceiptHandle"]
                }) # Appends the id of each message that we will delete from teh queue since we are about to process it 
            if len(delete_list) == 0:
                break
            else: # Deletes all of the messages in the delete list based on their Recepit Handle key 
                for handle in delete_list:
                    sqs.delete_message(
                    QueueUrl = queue_url,
                    ReceiptHandle = handle['ReceiptHandle'])
        except KeyError:
            return message_list # This is janky, but once we are out of messages we will received an HTTP request instead of a message. Since there is no ["Message"] key, I 
            # return the message list

def connect_to_pg(): # self explanatory, this connects to the postgres docker container that the makefile creates 
    conn = None
    try:
        conn = psycopg2.connect(database = "postgres", 
                        user = "postgres", 
                        password = "postgres",
                        host = "localhost",
                        port = 5432)
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    return conn

def copy_from_stringio(conn, df, table): # 
    # save dataframe to an in memory buffer so we don't use disk space. This is limited by the amount of available memory we have to compute
    buffer = StringIO()
    df.to_csv(buffer, index=False,index_label=None, header=False)
    buffer.seek(0)
    
    cursor = conn.cursor()
    try:
        cursor.copy_from(buffer, table, sep=",")
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        
        print("Error: %s" % error)
        conn.rollback()
        cursor.close()
        return 1
    print("copy_from_stringio() done")
    cursor.close()

def main():

    message_list = receive_sqs_messages(sqs=sqs)

    df = pd.DataFrame.from_records(map(json.loads, message_list))

    # Taking the ip and device_id columns to encrypt them with sha256 encoding 
    # We do this by indexing the dataframe (like an excel sheet) by its column names, and setting the columns 
    # themselves to encoded versions of the ip and device data present in each row
    df['hashed_ip'] = df['ip'].apply(lambda x:hashlib.sha256(x.encode()).hexdigest())
    df['hashed_device_id'] = df['device_id'].apply(lambda x: hashlib.sha256(x.encode()).hexdigest())

    # This creates the create_date column in the dataframe to insert it into postgres with a timestamp of when the message was ingested 
    df['create_date'] = pd.to_datetime('today')
    df['create_date'] = df['create_date'].dt.date

    # We create this dataframe in order to remove all columns we do not want to copy into postgres
    df2 = df[['user_id','device_type','hashed_ip','hashed_device_id','locale','app_version','create_date']]


    # # Connects to postgres
    conn = connect_to_pg()

    # Creates a .csv file from the dataframe and holds it in a memory buffer instead of writing it to the disk
    # Then it copies the .csv file into the target postgres table
    copy_from_stringio(conn,df2,'user_logins')
    
    #close the connection with postgres
    conn.close()



if __name__ == "__main__":
    main()