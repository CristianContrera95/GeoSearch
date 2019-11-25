from __future__ import print_function 

import pickle 
import os.path
import sys
import json
import time
from math import pi, sin, cos, sqrt, atan2, radians
from datetime import datetime as dt
from functools import partial
from httplib2 import Http

from googleapiclient.discovery import build 
from google_auth_oauthlib.flow import InstalledAppFlow 
from google.auth.transport.requests import Request
from apiclient.http import MediaFileUpload
from googleapiclient.http import BatchHttpRequest 


# Constants to use for API
vervose = False
all_images = False
recursive = True

CRED_DIR = 'creds'
OUTPUT_DIR = 'data'
JSON_FILENAME = 'images_data_{}.json'.format(dt.now().strftime("%d-%m-%y_%H-%M-%S"))
DRIVE_DIR = '0AMjJ9wCLSgjJUk9PVA'
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/drive.metadata']

API_VERSION = 'v3'
SPACES = 'drive'

"""
OTHER SCOPES: 
['https://www.googleapis.com/auth/drive',
 'https://www.googleapis.com/auth/drive.file',
 'https://www.googleapis.com/auth/drive.appdata',
 'https://www.googleapis.com/auth/drive.scripts',
 'https://www.googleapis.com/auth/drive.metadata']
"""
#-------------------------------------------------------------------------------------------------------


# Functions to performed images search
def print_metadata(data, tabs=0):
    if isinstance(data, dict):
        t = "\t"
        for item in data.keys():
            if isinstance(data[item], dict):
                print('{}{}:'.format(t*tabs, item))
                print_metadata(data[item], tabs+1)
            else:
                print('{}{}: {}'.format(t*tabs, item, data[item]))
        print('\n')
    elif isinstance(data, list):
        for item in data:
            print_metadata(item)


def meters_to_cordinates(lat, lon, mts):
    r_earth = 6378 * 1000  # earth radius in mts
    new_lat = lat  + (mts / r_earth) * (180 / pi);
    new_lon = lon + (mts / r_earth) * (180 / pi) / cos(lat * pi/180);
    return new_lat, new_lon


def calculate_distance(coordinates1, coordinates2):
    r_earth = 6378 * 1000  # earth radius in mts
    lat1 = radians(coordinates1[0])
    lon1 = radians(coordinates1[1])
    lat2 = radians(coordinates2[0])
    lon2 = radians(coordinates2[1])
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return abs(r_earth * c)


def write_log(data, ex_type, title=''):
    with open('{}_log.txt'.format(ex_type), 'a') as fp:
        fp.write(title+'\n')
        fp.write(str(data))
        fp.write('\n')


def check_folder(folder):
    if not os.path.exists(folder):
        os.mkdir(folder)
#-------------------------------------------------------------------------------------------------------


# parse args
if '-v' in sys.argv:
    vervose = True
    sys.argv.remove('-v')

if '-a' in sys.argv:
    all_images = True
    sys.argv.remove('-a')

if '--no-recursive' in sys.argv:
    recursive = False
    sys.argv.remove('--no-recursive')

if sys.argv[1] == 'help':
    print("\n\npass latitude longitude meters to script\nExample:\n\tpython geosearch -12.123 12.123 100\n")
    exit(0)
elif sys.argv[1] == 'delete_creds':
    if os.path.exists(os.path.join(cred_folder, 'token.pickle')):
        os.remove(os.path.join(cred_folder, 'token.pickle'))
    exit(0)
else:
    if len(sys.argv) > 1:
        try:
            coordinates = (float(sys.argv[1]), float(sys.argv[2]))
            distance = int(sys.argv[3])
        except ValueError:
            print("Error in coordinates/meters value. Must be a number")
            exit(1)
        except Exception as ex:
            print("Error in args.")
            write_log(ex, 'EXCEPTION')
            exit(1)
        else:
            print("\nSearching images close to: {}\n".format(coordinates))
#-------------------------------------------------------------------------------------------------------


check_folder(CRED_DIR)
check_folder(OUTPUT_DIR)
#-------------------------------------------------------------------------------------------------------


# Read/Create credentials to API
try:
    if os.path.exists(os.path.join(CRED_DIR, 'token.pickle')):
        with open(os.path.join(CRED_DIR, 'token.pickle'), 'rb') as token:
            creds = pickle.load(token)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(os.path.join(CRED_DIR, 'credentials.json'), SCOPES)
        creds = flow.run_local_server(port=0)
        with open(os.path.join(CRED_DIR, 'token.pickle'), 'wb') as token:
                pickle.dump(creds, token)

    files = build(SPACES, API_VERSION, credentials=creds).files()
