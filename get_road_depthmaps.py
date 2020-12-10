import gsv_panometa as gsv
import os
import pandas as pd

def read_seedpoins(csv_file):
    df = pd.read_csv(csv_file)
    return df


def get_depthmaps(csv_file, saved_path, max_steps=200):

    df_pts = read_seedpoins(csv_file)
    for idx, row in df_pts.iterrows():
        try:
            print("Processing row: ", idx)
            lon = row['LON']
            lat = row['LAT']
            panoId = row['panoId']
            if len(panoId) > 20:
                gsv.getDepthmap_from_panoId(panoId, saved_path)
            # print(lon)
        except Exception as e:
            print("Error in get_depthmaps(): ", e)
            continue



if __name__ == "__main__":
    saved_path = r'L:\Datasets\HamptonRoads\road_depthmaps'
    csv_file = r'L:\Datasets\HamptonRoads\EC-latlon-panoId.csv'
    get_depthmaps(csv_file, saved_path)