import requests
import json
import base64
import numpy as np
import struct
import PIL
import os
import copy
import zlib

from libtiff import TIFF


try:
    import Image
except ImportError:
    from PIL import Image

def getPanoId(lon, lat):
    try:
        jdata = getPanoJson_from_lonlat(lon, lat)
        panoId = jdata[1][1][1]
    except:
        panoId = ""   # if there is no panorama
    return panoId

def getPanoJson_from_lonlat(lon, lat):
    resp = _getGeoPhotoJS_frm_lonlat(lon, lat)
    line = resp.text.replace("/**/_xdc_._v2mub5 && _xdc_._v2mub5( ", "")[:-2]
    try:
        jdata = json.loads(line)
    except:
        jdata = ""   # if there is no panorama
    return jdata

def getPanoJson_from_panoId(panoId):
    resp = _getPanometaJS_from_panoId(panoId)
    line = resp.text.replace(")]}'\n", "")
    try:
        jdata = json.loads(line)
        jdata = gsv_dm.compressJson(jdata)
    except:
        jdata = ""   # if there is no panorama
    return jdata

def getDepthmap_from_panoId(panoId, saved_path=''):

    jdata = getPanoJson_from_panoId(panoId)

    # print(gsv_dm.parse(jdata[1][0][5][0][5][1][2]))
    print(gsv_dm.getDepthmapfrmJson(jdata, saved_path))


def _getPanometaJS_from_panoId(panoId):
    url = "https://www.google.com/maps/photometa/v1?authuser=0&hl=zh-CN&pb=!1m4!1smaps_sv.tactile!11m2!2m1!1b1!2m2!1szh-CN!2sus!3m3!1m2!1e2!2s{}!4m57!1e1!1e2!1e3!1e4!1e5!1e6!1e8!1e12!2m1!1e1!4m1!1i48!5m1!1e1!5m1!1e2!6m1!1e1!6m1!1e2!9m36!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e3!2b1!3e2!1m3!1e3!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e1!2b0!3e3!1m3!1e4!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e3"
    url = url.format(panoId)
    return requests.get(url, proxies=None)

def _getGeoPhotoJS_frm_lonlat(lon, lat):
    url = "https://maps.googleapis.com/maps/api/js/GeoPhotoService.SingleImageSearch?pb=!1m5!1sapiv3!5sUS!11m2!1m1!1b0!2m4!1m2!3d{0:}!4d{1:}!2d50!3m10!2m2!1sen!2sGB!9m1!1e2!11m4!1m3!1e2!2b1!3e2!4m10!1e1!1e2!1e3!1e4!1e8!1e6!5m1!1e2!6m1!1e2&callback=_xdc_._v2mub5"
    url = url.format(lat, lon)
    return requests.get(url, proxies=None)


