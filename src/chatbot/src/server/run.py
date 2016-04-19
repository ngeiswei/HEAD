#!/usr/bin/env python2.7

import os
import logging
from auth import requires_auth
from zipfile import ZipFile

LOG_CONFIG_FILE = os.environ.get('ROS_PYTHON_LOG_CONFIG_FILE', None)
if LOG_CONFIG_FILE is not None:
    import logging.config
    import rosgraph
    if 'ROS_LOG_DIR' not in os.environ:
        os.environ['ROS_LOG_DIR'] = os.path.expanduser('~/.hr')
    if 'ROS_LOG_FILENAME' not in os.environ:
        os.environ['ROS_LOG_FILENAME'] = os.path.join(
            os.environ['ROS_LOG_DIR'], 'chatbot_server.log')
    logging.config.fileConfig(LOG_CONFIG_FILE)
else:
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)

import sys
CWD = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(CWD, '..'))
sys.path.insert(0, os.path.join(CWD, '../scripts'))
from flask import Flask, request, Response, send_from_directory
import json
from chatbot import (ask, list_character, update_character, get_character,
                    load_sheet_keys, commit_character)

json_encode = json.JSONEncoder().encode
app = Flask(__name__)
VERSION = 'v1'
ROOT='/{}'.format(VERSION)

logger = logging.getLogger('hr.chatbot.server')
app.config['UPLOAD_FOLDER'] = os.path.expanduser('~/.hr/aiml')

@app.route(ROOT+'/chat', methods=['GET'])
@requires_auth
def chat():
    data = request.args
    id = data.get('botid')
    question = data.get('question')
    session = data.get('session')
    response, ret = ask(id, question, session)
    return Response(json_encode({'ret': ret, 'response': response}),
        mimetype="application/json")

@app.route(ROOT+'/chatbots', methods=['GET'])
@requires_auth
def list_chatbot():
    return Response(json_encode({'ret': 0, 'response': list_character()}),
        mimetype="application/json")

@app.route(ROOT+'/update', methods=['GET'])
@requires_auth
def update():
    data = request.args
    id = data.get('botid')
    csv_version = data.get('csv_version', '1')
    ret, response = update_character(id, csv_version)
    return Response(json_encode({
            'ret': int(ret),
            'response': response
        }),
        mimetype="application/json")

@app.route(ROOT+'/set_keys', methods=['GET'])
@requires_auth
def set_keys():
    data = request.args
    id = data.get('botid')
    sheet_keys = data.get('sheet_keys')
    ret, response = load_sheet_keys(id, sheet_keys)
    return Response(json_encode({
            'ret': int(ret),
            'response': response
        }),
        mimetype="application/json")

@app.route(ROOT+'/commit', methods=['GET'])
@requires_auth
def commit():
    data = request.args
    id = data.get('botid')
    ret, response = commit_character(id)
    return Response(json_encode({
            'ret': ret,
            'response': response
        }),
        mimetype="application/json")

@app.route(ROOT+'/send_csvdata', methods=['POST'])
def send_csvdata():
    from auth import check_auth, authenticate
    auth = request.form.get('Auth')
    if not auth or not check_auth(auth):
        return authenticate()

    try:
        id = request.form.get('botid')
        ssid = request.form.get('ssid')
        character = get_character(id, True) # make sure the character exists
        zipfile = request.files.get('csvzipfile')
        saved_zipfile = os.path.join(character.incoming_dir, zipfile.filename)
        zipfile.save(saved_zipfile)
        with ZipFile(saved_zipfile) as f:
            f.extractall(character.incoming_dir)
        character.set_csv_dir(os.path.join(character.incoming_dir, ssid))
        logger.info("Get zip file {}".format(zipfile.filename))
        return Response(json_encode({
                'ret': True,
                'response': "Get zip file {}".format(zipfile.filename)
            }),
            mimetype="application/json")

    except Exception as ex:
        return Response(json_encode({
                'ret': False,
                'response': str(ex)
            }),
            mimetype="application/json")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8001
    app.run(host='0.0.0.0', debug=False, use_reloader=False, port=port)