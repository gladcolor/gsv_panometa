import gsv_panometa as gsv
import os

# determine a location
lon = -77.072465
lat = 38.985399

# get the ID of the nearest panorama
panoId = gsv.getPanoId(lon, lat)

# set the saving path
saved_path = os.getcwd()

# get the depthmap
if gsv.getDepthmap_from_panoId(panoId, saved_path):
    print(f"Processed panorama {panoId}!\nTest passed!")
else:
    print("Test failed!")