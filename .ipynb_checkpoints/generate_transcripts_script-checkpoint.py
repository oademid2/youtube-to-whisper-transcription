#!/usr/bin/env python
# coding: utf-8

# In[1]:


from dotenv import load_dotenv # add this line
load_dotenv()

# In[2]:


import whisper
import torch  # install steps: pytorch.org

from tqdm.auto import tqdm  # !pip install tqdm
from pathlib import Path

import os
import json

import time

# In[3]:


device = "cuda" if torch.cuda.is_available() else "cpu"

model = whisper.load_model("base").to(device)

# In[4]:


import os
import googleapiclient.discovery
import urllib.parse as p
import pandas as pd
from youtube_transcript_api import YouTubeTranscriptApi
import json
def obj_dict(obj):
    return obj.__dict__

import subprocess
import requests
import re
import youtube_dl

# In[5]:


from pytube import YouTube  # !pip install pytube
from pytube.exceptions import RegexMatchError
from tqdm.auto import tqdm  # !pip install tqdm


# In[6]:


# Disable OAuthlib's HTTPS verification when running locally.
# *DO NOT* leave this option enabled in production.

api_service_name = "youtube"
api_version = "v3"
DEVELOPER_KEY = os.getenv('DEVELOPER_KEY')

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
youtube = googleapiclient.discovery.build(
    api_service_name, api_version, developerKey = DEVELOPER_KEY)

# In[7]:


import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Use a service account.
cred = credentials.Certificate('../analytics-c4f16-firebase-adminsdk-plgdk-2a3d65b3a8.json')

app = firebase_admin.initialize_app(cred)

db = firestore.client(app)
batch = db.batch()

# In[8]:


def check_nested_dict_keys(dic, keys):
    d = dic
    for key in keys:
        if key in d.keys():
            d = d[key]
            continue
        else:
            return dic['snippet']['thumbnails']['default']['url'] 
        
    return d

# In[9]:


class DatabaseHelper():
    
    def __init__(self, db):
        self.db = db
        self.CHANNELS = None
        self.VIDEOS = {}
    
    def get_channel_db(self,db):
        docs = self.db.collection(u'channels').stream()
        channelsCollection = {}
        for doc in docs:
            channelsCollection[doc.id]=doc.to_dict()
        return channelsCollection
    
    def set_channels(self):
        self.CHANNELS = self.get_channel_db(db)
        
    def set_videos(self,_id,videos):
        self.VIDEOS[_id] = videos

    def get_channel_videos(self,channelId):

        docs = db.collection(u'Videos').order_by('publishedAt', direction=firestore.Query.DESCENDING).where(u"channelID",u"==",u"{}".format(channelId)).stream()

        collection = []
        for doc in docs:
            vid =doc.to_dict()
            if "#shorts" not in vid['title']:
                collection.append(vid)
        return collection
    
    def get_channel_doc(self, video_url, allChannels):
        channel_id = video_url_to_channel_id(video_url)
        print(channel_id)

        for record in allChannels.values():
            if record['channelId'] == channel_id:
                print("Channel {} already exists.".format(record['title']))
                return record

        channelToAdd = generate_channel_json(video_url)    


        add = input("Create channel for url ? (0 for no, any other key for yes)".format(channelToAdd['title']))

        if add == 0:
            print("No channel for url")
            return


        docRef = db.collection(u"channels").document(u"{}".format(channelToAdd['channelId'])).set(channelToAdd)
        print("Channel {} is created.".format(channelToAdd['title']))
        return channelToAd

   
    # In[10]:


def generate_channel_json(sourceValue, source="url"):
    
    if source=="id":
        channel_id = sourceValue
    elif source=="url":
        video_url = sourceValue
        channel_id = video_url_to_channel_id(video_url)
    else:
        raise Exception("{} not a valid source.".format(source))
            
    request = youtube.channels().list(
            part="snippet,contentDetails",
            id=channel_id
        )
    response = request.execute()
    
    channel_df = {}#pd.DataFrame(columns=['channelId', 'title', 'uploads','description','thumbnail'])
    channel_df['channelId'] = channel_id
    channel_df['title'] = response['items'][0]['snippet']['title']
    channel_df['uploads'] = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    channel_df['description'] = response['items'][0]['snippet']['description']
    channel_df['thumbnail'] = check_nested_dict_keys(response['items'][0],["snippet","thumbnails","high","url"])
    channel_df['videos'] = []
    
    #full_channel_df = pd.concat([full_channel_df, pd.DataFrame.from_dict(channel_df)])

    return channel_df

