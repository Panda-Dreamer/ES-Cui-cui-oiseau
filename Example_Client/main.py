from asyncio.windows_events import NULL
import os
import json
import time
import requests
import argparse
import urllib.parse

from multiprocessing import freeze_support


def sendRequest(host, port, fpath, mdata):

    url = 'http://{}:{}/analyze'.format(host, port)

    print('Requesting analysis for {}'.format(fpath))

    # Make payload
    multipart_form_data = {
        # Audio file to analyze in bytes
        'audio': (fpath.split(os.sep)[-1], open(fpath, 'rb')),
        'meta': (None, mdata)
    }

    # Send request
    start_time = time.time()
    response = requests.post(url, files=multipart_form_data)

    body = json.loads(response.text)
    max = 0
    result = NULL

    for obj in body["results"]:
        if(obj[1] > max):
            max = obj[1]
            result = obj[0]

    end_time = time.time()

    print('Response: {}, Confidence: {}%, Time: {:.4f}s'.format(
        result, str(round(max, 3) * 100), max, end_time - start_time), flush=True)

    url = 'http://{}:{}/get-bird?specie={}'.format(host, port, urllib.parse.quote(
        str(body["results"][0][0]).split("_")[1].encode('utf8')))
    start_time = time.time()
    response = requests.get(url)
    body = json.loads(response.text)

    end_time = time.time()
    data = json.loads(response.text)
    print('Response:{}, Time: {:.4f}s'.format(
        data, end_time - start_time), flush=True)
    return data


if __name__ == '__main__':

    # Freeze support for excecutable
    freeze_support()

    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Client that queries an analyzer API endpoint server.')
    parser.add_argument('--host', default='129.151.70.77',
                        help='Host name or IP address of API endpoint server.')
    parser.add_argument('--port', type=int, default=5000,
                        help='Port of API endpoint server.')
    parser.add_argument('--i', default='soundscape.wav',
                        help='Path to file that should be analyzed.')
    parser.add_argument(
        '--o', default='', help='Path to result file. Leave blank to store with audio file.')
    parser.add_argument('--lat', type=float, default=-1,
                        help='Recording location latitude. Set -1 to ignore.')
    parser.add_argument('--lon', type=float, default=-1,
                        help='Recording location longitude. Set -1 to ignore.')
    parser.add_argument('--week', type=int, default=-1,
                        help='Week of the year when the recording was made. Values in [1, 48] (4 weeks per month). Set -1 for year-round species list.')
    parser.add_argument('--overlap', type=float, default=0.0,
                        help='Overlap of prediction segments. Values in [0.0, 2.9]. Defaults to 0.0.')
    parser.add_argument('--sensitivity', type=float, default=1.0,
                        help='Detection sensitivity; Higher values result in higher sensitivity. Values in [0.5, 1.5]. Defaults to 1.0.')
    parser.add_argument('--pmode', default='avg',
                        help='Score pooling mode. Values in [\'avg\', \'max\']. Defaults to \'avg\'.')
    parser.add_argument('--num_results', type=int, default=5,
                        help='Number of results per request. Defaults to 5.')
    parser.add_argument('--sf_thresh', type=float, default=0.03,
                        help='Minimum species occurrence frequency threshold for location filter. Values in [0.01, 0.99]. Defaults to 0.03.')
    parser.add_argument('--save', type=bool, default=False,
                        help='Define if files should be stored on server. Values in [True, False]. Defaults to False.')

    args = parser.parse_args()
    mdata = {'lat': args.lat,
             'lon': args.lon,
             'week': args.week,
             'overlap': args.overlap,
             'sensitivity': args.sensitivity,
             'sf_thresh': args.sf_thresh,
             'pmode': args.pmode,
             'num_results': args.num_results,
             'save': args.save}

    # Send request
    data = sendRequest(args.host, args.port, args.i, json.dumps(mdata))
