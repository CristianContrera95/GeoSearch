from __future__ import print_function 

import pickle 
import os.path
import sys
import json
import time
from math import pi, sin, cos, acos
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

DRIVE_DIR = '0AMjJ9wCLSgjJUk9PVA'
CRED_DIR = 'creds'
OUTPUT_DIR = 'data'
JSON_FILENAME = 'images_data_{}.json'.format(dt.now().strftime("%d-%m-%y_%H-%M-%S"))
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
# -------------------------------------------------------------------------------------------------------


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
    new_lat = lat + (mts / r_earth) * (180 / pi)
    new_lon = lon + (mts / r_earth) * (180 / pi) / cos(lat * pi/180)
    return new_lat, new_lon


def calculate_distance(coordinates1, coordinates2):
    """
    Return distance beteenw cordinates in mts
    :param coordinates1: tuple (lat,log)
    :param coordinates2: tuple (lat,log)
    :return: int
    """
    r_earth = 6378 * 1000  # earth radius in mts

    lat1 = pi * coordinates1[0] / 180.0
    lon1 = pi * coordinates1[1] / 180.0
    lat2 = pi * coordinates2[0] / 180.0
    lon2 = pi * coordinates2[1] / 180.0

    d = acos(sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(lon1 - lon2)) * r_earth
    return d


def write_log(data, ex_type, title=''):
    with open('{}_log.txt'.format(ex_type), 'a') as fp_log:
        fp_log.write(title+'\n')
        fp_log.write(str(data))
        fp_log.write('\n')


def check_folder(folder_path):
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)
# -------------------------------------------------------------------------------------------------------


if len(sys.argv) == 1:
    print('No args')
    exit(0)

coordinates = None
given_date = None
given_hour = None
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

if len(sys.argv) > 1 and sys.argv[1] == 'help':
    print("\n\npass latitude longitude meters to script\nExample:\n\tpython geosearch -12.123 12.123 100\n")
    exit(0)
elif len(sys.argv) > 1 and sys.argv[1] == 'delete_creds':
    if os.path.exists(os.path.join(CRED_DIR, 'token.pickle')):
        os.remove(os.path.join(CRED_DIR, 'token.pickle'))
    exit(0)
else:
    if len(sys.argv) > 1:
        try:
            try:
                dt.strptime(sys.argv[1], '%Y-%m-%d')
                given_date = sys.argv[1]
                given_hour = '00:00:00'

                if len(sys.argv) > 2:
                    dt.strptime(sys.argv[2], '%H:%M:%S')
                    given_hour = sys.argv[2]
                print("\nSearching images after to: {} {}\n".format(given_date, given_hour))

            except Exception as ex:
                write_log(ex, 'EXCEPTION')
                coordinates = (float(sys.argv[1]), float(sys.argv[2]))
                distance = int(sys.argv[3])
                print("\nSearching images close to: {}\n".format(coordinates))

        except ValueError:
            print("Error in coordinates/meters or format date value. Must be a number or YYYY-mm-dd")
            exit(1)
        except Exception as ex:
            print("Error in args.")
            write_log(ex, 'EXCEPTION')
            exit(1)
# -------------------------------------------------------------------------------------------------------


check_folder(CRED_DIR)
check_folder(OUTPUT_DIR)
# -------------------------------------------------------------------------------------------------------


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
# -------------------------------------------------------------------------------------------------------


# Get all folder in dir
if coordinates is not None:
    folders_id = [DRIVE_DIR]
    page_token = None
    if recursive:
        query = "(mimeType='application/vnd.google-apps.folder')"  # and ('{}' in parents)".format(drive_folder)
        fields = "nextPageToken, files(id, parents)"

        try:
            folders_drive = files.list(pageSize=1000, spaces=SPACES, q=query, fields=fields, pageToken=page_token)\
                                 .execute()\
                                 .get('files', [])
        except Exception as ex:
            print('Error to connect API')
            write_log(ex, 'EXCEPTION')
            exit(0)
        else:
            folders_drive = list(filter(lambda f: 'parents' in f, folders_drive))

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
# -------------------------------------------------------------------------------------------------------


