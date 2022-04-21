import os
import json
from numpy import imag
from requests import request
from bottle import get, post, route
import bottle
import argparse
from datetime import datetime, date
import traceback
from bs4 import BeautifulSoup
from multiprocessing import freeze_support
import io

import config as cfg
import analyze

EBirdAPIKEY = "s08bvu01hv7h"

def clearErrorLog():

    if os.path.isfile(cfg.ERROR_LOG_FILE):
        os.remove(cfg.ERROR_LOG_FILE)


def writeErrorLog(msg):

    with open(cfg.ERROR_LOG_FILE, 'a') as elog:
        elog.write(msg + '\n')


def resultPooling(lines, num_results=5, pmode='avg'):

    # Parse results
    results = {}
    for line in lines:
        d = line.split('\t')
        species = d[2].replace(', ', '_')
        score = float(d[-1])
        if not species in results:
            results[species] = []
        results[species].append(score)

    # Compute score for each species
    for species in results:

        if pmode == 'max':
            results[species] = max(results[species])
        else:
            results[species] = sum(results[species]) / len(results[species])

    # Sort results
    results = sorted(results.items(), key=lambda x: x[1], reverse=True)

    return results[:num_results]


@route('/', method='GET')
def handleRequest():
    return """
  <html>
  <head>
    <title>Test CUI-CUI</title>
  </head>
  <body>
    <h1>Upload File v1.3</h1>
    <form action="/analyze" method="post" enctype="multipart/form-data">
      Category:      <input type="text" name="meta"  value='{"lat": -1, "lon": -1, "week": -1, "overlap": 0.0, "sensitivity": 1.0, "sf_thresh": 0.03, "pmode": "avg", "num_results": 5, "save": false }'/>
      Select a file: <input type="file" name="audio" accept=".m4a, .mp3, .wav" required/>
      Display: <input type="text" name="display" value='name'/>
      <input type="submit" value="Start upload" />
    </form>
   
  </body>
</html>
  """


@route('/get-bird', method='GET')
def handleRequest2():
    specie = bottle.request.query["specie"]
    if specie is None:
        return "Faut indiquer une espèce dum dum: url?specie=dumdum et en URL encoded dumdum"
#https://api.ebird.org/v2/ref/taxon/find?locale=fr_FR&cat=species&key=jfekjedvescr&q=Troglodyte%20de%20Sharpe
    link = "https://api.ebird.org/v2/ref/taxon/find?locale=fr_FR&cat=species&key=jfekjedvescr&q=" + specie
    r = request(method='GET', url=link)
    if r.status_code != 200:
        return "Erreur lors de la requête à l'API eBird"

    data = json.loads(r.text)
    if len(data) == 0:
        return "Aucun résultat pour cette espèce"

    code, name = data[0]["code"], data[0]["name"]

    link = "https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=json&locale=fr_FR&species="+code

    r = request(method='GET', url=link)
    if r.status_code != 200:
        return "Erreur lors de la 2eme requête à l'API eBird"

    data2 = json.loads(r.text)
    if len(data) == 0:
        return "Aucun résultat pour ce code espèce"

    rdata = {
        "sciName": data2[0]["sciName"],
        "comName": data2[0]["comName"],
        "family": data2[0]["familySciName"],
    }

    r2 = request(method='GET', url="https://ebird.org/species/"+code)
    if r2.status_code != 200:
        return "Erreur lors de la 3eme requête à l'API eBird"

    soup = BeautifulSoup(r2.text, 'html.parser')

    imageDIV = str(soup.find_all("div", {"class": "MediaThumbnail Media--playButton"})  [0]).split("src")[1].split("\"")[1]
    rdata["image"] = imageDIV
  
    return json.dumps(rdata)

    # API EBIRD s08bvu01hv7h
    # https://en.wikipedia.org/w/api.php?action=query&titles=Eagle&prop=extracts&format=json
    # https://api.ebird.org/v2/ref/taxon/find?locale=fr_FR&cat=species&key=s08bvu01hv7h&q=%20Troglodyte%20de%20Sharpe
    # https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=json&locale=fr_FR&species=


