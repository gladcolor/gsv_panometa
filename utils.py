import requests
import json
import base64
import struct
import PIL
import os

import pandas as pd
import numpy as np
import zlib

def refactorJson(jdata):
    newJson = {}

    if len(jdata) < 1:
        return ""

    # restore the first level keys
    newJson['Data'] = {}
    newJson['Projection'] = {}
    newJson['Location'] = {}
    newJson['Links'] = {}
    newJson['model'] = {}

    # Data
    newJson['Data']['image_width'] = jdata[1][0][2][2][1]
    newJson['Data']['image_height'] = jdata[1][0][2][2][0]
    newJson['Data']['tile_width'] = jdata[1][0][2][3][1][0]
    newJson['Data']['tile_height'] = jdata[1][0][2][3][1][1]
    newJson['Data']['image_date'] = jdata[1][0][6][7][0]
    newJson['Data']['imagery_type'] =  jdata[1][0][0][0]
    newJson['Data']['copyright'] =  jdata[1][0][4][0][0][0][0]

    # Projection
    newJson['Projection']['projection_type'] = 'spherical'
    newJson['Projection']['pano_yaw_deg'] = jdata[1][0][5][0][1][2][0]
    newJson['Projection']['tilt_yaw_deg'] =  jdata[1][0][5][0][1][2][1]
    newJson['Projection']['tilt_pitch_deg'] =  jdata[1][0][5][0][1][2][2]

    # Location
    newJson['Location']['panoId'] = jdata[1][0][1][1]
    newJson['Location']['zoomLevels'] = ''
    newJson['Location']['lat'] = jdata[1][0][5][0][1][0][2]
    newJson['Location']['lng'] = jdata[1][0][5][0][1][0][3]
    newJson['Location']['original_lat'] = ''
    newJson['Location']['original_lng'] = ''
    newJson['Location']['elevation_wgs84_m'] = ""
    newJson['Location']['description'] = jdata[1][0][3][2][0][0]
    newJson['Location']['streetRange'] = ''
    newJson['Location']['region'] = ''
    newJson['Location']['country'] = ''
    newJson['Location']['elevation_egm96_m'] = jdata[1][0][5][0][1][1][0]

    # Links
    # newJson['Links']['panoId'] =
    # newJson['Links']['zoomLevels'] =

    # model
    newJson['model']['depth_map'] = jdata[1][0][5][0][5][1][2]

    return newJson