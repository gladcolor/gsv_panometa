import gsv_panometa as gsv
import os

lon = -77.072465
lat = 38.985399

panoId = gsv.getPanoId(lon, lat)

saved_path = os.getcwd()
if gsv.getDepthmap_from_panoId(panoId, saved_path):
    print(f"Processed panorama {panoId}!\nTest passed!")
else:
    print("Test failed!")