def video_url_to_channel_id(video_url):
    video_param_from_url = video_url.split("/watch?v=")[1].split("&")[0]
    request = youtube.videos().list(
            part="snippet,contentDetails",
            id=video_param_from_url
        )
    response = request.execute()
    channel_id = response['items'][0]['snippet']['channelId']
    return channel_id


def get_channel_doc(video_url, allChannels):
    channel_id = video_url_to_channel_id(video_url)
    print(channel_id)
    
    for record in allChannels.values():
        if record['channelId'] == channel_id:
            print("Channel {} already exists.".format(record['title']))
            return record

    channelToAdd = generate_channel_json(video_url)    


    add = input("Create channel for url ? (0 for no, any other key for yes)".format(channelToAdd['title']))

    if add == 0:
        print("No channel for url")
        return
    

    docRef = db.collection(u"channels").document(u"{}".format(channelToAdd['channelId'])).set(channelToAdd)
    print("Channel {} is created.".format(channelToAdd['title']))
    return channelToAdd

# In[11]:


def get_uploads_id(youtube, channel_id):
    request = youtube.channels().list(
            part="snippet,contentDetails",
            id=channel_id
        )
    response = request.execute()
    return response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

def get_uploaded_videos_response(youtube, channel_id,**args):
    
    playlist_id = get_uploads_id(youtube, channel_id)
    max_total=args.get("max_total") if args.get("max_total") else 1000
    oldest_date=args.get("oldest_date") if args.get("oldest_date") else False

    
    params = {
        "part":"snippet,contentDetails",
        "playlistId": playlist_id,
        "maxResults": 50
    }
    
    uploaded_videos_content_details_list = []

    while True:
        response = youtube.playlistItems().list(**params).execute()
        
        
        if oldest_date:
                
            oldestResponseDate = response.get('items')[-1]['snippet']['publishedAt'].split("T")[0]
            if oldestResponseDate <= oldest_date:
                add_response = []
                for r in response.get('items'):
                    date = r['snippet']['publishedAt'].split("T")[0]
                    if date <= oldest_date:
                        break
                    else:
                        add_response.append(r)
                videos_list = uploaded_videos_content_details_list + add_response
                print("New videos found: {}".format(len(videos_list)))
                print("Newest video: {}, {}".format(videos_list[0]['snippet']['title'],videos_list[0]['snippet']['publishedAt']))
                print("Oldest video: {}, {}".format(videos_list[-1]['snippet']['title'],videos_list[-1]['snippet']['publishedAt']))


                return videos_list

      
        uploaded_videos_content_details_list = uploaded_videos_content_details_list + response.get('items')
        
        if (max_total and len(uploaded_videos_content_details_list) >= max_total):
            return uploaded_videos_content_details_list[:max_total]
     
        elif 'nextPageToken' in response.keys():
            params['pageToken'] = response['nextPageToken']
            continue
        else:
            break

    print("Videos retreived.")
    return uploaded_videos_content_details_list

def getYoutubeDuration(videoId):
    responseVideoDetails = youtube.videos().list( part="contentDetails",id=videoId).execute()
    durationResponse=responseVideoDetails['items'][0]['contentDetails']['duration']

    duration_string = durationResponse.replace('PT',"")
    number_values = re.findall('\d+',duration_string)
    symbols_available= ''.join([i for i in duration_string if not i.isdigit()])
    symbol_map = {}
    for symbol in 'HMS':
        index = symbols_available.find(symbol)
        if index > -1:
            symbol_map[symbol] = number_values[index]

    duration = 0


    for idx in symbol_map:
        if idx == "H":
            duration = int(symbol_map[idx])*60*60 + duration
        if idx == "M":
            duration = int(symbol_map[idx])*60 + duration
        if idx == "S":
            duration = int(symbol_map[idx]) + duration
            
    return duration

def video_response_list_to_list_of_dicts(response_list):
    
    list_of_dicts = []
    for x in response_list:
        if "#shorts" in x['snippet']['title']:
            continue
            
        video_df = {}
        video_df['id'] = x['id']
        video_df['videoId'] = x['contentDetails']['videoId'] 
        video_df['title'] = x['snippet']['title'] 
        video_df['description'] = x['snippet']['description'] 
        video_df['thumbnail'] = check_nested_dict_keys(x,["snippet","thumbnails","maxres","url"])      
        video_df['channelID'] = x['snippet']['channelId'] 
        video_df['videoId'] = x['contentDetails']['videoId'] 
        video_df['publishedAt'] =x['snippet']['publishedAt'].split("T")[0] 
        video_df['videoUrl'] = "https://www.youtube.com/watch?v={}".format(x['contentDetails']['videoId'] )
        video_df['duration'] = getYoutubeDuration(x['contentDetails']['videoId']  )
        
        video_df['text'] = ''
