import requests
import json
import base64
import numpy as np
import struct
import PIL
import os

import zlib

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
    return gsv_dm.getDepthmapfrmJson(jdata, saved_path)


def _getPanometaJS_from_panoId(panoId):
    url = "https://www.google.com/maps/photometa/v1?authuser=0&hl=zh-CN&pb=!1m4!1smaps_sv.tactile!11m2!2m1!1b1!2m2!1szh-CN!2sus!3m3!1m2!1e2!2s{}!4m57!1e1!1e2!1e3!1e4!1e5!1e6!1e8!1e12!2m1!1e1!4m1!1i48!5m1!1e1!5m1!1e2!6m1!1e1!6m1!1e2!9m36!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e3!2b1!3e2!1m3!1e3!2b0!3e3!1m3!1e8!2b0!3e3!1m3!1e1!2b0!3e3!1m3!1e4!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e3"
    url = url.format(panoId)
    return requests.get(url, proxies=None)

def _getGeoPhotoJS_frm_lonlat(lon, lat):
    url = "https://maps.googleapis.com/maps/api/js/GeoPhotoService.SingleImageSearch?pb=!1m5!1sapiv3!5sUS!11m2!1m1!1b0!2m4!1m2!3d{0:}!4d{1:}!2d50!3m10!2m2!1sen!2sGB!9m1!1e2!11m4!1m3!1e2!2b1!3e2!4m10!1e1!1e2!1e3!1e4!1e8!1e6!5m1!1e2!6m1!1e2&callback=_xdc_._v2mub5"
    url = url.format(lat, lon)
    return requests.get(url, proxies=None)


