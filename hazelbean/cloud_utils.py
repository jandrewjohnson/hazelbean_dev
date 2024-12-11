from google.cloud import storage
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
import os
import subprocess
import hazelbean as hb
import taskgraph
import urllib
import time
import socket

# Set timeout for all socket connections
timeout_seconds = 5  # 5 seconds, for example
socket.setdefaulttimeout(timeout_seconds)


L = hb.get_logger('cloud_utils')

def is_internet_available(timeout=1):
    try: 
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except:
        return False
        

def gsutil_download_url(url, target_path, skip_if_target_exists=False):
    gsutil_path = url.replace('https://storage.cloud.google.com/', 'gs://')
    command = 'gsutil cp ' + gsutil_path + ' ' + target_path

    # old_cwd = os.getcwd()
    # os.chdir(os.path.split(call_list[0])[0])
    print('command', command)

    os.system(command)
    proc = subprocess.Popen(command)
    # proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # for line in iter(proc.stdout.readline, ''):
    #     cleaned_line = str(line).replace('b\'\'', '').replace('b\'', '').replace('\\r\\n\'', '').replace('b\"', '').replace('\\r\\n\"', '')
    #     cleaned_line.rstrip("\r\n")
    #     if len(cleaned_line) > 0:
    #         L.info('GSUTIL' + ': ' + cleaned_line)
    #     poll = proc.poll()
    #     if poll is not None:
    #         break
    #
    #
    # proc.stdout.close()

    if proc.wait() != 0:
        raise RuntimeError("%r failed, exit status: %d" % (str(command), proc.returncode))

    proc.terminate()
    proc = None


def download_url(url, target_path, skip_if_target_exists=False):
    """Download `url` to `target_path`. DO NOT USE BROKEN.

    Args:
        url (str): url path to a file.
        target_path (str): desired output target path.
        skip_if_target_exists (bool): if True will not download a file if the
            path already exists on disk.

    Returns:
        None.

    """
    if skip_if_target_exists and os.path.exists(target_path):
        return
    hb.create_directories(target_path)
    with open(target_path, 'wb') as target_file:
        last_download_size = 0
        start_time = time.time()
        with urllib.request.urlopen(url) as url_stream:
            print('url_stream', url_stream)
            meta = url_stream.info()
            print(meta)
            # file_size = int(meta["Content-Length"])
            #
            file_size = 10000000000
            hb.log("Downloading: %s Bytes: %s" % (target_path, file_size))

            downloaded_so_far = 0
            block_size = 2**20
            last_log_time = time.time()
            while True:
                data_buffer = url_stream.read(block_size)
                if not data_buffer:
                    # WARNING# I started using this but switched to GSUTIL because the second pass through this While loop always returned a None and broke out.
                    break
                downloaded_so_far += len(data_buffer)
                target_file.write(data_buffer)
                time_since_last_log = time.time() - last_log_time
                if time_since_last_log > 5.0:
                    download_rate = (
                        (downloaded_so_far - last_download_size)/2**20) / (
                            float(time_since_last_log))
                    last_download_size = downloaded_so_far
                    status = r"%10dMB  [%3.2f%% @ %5.2fMB/s]" % (
                        downloaded_so_far/2**20, downloaded_so_far * 100. /
                        file_size, download_rate)
                    hb.log(status)
                    last_log_time = time.time()
        total_time = time.time() - start_time
        final_download_rate = downloaded_so_far/2**20 / float(total_time)
        status = r"%10dMB  [%3.2f%% @ %5.2fMB/s]" % (
            downloaded_so_far/2**20, downloaded_so_far * 100. /
            file_size, final_download_rate)
        hb.log(status)
        target_file.flush()
        os.fsync(target_file.fileno())



def download_urls_list(input_list, target_dir, use_gsutil=False):

    task_graph = taskgraph.TaskGraph(target_dir, -1)

    for input_url in input_list:
        target_path = os.path.join(target_dir, os.path.basename(input_url))
        if use_gsutil:
            gsutil_download_url(input_url, target_path)
        else:
            download_task = task_graph.add_task(
                func=download_url,
                args=(input_url, target_path),
                target_path_list=[target_path],
            task_name='download baccini')

    task_graph.close()
    task_graph.join()