class gsv_depthmap(object):
    def parse(self, b64_string):
        # fix the 'inccorrect padding' error. The length of the string needs to be divisible by 4.
        b64_string += "=" * ((4 - len(b64_string) % 4) % 4)
        # convert the URL safe format to regular format.
        data = b64_string.replace("-", "+").replace("_", "/")

        data = base64.b64decode(data)  # decode the string
        # data = zlib.decompress(data)  # decompress the data
        # data = b64_string.encode("utf-8")
        return np.array([d for d in data])

    def parseHeader(self, depthMap):
        return {
            "headerSize": depthMap[0],
            "numberOfPlanes": self.getUInt16(depthMap, 1),
            "width": self.getUInt16(depthMap, 3),
            "height": self.getUInt16(depthMap, 5),
            "offset": self.getUInt16(depthMap, 7),
        }

    def get_bin(self, a):
        ba = bin(a)[2:]
        return "0" * (8 - len(ba)) + ba

    def getUInt16(self, arr, ind):
        a = arr[ind]
        b = arr[ind + 1]
        return int(self.get_bin(b) + self.get_bin(a), 2)

    def getFloat32(self, arr, ind):
        return self.bin_to_float("".join(self.get_bin(i) for i in arr[ind: ind + 4][::-1]))

    def bin_to_float(self, binary):
        return struct.unpack("!f", struct.pack("!I", int(binary, 2)))[0]

    def parsePlanes(self, header, depthMap):
        indices = []
        planes = []
        n = [0, 0, 0]

        for i in range(header["width"] * header["height"]):
            indices.append(depthMap[header["offset"] + i])

        for i in range(header["numberOfPlanes"]):
            byteOffset = header["offset"] + header["width"] * header["height"] + i * 4 * 4
            n = [0, 0, 0]
            n[0] = self.getFloat32(depthMap, byteOffset)
            n[1] = self.getFloat32(depthMap, byteOffset + 4)
            n[2] = self.getFloat32(depthMap, byteOffset + 8)
            d = self.getFloat32(depthMap, byteOffset + 12)
            planes.append({"n": n, "d": d})

        return {"planes": planes, "indices": indices}

    def computeDepthMap(self, header, indices, planes):

        v = [0, 0, 0]
        w = header["width"]
        h = header["height"]

        depthMap = np.empty(w * h)

        sin_theta = np.empty(h)
        cos_theta = np.empty(h)
        sin_phi = np.empty(w)
        cos_phi = np.empty(w)

        for y in range(h):
            theta = (h - y) / h * np.pi  # original
            # theta = y / h * np.pi  # huan
            sin_theta[y] = np.sin(theta)
            cos_theta[y] = np.cos(theta)

        for x in range(w):
            phi = x / w * 2 * np.pi  # + np.pi / 2
            sin_phi[x] = np.sin(phi)
            cos_phi[x] = np.cos(phi)

        for y in range(h):
            for x in range(w):
                planeIdx = indices[y * w + x]

                # Origninal
                # v[0] = sin_theta[y] * cos_phi[x]
                # v[1] = sin_theta[y] * sin_phi[x]

                # Huan
                v[0] = sin_theta[y] * sin_phi[x]
                v[1] = sin_theta[y] * cos_phi[x]
                v[2] = cos_theta[y]

                if planeIdx > 0:
                    plane = planes[planeIdx]
                    t = np.abs(plane["d"] / (v[0] * plane["n"][0] + v[1] * plane["n"][1] + v[2] * plane["n"][2]))
                # original, not flip
                #     depthMap[y * w + (w - x - 1)] = t
                # else:
                #     depthMap[y * w + (w - x - 1)] = 0

                    # flip:  -Huan
                    if t < 100:
                        depthMap[y * w + x] = t
                    else:
                        depthMap[y * w + x] = 0
                else:
                    depthMap[y * w + x] = 0

        return {"width": w, "height": h, "depthMap": depthMap}

    def getDepthmapfrmJson(self, jdata, saved_path=''):
        try:
            depthMapData = self.parse(jdata[1][0][5][0][5][1][2])
            # parse first bytes to describe data
            header = self.parseHeader(depthMapData)
            # parse bytes into planes of float values
            data = self.parsePlanes(header, depthMapData)
            # compute position and values of pixels
            depthMap = self.computeDepthMap(header, data["indices"], data["planes"])
            if saved_path != '':
                if not os.path.exists(saved_path):
                    os.mkdir(saved_path)

                try:
                    new_name = os.path.join(saved_path, panoId + ".tif")
                    img = self.saveDepthmapImage(depthMap, new_name)
                    with open(os.path.join(saved_path, panoId + '.json'), 'w') as f:
                        json.dump(jdata, f)
                except Exception as e:
                    print("Error in getDepthmapfrmJson() saving depthmap file or json file, panoId, error_info:", panoId, e)

            return depthMap
        except Exception as e:
            print("Error in getDepthmapfrmJson():", e)


    def saveDepthmapImage(self, depthMap, saved_file):
        im = depthMap["depthMap"]

        # print(im)
        im[np.where(im == max(im))[0]] = 0
        # if min(im) < 0:
        #     im[np.where(im < 0)[0]] = 0
        im = im.reshape((depthMap["height"], depthMap["width"]))  # .astype(int)
        # display image
        img = Image.fromarray(im)
        # img.save(saved_file.replace(".tif", 'noflip.tif'))
        # img = img.transpose(Image.FLIP_LEFT_RIGHT)
        # img.save(saved_file, compression="tiff_deflate")  # has bug, cannot read the results correctly
        img.save(saved_file)

        return img

    def compressJson(self, jdata):
        # compressed = copy.deepcopy(jdata)
        try:
            del jdata[1][0][5][0][5][3][2]

            # cannot compress it yet. The following code works fine, but cannot store the base64 string in the json.
            # string_bytes = jdata[1][0][5][0][5][1][2].encode("ascii")
            # compressed_string = zlib.compress(string_bytes)
            # base64_string = base64.b64encode(compressed_string)
            # debase64_string = base64.b64decode(base64_string)
            # uncompressed_string = zlib.decompress(debase64_string)
            # jdata[1][0][5][0][5][1][2] = uncompressed_string.decode('ascii')



        except Exception as e:
            print("Error in compressJson(), error_info:", e)
        return jdata

gsv_dm = gsv_depthmap()

if __name__ == "__main__":
    lon = -77.072465
    lat = 38.985399
    # resp = _getGeoPhotoJS_frm_lonlat(lon, lat)
    # print(resp.text)
    panoId = getPanoId(lon, lat)
    print(panoId)
    saved_path = r'K:\Research\street_view_depthmap'
    getDepthmap_from_panoId(panoId, saved_path)