#         video_df['assemblySentences'] ='' 
#         video_df['assemblyText'] ='' 
#         video_df['availability']=''
#         video_df['assemblyId'] = ''
#         video_df['ytaTranscript'] = ''
#         video_df['mainTranscript'] = ''
#         video_df['ytaAvailability'] = ''


        list_of_dicts.append(video_df)


    return list_of_dicts

# In[12]:


def pullChannel(url, DB, oldest_date=None):

    #Create channel
    channel = get_channel_doc(url,DB.CHANNELS)
    
    videos_collections= DB.get_channel_videos(channel['channelId'])#load all videos
    
    DB.set_videos(channel['channelId'],videos_collections)
    #check for videos not yet uploaded

    if videos_collections and oldest_date:
        oldest_date = videos_collections[0]['publishedAt']
    else:
        oldest_date = None
    new_video_responses = get_uploaded_videos_response(youtube, channel['channelId'],
                                               oldest_date=oldest_date)

    list_of_new_video_responses_as_dicts = video_response_list_to_list_of_dicts(new_video_responses)


    return channel, list_of_new_video_responses_as_dicts

#add videos to transcript execution

# In[13]:


def getCost(videoList):
    cost = 0
    for vid in videoList:
        cost = vid['duration']*0.00025 + cost
    return cost

# In[14]:


def transcript_object(video, text, segments,source):
    item = {}
    item['videoId'] = video['videoId']
    item['transcriptId'] = 'TRANSCRIPT_'+video['videoId']
    
    keys = ['start','end','text','id']
    segments = result['segments']
    item['transcript'] = [{ keep: item[keep] for keep in keys } for item,i in zip(segments,range(len(segments)) )]
    item['fullTranscript'] = result
    item['text'] = text
    item['source'] = source

    return item

# In[15]:


def get_audio(url,_id):
    yt = YouTube(url)
    video = yt.streams.filter(only_audio=True).first()
    out_file=video.download(output_path="audio_files")
    base, ext = os.path.splitext(out_file)
    new_file = 'audio_files/'+_id+'.mp3'
    os.rename(out_file, new_file)
    a = new_file
    return a

def transcribe(video):
    
    metric = {}
    result = {}
    _id = video['videoId']


    try:
        start = time.time()

        get_audio(video['videoUrl'],_id)
        print('Downloaded {}'.format(video['videoId']))


        # transcribe to get speech-to-text data
        result = model.transcribe('audio_files/{}.mp3'.format(_id))

        # add results to data list
        with open('transcript_files/{}.json'.format(_id), 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        os.remove("audio_files/{}.mp3".format(_id))
        source = "whisper"
        print('Transcribed {}'.format(video['videoId']))



    except Exception as e: # work on python 3.x

        print("video error: {}".format(_id))

     
        try:
            print('Could not get streaming data. Attempting assembly...')
            ydl_opts = {'format': 'bestaudio'}


            ydl =youtube_dl.YoutubeDL(ydl_opts)

            videoUrl = video['videoUrl']
            info = ydl.extract_info(videoUrl, download=False)
            audioUrl = info['formats'][0]['url']
            requestForTrancript = postTranscript(audioUrl)
            source = "pendng"
        except Exception as e: # work on python 3.x
            print('Could not get assembly data.')

            source = "fail"


    
    metric['id'] = _id
    metric['time'] = time.time() - start
    
    return result, metric,source



def TranscribeList(l,x):
    data = []
    metrics= []
    done = []
    i=0
    for doc in l:

        if doc['videoId'] not in done:
            print(x,": ",i)
        else:
            print("already transcribed.")
            continue
        i = i+1

        result, metric, source = transcribe(doc)

        if source == "whisper":
            data.append(result)
            metrics.append(metric)
            

            doc['text'] = result['text']
            transcript = transcript_object(doc, result['text'],result, source)

            docRef = DB.db.collection(u"Videos").document(u"{}".format(doc['videoId'])).set(doc)
            docRef = DB.db.collection(u"Transcripts").document(u"{}".format(doc['videoId'])).set(transcript)

            done.append(doc)
        

        else:
            doc['text'] = 'error'
            #transcript = transcript_object(doc, result['segments'], source)

            docRef = DB.db.collection(u"Videos").document(u"{}".format(doc['videoId'])).set(doc)
    #         docRef = DB.db.collection(u"Transcripts").document(u"{}".format(doc['videoId'])).set(transcript)