# Performed image search
images_dict = {}
fields = "nextPageToken, files(name, thumbnailLink, webContentLink, \
          imageMediaMetadata/location/latitude, imageMediaMetadata/location/longitude, modifiedTime)"
count = 0
images_total = 0


def save_metadata(request_id, response, exception, q=''):

    global count, images_total, images_dict

    if exception is not None:
        write_log(exception, 'EXCEPTION', title=q)
        return
    while True:

        for image in response.get('files', []):
            images_total += 1
            if ('imageMediaMetadata' in image) and ('location' in image['imageMediaMetadata']):
                image['latitude'] = image['imageMediaMetadata']['location']['latitude']
                image['longitude'] = image['imageMediaMetadata']['location']['longitude']
                del image['imageMediaMetadata']
                if (calculate_distance(coordinates, (image['latitude'], image['longitude'])) <= distance) or all_images:
                    count += 1
                    if vervose:
                        print_metadata(image)
                    images_dict.update({count: image})

        n_page_token = response.get('nextPageToken', None)
        if n_page_token is None:
            break
        else:
            response = files.list(pageSize=1000, spaces=SPACES, q=q, fields=fields, pageToken=n_page_token).execute()


page_token = None
http = Http(cache='.cache_geosearch')  # enable cache in drive
batch = BatchHttpRequest()

if coordinates is not None:
    # add a 100 http request to batchrequest
    total_querys = 100 if len(folders_id) >= 100 else len(folders_id)
    folder_per_query = (len(folders_id) // 100) + 1
    end = 0
    for i in range(folder_per_query, total_querys+folder_per_query, folder_per_query):
        start = end
        end = i if i < len(folders_id) else len(folders_id)-1

        if start == end: break

        query = "(mimeType='image/jpeg') and (" + " or ".join(map(lambda idx: "('{}' in parents)".format(idx),
                                                                  folders_id[start:end])) + ")"
        batch.add(files.list(pageSize=1000, spaces=SPACES, q=query, fields=fields, pageToken=page_token),
                  partial(save_metadata, q=query))


# -------------------------------------------------------------------------------------------------------
# OTHER queries implemented:

# """query for a unique request:"""
# query = "(mimeType='image/jpeg') and (" + \
#         " or ".join(map(lambda idx: "('{}' in parents)".format(idx), folders_id)) + ")"

# """One query per folder:"""
# for folder_id in folders_id:
#     query = "(modifiedTime>'{}T{}') and (mimeType='image/jpeg')".format(given_date, given_hour)
#     batch.add(files.list(pageSize=1000, spaces=SPACES, q=query, fields=fields, pageToken=page_token),
#               partial(save_metadata, q=query))


query = "(modifiedTime>'{}T{}') and (mimeType='image/jpeg')".format(given_date, given_hour)
works = False
for i in range(1, 6):
    try:
        if coordinates is not None:
            batch.execute(http=http)
        else:
            while True:
                response_ = files.list(pageSize=1000, spaces=SPACES, q=query, fields=fields, pageToken=page_token)\
                                .execute()
                for img in response_.get('files', []):
                    images_total += 1
                    images_dict.update({count: img})
                    count += 1

                    if vervose:
                        print_metadata(img)

                page_token = response_.get('nextPageToken', None)
                if page_token is None:
                    break

        if vervose:
            print('Total images processed', images_total)
    except Exception as exc:
        images_dict = {}
        count = 0
        images_total = 0
        print('Error to connect API. Trying again in {} seconds'.format(i))
        write_log(exc, 'EXCEPTION')
        time.sleep(i)
    else:
        works = True
        break


if not works:
    print('Error to connect API. Tries reached')
    exit(0)

with open(os.path.join(OUTPUT_DIR, JSON_FILENAME), 'w') as fp:
    json.dump(images_dict, fp, indent='\t', sort_keys=True)


if not count:
    print("Not images found")
else:
    print("{} images found.\nSee: {}\n".format(count, os.path.join(OUTPUT_DIR, JSON_FILENAME)))
# -------------------------------------------------------------------------------------------------------