class gsv_depthmap(object):
    def parse(self, b64_string, compressed=True):
        # print("\nb64_string: ", b64_string)
        # print("len(b64_string): ", len(b64_string))
        # fix the 'inccorrect padding' error. The length of the string needs to be divisible by 4.

         # data = b64_string

        b64_string += "=" * ((4 - len(b64_string) % 4) % 4)
        b64_string = b64_string.replace("-", "+").replace("_", "/")

        data = base64.b64decode(b64_string)  # decode the string

        if compressed:
            # print("uncompressing")
            try:
                data = base64.b64decode(b64_string)
                data = zlib.decompress(data)  # decompress the data
                data = data.decode("ascii")
                data += "=" * ((4 - len(data) % 4) % 4)
                data = data.replace("-", "+").replace("_", "/")
                data = base64.b64decode(data)
            except Exception as e:
                print("Error in uncompressing: ", e)


        # convert the URL safe format to regular format.
        # b64_string += "=" * ((4 - len(b64_string) % 4) % 4)
        # data = b64_string.replace("-", "+").replace("_", "/")



        # data = base64.b64decode(data)  # decode the string
        #
        # data = b64_string.encode("utf-8")
        # print(type(data))
        # print(len(data))
        # print(data)
        data = np.array([d for d in data])
        # print(data)

        return data

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
            depthMapData = self.parse(jdata[1][0][5][0][5][1][2], compressed=True)
            panoId = jdata[1][0][1][1]

            # depthMapData = self.parse(jdata[1][0][11], compressed=True)
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
            # print("len(jdata[1][0][5][0][5][1][2]):", len(jdata[1][0][5][0][5][1][2]))

            string_bytes = jdata[1][0][5][0][5][1][2].encode("ascii")

            # print("len(string_bytes):", len(string_bytes))
            compressed_string = zlib.compress(string_bytes)
            # print("compressed_string:", compressed_string)
            # print("len(compressed_string):", len(compressed_string))
            # print("compressed_string:", compressed_string.decode("utf-8"))

            # compressed_string = b"eJzt131wFPUdx_G7EEJSNJeExzwQCCGCITwkAi3NLrsJtlEL2lY6MC3WYaYwOFiR-gAWyRZaE8WWhwpalKEgtII81Maq0Fz4gaWtBYtt6aApIk-llAFqisgodZjeQx4vd7_bvdvffXdvP-9_mMll5va3r88tl_SJLleKy53uQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQgghhBBCCCGEEEIIIYQQQv5SOkd9MUh8KbqjvlJkavrhsYPkKmZ5rMDumUKPEdgyk-2xARslyB4bsEOC8TEBK5cQfEzAmiUQHxOwWgnHxwQsFJE-FmCJCPWxAPKI9f1R3wIHR03fGvVtcGjU7J2ivhUOjJo8JOrb4bCoucNEfUucFLV12KhvimOiho4Y9Y1xRtTKkaO-M06I2piXh_rmJH_UxNzgLzpqYX7wFxw1cJTgLzhq4CjBX3DUwFGCv-CogaPkwQAERy3MD_6ioxbmB3_RUQvzg7_oqIX5wV901ML84C86amF-8BcdtTA_-IuOWpgf_EVHLcwP_qKjFuYHf9FRC_ODv-iohfnBX3TUwvzgLzpqYX7wFx21MD_4i45amB_8RUctzA_-oqMW5gd_0VEL84O_6KiF-cFfdNTC_OAvOmphfvAXHbUwP_iLjlqYH_xFRy3MD_6ioxbmB3_RUQvzg7_oqIX5wV901ML84C86amF-8BcdtTA_-IuOWpgf_EVHLcwP_qKjFuYHf-FRE3ODv_CoibnBX3jUxNzgLzxqYm7wFx41MTf4C4-amBv8hUdNzA3-wqMm5kbu3zNSxNdlXtTE3Gj8I6KHLyuL4iLNipqYW2L9Dbp3-GfZeALUxNwS5B8jPPxFlwD_-OzhLzT4C4-amBv8hUdNzA3-wqMm5maqf_g_2uFv4UzzD0pFfgX-lswU_w4p_qvwt1wm-HeWivY6_C2WeP_4-eEvLvgLj5qYG_yFR03MDf7CoybmZty_b9-QH8CfHzUxN2P-A_v6C_kh_Dnl5eVRE3Pz-_frp-8sAwfC32j28Ne3APgbzy7-egYAf-PBH_5WDv5is7H_YNfgwV1-AH_9DW0N_snpf0O3cnNzC9sqbg3-dvfv7swvN1j7DuBvE__P8YtpBb7ycgupibnp8q8I_qPDf1Brw4b5XsgJROzfK1AUXQMZXwE1MTePp6ws4F86ZMyY0aNdI0eO9N20sWPLXKWlpUPaco0YMaKkpM2_xFd-fhv1oM5SOZ3K9ldQYJZ_747Se8Vewpdgdf_y8oD_cH_jvzBuws2-BnRvWLCb_OV0qYt_dmsFBQU3BhPgH9iArzhmYO4WuAOgJubm8eTkBPxHjRpV1F6OgT6f3VFBB3ug_r7M8k_1FWYDZuzA7DV0_R-ImpibxxPmsz4gP6J2dphC0Nvg_fXolAn-nA2Yt4MYNhHpy0eGP2pibh5PfphuDMccQt7NPCK8gdxhC_hnZqamRthAlxGIGUL3In_lzOgaNTE3jycsY9QPeCT4GN35_r4yg6WmRhxB6AaELUGPuc39s6Nym_R51-0fdgHRHwSmjkGXtu38wz7fE_NpN-QfaQJGR6BjGWF-wZB4l1Kpibnp9xckbsQ_4gLMGUHkYqUPRE3MLTy_YOXY_XkL0P2dIAH6XS6K2piXh4w6bNH9o07A7EdBPPKW34DF-PX565iAaTOIX97SG7Crv74FxD0Dc9wtuwFq7e7p9zcygRiHYCK79UZALR0-Q_7GJxBpCuHGYLK5hUZAjczL6ABinoA1gn1Ixv3bF2DTCfgDfVux-Nv-KdCWo-WDxeqfFBNIS0tzrnywOPztP4G01pwI31p8_jbfQJt_WsdpokJ3_RVqvriL399t3y-EYfz11ScQtZ0ZmeJv1w3E7N-2APtPwDT_ziOgdtVbHP7uJHkImOvvz0YPgvj8k-IhYCp9R_YYQbz-bvtPwDzycFl8Bib4u20-AZOg-Vl1Bub4u-08ATN4jZSZaaExmMUfyJ4TMOXo8ZcE_m5bPgbMOnqcJYe_P5ttwMyjx1Hy-Puz0QbMPnqMJZd_IHuMQMjRjZeE_sGsvgKBRzdS0voHs-4KhB9dX0nu316f8Etwk9gH3tkaOcU_UvCHP_zhD3_4wx_-8Ic__OEPf_g7YQCk_PAnD_7whz_84Q9_-MMf_vCHP_zhD3_4w1-oP_Xh3fCHP_zhD3_4wx_-8Ic__OEPf_jDH_7wh39yDwD-8Kfihz998Ic__OEPf_jDH_6J9Kc-uz_4wx_-8Ic__OEPf_jDH_7wd8oACPnhb4HgD3_4wx_-8E-wP_XRA8Ef_vCHP_zh78QBwB_-NPzwhz998Kfypz55MPjDH_7wd-oA4A9_En74O9uf-uCtwR_-8Ie_UwdAxQ9_Z_tTn7st-MPfyQMg4oe_s_2pj90e_OHv5AHQ8FvHn3wAxMen8Sc-dOeo_YkHQMIPf2f70x65a9T8xANwOr8F_EkHQMAP_9AIj-90fkv4Ew7A6fzW8KcbgNP5LeJPNoAE81MdM3LU8O3RHD-h-hbkt44_zQIcrm8pf4oFJEw_8UfTFzV5aIk9vcPx3dbz95e40zvb3h-1deQScXqh8lanD0bNHDWRhxfiLvKCzY-a12hmnt2R4KFRgwpI58mT31Zf1Fw0Ud91C0ZNkoio77GlcoV0094zQ-veWO594arGNvbNU39y53xl-bbX9u5ZXi-NOPYP9ejFisb3186QMq5prGpPrvrplErpldc2eOd9qLE9xweotZM1tuvkuqbTFcXeXtK6qju8K0oeeuktueFALXv7WK56R-EJaf3H871bT2qMPZqlzi1skWqOrJBONmts9ZnRqjZtiVT_wRFp0mmNHWy-RS1OuSr9bewU7zePa-y7d2arE-9ZKOWtrm96a67GNs_8WKm4f4B89PZ8b_VfNNZQWqRqFR819pZ-L1Vc0NjPvpKlrvpFhbRx__mmg3fVstSnLyjbry1WTqwdN2n8nlSppe9zSvN5je2v3e91fVruHffmM1V_ri5qvHy2WP7qIY3NPnlNeXHa4crdYx6QD6_U2IbH9inji4c3Zo_Ok6f_VWMrs3PUXy1OZy_9dAa7ujRdOnfzrdW3rNGUNY_Mbtr3Xo00Y2FW1bKMYY3bt5z2vvEvjWUOldXiE3WVK1Pq5Ovf01jNgp8rl5bXsjNr35Nd56d5Hxw4uEo5d0Da_Ot___aTixoremeQOv1Uw6TC5vlKwc7JXtZ8tmr237c0HmtYKm9YrLHdLduVL_3hw8ZFn-2Uv5atsXO3rVLcmSu-eDz9VFPRQ7XshR35Vf1TNldO3fdMZd11jblreqqX352vPPJOw94vX62Tru0ur378k3J5WfoDsnK3xtYU9lAPzhgurUpfIs_VNNa0fo_yn3lD5WfX53mf-pPGjhyU1YE9N0kNg2Y1XrmssXXF_dUXz6rSpDHnvN86pbFZB15Wr12_PHH-iJ5Nfq8Fy1ZXff_2ftLd11fJR2ZoTN60VHn9h-nSZ68837S0WmOXTpZVvVsqyfnbviHXztLYDxZMVDMWHZXydjwh773Ht6ff_VK5b9QuaVrJrsrqFo29Wv8_dc7DV6T3mSrVfKCxQ1P6VT32VJp8W_oi-a7v-DxePqds_bRIenzHKPnYfo31fDBL3fzw29L5Jx-VSv_pe7-S9Kp-m0bK9079sTy9TGNpZ8uUZ8s3SK8-sV9a4rv-w_I2dea2XpVDB_ym8YTvfrUUvK4WXZqpFKhutmrfWumPNYuqt1zoI--avEI-OsH3_h_NVe473EOeU7JWvjJGY98ePUFZv65F8g55Wr51isbenFqnbNma0XTo3oNNNzxfq3iVncrGH329cXj9ZXlZRS27v_mS_Fz9f6WlvefJixZqbM6hi8r_AXMBMr0"
            # print("len(compressed_string):", len(compressed_string))


            base64_string = base64.b64encode(compressed_string)
            # base64_string = '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'
            # base64_string = bytes('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'.encode("utf-8"))
            # print("len(base64_string):", len(base64_string))
            # print("base64_string:", base64_string)

            debase64_string = base64.b64decode(base64_string)
            # print("len(debase64_string):", len(debase64_string))

            uncompressed_string = zlib.decompress(debase64_string)
            # print("len(uncompressed_string):", len(uncompressed_string))
            # print("uncompressed_string:", uncompressed_string)

            # print("base64_string:", base64_string.decode("ascii"))
            jdata[1][0][5][0][5][1][2] = base64_string.decode('ascii')
            # jdata[1][0][5][0][5][1][2] = uncompressed_string.decode('ascii')
            # jdata[1][0][10] =

            # jdata[1][0][11] = base64_string.decode('ascii')




        except Exception as e:
            print("Error in compressJson(), error_info:", e)
        return jdata

gsv_dm = gsv_depthmap()

def gsv_panometa_test():
    lon = -77.072465
    lat = 38.985399


    panoId = getPanoId(lon, lat)

    saved_path = os.getcwd()
    if getDepthmap_from_panoId(panoId, saved_path):
        print(f"Processed panorama {panoId}!\nTest passed!")
    else:
        print("Test failed!")

if __name__ == "__main__":
    gsv_panometa_test()