def download_google_cloud_blob(bucket_name, source_blob_name, credentials_path, destination_file_name, chunk_size=262144*5, verbose=False):
    """There is a duplicate version of this that i want to get rid of in the seals repo. Downloads a blob from the bucket."""
    require_database = True
    if hb.path_exists(credentials_path) and require_database:
        
        
        client = storage.Client.from_service_account_json(credentials_path)
    else:
        if credentials_path is not None:
            hb.log('Unable to find referenced database license. Your code currently is stating it should be found at ' + str(credentials_path) + ' with abspath of ' + str(hb.path_abs(credentials_path)) + ' relative to where the run script was launched. Defaulting to publicly available data. If you would like to generate your own database, disable this check (set require_database to False). Otherwise, feel free to reach out to the developer of SEALS to acquire the license key. It is only limited because the data are huge and expensive to host (600+ Gigabytes).')
        else:
            if verbose:
                hb.log('No credentials path provided. Defaulting to publicly available data.')
            bucket_name = 'gtap_invest_seals_2023_04_21'
            
        # If credentials path does not exist or is none, just get a client without credentials. This will only work if the bucket is public.
        client = storage.Client.create_anonymous_client()
        

    try:
        bucket = client.bucket(bucket_name)
    except Exception as e:
        if verbose:
            hb.log('Unable to get bucket ' + str(bucket_name) + ' with exception ' + str(e))

    try:
        # source_blob_name = 'base_data/' + source_blob_name
        blob = bucket.get_blob(source_blob_name, timeout=(1,2)) # LEARNING POINT, difference between bucket.blob and bucket.get_blob is the latter sets extra attributes like blob.size.
    except Exception as e:
        if verbose:
            hb.log('Unable to get blob ' + str(source_blob_name) + ' with exception ' + str(e))

    if blob is None:
        if verbose:
            hb.log('Unable to get blob ' + str(source_blob_name) + ' from ' + source_blob_name + ' in ' + bucket_name + '.')


    L.info('Starting to download to ' + destination_file_name + ' from ' + source_blob_name + ' in ' + bucket_name + '. The size of the object is ' + str(blob.size))

    current_dir = os.path.split(destination_file_name)[0]
    hb.create_directories(current_dir, ignore_dots_in_dirname=True)


    try:
        blob.download_to_filename(destination_file_name)
    except Exception as e:
        if verbose:
            hb.log('Blob download_to_file failed for ' + str(destination_file_name) + ' with exception ' + str(e))



    # LEARNING POINT, this was 4x slower.
    # parts = int(blob.size / chunk_size)
    # file_obj = open(destination_file_name, "wb")
    # for part in range(0,parts+1):
    #     blob.download_to_file(file_obj, start=part*chunk_size, end=(part+1)*chunk_size-1)
    #     print_progress_bar(part, parts)
    # print('Download completed')


# def getBucketFileProgress(bucket_name, source_blob_name, destination_file_name, chunk_size=262144*5, client=None):
#     """
#     Downloads a file from a bucket with a progres bar.
#     @params:
#         bucket_name           - Required : bucket name (Str)
#         source_blob_name      - Required : blob name (Str)
#         destination_file_name - Required : local filename (Str)
#         chunk_size            - Optional : Must be a multiple of 256 KB. Default 5*256KB (Int)
#         client                - Optional : storage client (Obj)
#     """
#     if not client:
#         client = storage_client.Client()
#
#     bucket = client.get_bucket(bucket_name)
#     blob = bucket.get_blob(source_blob_name)
#     parts = int(blob.size / chunk_size)
#     file_obj = open(destination_file_name, "wb")
#     for part in range(0,parts+1):
#         blob.download_to_file(file_obj, start=part*chunk_size, end=(part+1)*chunk_size-1)
#         printProgressBar(part, parts)
#     print('Download completed')

def list_files_in_google_drive_folder(input_folder_id, credentials_path):
    # NYI! This approach uses google drive, but htat means I need to verify gtapinvest as an app with google. not worth it. switching back to gsutil for now.
    # If modifying these SCOPES, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    creds = None
    # The file token.pickle stores the user's access and refresh tokens.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    # Call the Drive v3 API
    query = f"'{input_folder_id}' in parents"
    results = service.files().list(q=query, pageSize=10, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))
            
            
def promote_ref_path_to_base_data(input_path, pivot_path, base_data_dir):
    # Moves an input path to the base_data_dir based on the pivot_path
    # Doesn't currently upload to cloud but that could be done.
    # NOTE A ref_path is never a full path as it excludes the prefix base_Data_dir, cur_dir, or wahtever dir it was found in. This function you
    # explicitly define the pivot path
    
    # Get ref_path first
    ref_path = hb.get_path_to_right_of_dir(input_path, pivot_path)
    
    # Check if the file exists
    if not hb.path_exists(input_path):
        raise NameError('The file ' + str(input_path) + ' does not exist.')
    
    # Check if the base_data_dir exists
    if not hb.path_exists(base_data_dir):
        raise NameError('The directory ' + str(base_data_dir) + ' does not exist.')
    
    # Check if the file is in the base_data_dir
    joined_path = os.path.join(base_data_dir, ref_path)
    if hb.path_exists(joined_path):
        raise NameError('The file ' + str(joined_path) + ' is already in the base_data_dir.')
    
    # Move the file to the base_data_dir
    os.rename(input_path, joined_path)
    