except Exception as ex:
    print("Error while trying create google drive files handle")
    write_log(ex, 'EXCEPTION')
    exit(0)
#-------------------------------------------------------------------------------------------------------


# Get all folder in dir
folders_id = [DRIVE_DIR]
page_token = None
if recursive:
    query = "(mimeType='application/vnd.google-apps.folder')"  # and ('{}' in parents)".format(drive_folder)
    fields = "nextPageToken, files(id, parents)"

    try:
        folders_drive = files.list(pageSize=1000, spaces=SPACES, q=query, fields=fields, pageToken=page_token).execute().get('files', [])
    except Exception as ex:
        print('Error to connect API')
        write_log(ex, 'EXCEPTION')
        exit(0)
    else:
        folders_drive = list(filter(lambda folder: 'parents' in folder, folders_drive))

    flag = True
    while flag:
        flag = False
        index = 0
        for folder in folders_drive:
            if folder['parents'][0] in folders_id:
                folders_id.append(folders_drive.pop(index)['id'])
                flag = True
                break
            index += 1
#-------------------------------------------------------------------------------------------------------


# Performed image search
images_dict = {}
fields = "nextPageToken, files(id, name, mimeType, thumbnailLink, webViewLink, webContentLink, \
          imageMediaMetadata/location/latitude, imageMediaMetadata/location/longitude)"
count = 0
images_total = 0
def save_metadata(request_id, response, exception, q=''):
    
    global count, images_total, images_dict

    if exception is not None:
        write_log(ex, 'EXCEPTION', title=q)
        return
    while True:

        for image in response.get('files', []):
            images_total += 1
            if ('imageMediaMetadata' in image) and ('location' in image['imageMediaMetadata']):
                image['latitude'] = image['imageMediaMetadata']['location']['latitude']
                image['longitude'] = image['imageMediaMetadata']['location']['longitude']
                del image['imageMediaMetadata']
                if (calculate_distance(coordinates, (image['latitude'], image['longitude'])) < distance) or all_images:
                    count += 1
                    if vervose:
                        print_metadata(image)
                    images_dict.update({count: image})

        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
        else:
            response = files.list(pageSize=1000, spaces=SPACES, q=q, fields=fields, pageToken=page_token).execute()


page_token = None
http = Http(cache='.cache_geosearch')  # enable cache in drive
batch = BatchHttpRequest()

# add a 100 http request to batchrequest
total_querys = 100 if len(folders_id) >= 100 else len(folders_id)
folder_per_query = (len(folders_id) // 100) + 1

end = 0
for i in range(folder_per_query, total_querys+folder_per_query, folder_per_query):
    start = end
    end = i if i < len(folders_id) else len(folders_id)-1

    if start == end: break

    query = "(mimeType='image/jpeg') and (" + " or ".join(map(lambda idx: "('{}' in parents)".format(idx), folders_id[start:end])) + ")"
    batch.add(files.list(pageSize=1000, spaces=SPACES, q=query, fields=fields, pageToken=page_token),
               partial(save_metadata, q=query))

#-------------------------------------------------------------------------------------------------------
# OTHER queries implemented:

# """query for a unique request:"""
# query = "(mimeType='image/jpeg') and (" + " or ".join(map(lambda idx: "('{}' in parents)".format(idx), folders_id)) + ")"

# """One query per folder:"""
# for folder_id in folders_id:
#     query = "(mimeType='image/jpeg') and ('{}' in parents)".format(folder_id)
#     batch.add(files.list(pageSize=1000, spaces=SPACES, q=query, fields=fields, pageToken=page_token),
#               partial(save_metadata, q=query))


works = False
ex_ = None
for i in range(1,6):
    try:
        batch.execute(http=http)
        if vervose:
            print('Total images processed', images_total, 'in {} folders'.format(len(folders_id)))
    except Exception as ex:
        ex_ = ex
        print('Error to connect API. Trying again in {} seconds'.format(i))
        time.sleep(i)
    else:
        works = True
        break
if not works:
    print('Error to connect API. Tries reached')
    write_log(ex_, 'EXCEPTION')
    exit(0)

with open(os.path.join(OUTPUT_DIR, JSON_FILENAME), 'w') as fp:
    json.dump(images_dict, fp)


if not count:
    print("Not images found")
else:
    print("{} images found.\nSee: {}\n".format(count, os.path.join(OUTPUT_DIR, JSON_FILENAME)))
#-------------------------------------------------------------------------------------------------------