@bottle.route('/analyze', method='POST')
def handleAnalyzeRequest():

    # Print divider
    print('{}  {}  {}'.format('#' * 20, datetime.now(), '#' * 20))
    print('---------------------')
    upload = bottle.request.files.get('audio')
    mdata = json.loads(bottle.request.forms.get('meta'))

    # Get filename
    name, ext = os.path.splitext(upload.filename.lower())

    # Save file
    try:
        if ext.lower() in ['.wav', '.mp3', '.flac', '.ogg', '.m4a']:
            if 'save' in mdata and mdata['save']:
                save_path = os.path.join(
                    cfg.FILE_STORAGE_PATH, str(date.today()))
                if not os.path.exists(save_path):
                    os.makedirs(save_path)
                file_path = os.path.join(save_path, name + ext)
            else:
                save_path = ''
                file_path = 'tmp' + ext.lower()
            upload.save(file_path, overwrite=True)

        else:
            data = {'msg': 'Filetype not supported.'}
            return json.dumps(data)

    except:

        # Print traceback
        print(traceback.format_exc(), flush=True)

        # Write error log
        msg = 'Error: Cannot save file {}.\n{}'.format(
            file_path, traceback.format_exc())
        print(msg, flush=True)
        writeErrorLog(msg)

        # Return error
        data = {'msg': 'Error while saving file.'}
        return json.dumps(data)

    # Analyze file
    try:

        # Set config based on mdata
        if 'lat' in mdata and 'lon' in mdata:
            cfg.LATITUDE = float(mdata['lat'])
            cfg.LONGITUDE = float(mdata['lon'])
        else:
            cfg.LATITUDE = -1
            cfg.LONGITUDE = -1
        if 'week' in mdata:
            cfg.WEEK = int(mdata['week'])
        else:
            cfg.WEEK = -1
        if 'overlap' in mdata:
            cfg.OVERLAP = max(0.0, min(2.9, float(mdata['overlap'])))
        else:
            cfg.OVERLAP = 0.0
        if 'senitivity' in mdata:
            cfg.SENITIVITY = max(
                0.5, min(1.0 - (float(mdata['senitivity']) - 1.0), 1.5))
        else:
            cfg.SENITIVITY = 1.0
        if 'sf_thresh' in mdata:
            cfg.LOCATION_FILTER_THRESHOLD = max(
                0.01, min(0.99, float(mdata['sf_thresh'])))
        else:
            cfg.LOCATION_FILTER_THRESHOLD = 0.03

        # Set species list
        if not cfg.LATITUDE == -1 and not cfg.LONGITUDE == -1:
            analyze.predictSpeciesList()

        # Analyze file
        success = analyze.analyzeFile((file_path, cfg.getConfig()))

        # Parse results
        if success:

            # Open result file
            lines = []
            with open(cfg.OUTPUT_PATH, 'r') as f:
                for line in f.readlines():
                    lines.append(line.strip())

            # Pool results
            if 'pmode' in mdata and mdata['pmode'] in ['avg', 'max']:
                pmode = mdata['pmode']
            else:
                pmode = 'avg'
            if 'num_results' in mdata:
                num_results = min(99, max(1, int(mdata['num_results'])))
            else:
                num_results = 5
            results = resultPooling(lines, num_results, pmode)

            # Prepare response
            data = {'msg': 'success', 'results': results, 'meta': mdata}

            # Save response as metadata file
            with open(file_path.rsplit('.', 1)[0] + '.json', 'w') as f:
                json.dump(data, f, indent=2)

            # Return response
            del data['meta']
            display = bottle.request.forms.get('display')
            if display == 'name':
              return 'Résultat: {}, \n Confiance: {}%'.format(data["results"][0][0],str(round(data["results"][0][1], 3) * 100))
            else:
              return json.dumps(data)

        else:
            data = {'msg': 'Error during analysis.'}
            return json.dumps(data)

    except Exception as e:

        # Print traceback
        print(traceback.format_exc(), flush=True)

        # Write error log
        msg = 'Error: Cannot analyze file {}.\n{}'.format(
            file_path, traceback.format_exc())
        print(msg, flush=True)
        writeErrorLog(msg)

        data = {'msg': 'Error during analysis: {}'.format(str(e))}
        return json.dumps(data)

@bottle.route('/<:re:.*>', method='OPTIONS')
def enable_cors_generic_route():
    """
    This route takes priority over all others. So any request with an OPTIONS
    method will be handled by this function.

    See: https://github.com/bottlepy/bottle/issues/402

    NOTE: This means we won't 404 any invalid path that is an OPTIONS request.
    """
    add_cors_headers()

@bottle.hook('after_request')
def enable_cors_after_request_hook():
    """
    This executes after every route. We use it to attach CORS headers when
    applicable.
    """
    add_cors_headers()

def add_cors_headers():
      bottle.response.headers['Access-Control-Allow-Origin'] = '*'
      bottle.response.headers['Access-Control-Allow-Methods'] = \
            'GET, POST, PUT, OPTIONS'
      bottle.response.headers['Access-Control-Allow-Headers'] = \
            'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

      
if __name__ == '__main__':

    # Freeze support for excecutable
    freeze_support()

    # Clear error log
    clearErrorLog()

    # Parse arguments
    parser = argparse.ArgumentParser(
        description='API endpoint server to analyze files remotely.')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host name or IP address of API endpoint server. Defaults to \'0.0.0.0\'')
    parser.add_argument('--port', type=int, default=5000,
                        help='Port of API endpoint server. Defaults to 8080.')
    parser.add_argument('--spath', default='uploads/',
                        help='Path to folder where uploaded files should be stored. Defaults to \'/uploads\'.')
    parser.add_argument('--threads', type=int, default=4,
                        help='Number of CPU threads for analysis. Defaults to 4.')
    parser.add_argument('--locale', default='fr',
                        help='Locale for translated species common names. Values in [\'af\', \'de\', \'it\', ...] Defaults to \'en\'.')

    args = parser.parse_args()

   # Load eBird codes, labels
    cfg.CODES = analyze.loadCodes()
    cfg.LABELS = analyze.loadLabels(cfg.LABELS_FILE)

    # Load translated labels
    lfile = os.path.join(cfg.TRANSLATED_LABELS_PATH, os.path.basename(
        cfg.LABELS_FILE).replace('.txt', '_{}.txt'.format(args.locale)))
    if not args.locale in ['en'] and os.path.isfile(lfile):
        cfg.TRANSLATED_LABELS = analyze.loadLabels(lfile)
    else:
        cfg.TRANSLATED_LABELS = cfg.LABELS

    # Set storage file path
    cfg.FILE_STORAGE_PATH = args.spath

    # Set min_conf to 0.0, because we want all results
    cfg.MIN_CONFIDENCE = 0.0

    # Set path for temporary result file
    cfg.OUTPUT_PATH = 'tmp.txt'

    # Set result type
    cfg.RESULT_TYPE = 'audacity'

    # Set number of TFLite threads
    cfg.TFLITE_THREADS = max(1, int(args.threads))

    # Run server
    print('UP AND RUNNING! LISTENING ON {}:{}'.format(
        args.host, args.port), flush=True)
    bottle.run(host=args.host, port=args.port, quiet=True)