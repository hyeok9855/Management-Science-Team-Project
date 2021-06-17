import json
import numpy as np
import pandas as pd
import xmltodict
import time
from utils.geocoder import *
from pyproj import transform, Proj


# 서울시 문화재 정보
def get_heritage_coords(file_path="data/heritage_coords.json"):
    try:
        with open(file_path, "r") as fp:
            heritage = json.load(fp)
        return heritage

    except FileNotFoundError:
        heritage = {}

        params3 = {
            "stCcbaAsdt": 0,
            "enCcbaAsdt": 2022,
            "ccbaCtcd": "11",
            "ccbaCncl": "N",
            "pageUnit": 1000000,
        }
        url3 = f"http://www.cha.go.kr/cha/SearchKindOpenapiList.do"
        res3 = requests.get(url3, params3)

        data = xmltodict.parse(res3.text)
        for row in data['result']['item']:
            if row['ccbaKdcd'] in ['11', '12', '13', '14', '15', '16', '21']:
                if row['longitude'] != '0':
                    heritage[row['ccbaMnm1']] = (row['latitude'], row['longitude'])

        with open(file_path, "w") as fp:
            json.dump(heritage, fp)

        return heritage


# --------------------------------------------------------------- #


# 서울시 학교 기본정보
def get_school_coords(file_path="data/school_coords.json", error_file_path="data/error_school_address.json",
                      key="6d70667469687965313132704a757478"):
    try:
        with open(file_path, "r") as fp:
            school_coords = json.load(fp)
        return school_coords
    except FileNotFoundError:
        school_coords = {}
        error_address = {}
        _from = 1
        _to = 1000
        while True:
            url4 = f"http://openapi.seoul.go.kr:8088/{key}/json/neisSchoolInfo/{_from}/{_to}/"
            res4 = requests.get(url4)
            data = res4.json().get("neisSchoolInfo")
            if "ERROR-332" in str(res4.content)[:100]:
                break
            elif data:
                for row in data["row"][2:]:
                    scl_name = row['SCHUL_NM']
                    scl_address = row["ORG_RDNMA"]
                    try:
                        road_addr, address_codes = search_road_address(scl_name)
                        # print(address_codes)
                        if road_addr != row["ORG_RDNMA"]:
                            raise AssertionError("찾은 주소가 원 주소랑 다릅니다!")
                        coords = road_code_to_coords(*address_codes)
                        school_coords[scl_name] = coords
                        print(scl_name, coords)
                    except Exception as e1:
                        try:
                            coords = address_to_coords(scl_address, 'road')
                            school_coords[scl_name] = coords
                            print(coords)
                        except Exception as e2:
                            print(e1)
                            print(e2)
                            print(scl_name, scl_address)
                            error_address[scl_name] = scl_address

                            # 서울안암초등학교: [37.590995292645225, 127.02760787629121]
                            if "scl_name" == "서울안암초등학교":
                                school_coords[scl_name] = [37.590995292645225, 127.02760787629121]
                            # 서울개포초등학교 -> 폐업함
                            # 서울국악예술고등학교 -> 국립전통예술고등학교 (교명 변경)

                    time.sleep(0.5)

                _from, _to = _to + 1, _to + 1000

                print(f"{_to} / ???????")

                last_n_rows = len(data['row'])
            else:
                print(f"Finished!\ntotal # samples {_from + last_n_rows}")
                break

        with open(file_path, "w") as fp:
            json.dump(school_coords, fp)

        with open(error_file_path, "w") as fp:
            json.dump(error_address, fp)

        return school_coords


# ----------------------------------------------------------- #


# 전국 LPG 충전소 현황
def get_LPG_coords(file_path="data/lpg_coords.csv"):
    try:
        return pd.read_csv(file_path, header=0)
    except FileNotFoundError:
        LPG = pd.read_csv("../public_data/한국가스안전공사_전국 LPG 충전소 현황_20200824.csv", header=0, encoding='cp949')
        LPG.drop(LPG.index[LPG['행정 구역'].str[:2] != '서울'], axis=0, inplace=True)
        coord_lst = []
        for i in LPG.index:
            coord_lst.append(address_to_coords(LPG.loc[i, '소재지'], 'parcel'))
        LPG['coords'] = pd.Series(coord_lst)

        LPG.to_csv(file_path, header=True, index=False)
        return LPG


# ----------------------------------------------- #


def get_lpg_with_house_polygon(LPG, file_path="data/lpg_with_away_buildings.csv"):
    try:
        return pd.read_csv(file_path, header=0)
    except FileNotFoundError:
        LPG_with_away_buildings = LPG[["업소명", "coords"]]
        LPG_with_away_buildings["lats"] = np.empty((LPG.shape[0], 0)).tolist()
        LPG_with_away_buildings["longs"] = np.empty((LPG.shape[0], 0)).tolist()

        for idx in LPG.index:
            lat, long = tuple(eval(LPG.loc[idx, "coords"]))
            tm_x, tm_y = transform(Proj(init='EPSG:4326'), Proj(init='EPSG:5174'), long, lat)

            bbox = f"{tm_x - 75},{tm_y - 75},{tm_x + 75},{tm_y + 75},EPSG:5174"
            params = {
                "ServiceKey": "VnUwgSZ6vW87ddKplDlj1Qc8R+nAJ+0eb4AcHGqy87dJphB2zdXRnJB/z2UP06cSJC/pDUdmzyRRykWpBVdbFQ==",
                "typeName": "F253",
                "bbox": bbox,
                "maxFeatures": "100",
                "srsName": "EPSG:4326",
                "resultType": "results",
            }
            url = f"http://apis.data.go.kr/1611000/nsdi/BuildingUseService/wfs/getBuildingUseWFS"
            res = requests.get(url, params=params)

            data = xmltodict.parse(res.text)["wfs:FeatureCollection"]
            buildings = data.get('gml:featureMember')
            if not buildings:
                print(LPG.loc[idx, "업소명"], buildings)
            if buildings:
                print(LPG.loc[idx, "업소명"], len(buildings))

                count = 1
                for bld in buildings:
                    try:
                        dic = bld["NSDI:F253"]
                    except TypeError:
                        dic = buildings["NSDI:F253"]

                    if dic["NSDI:MAIN_PRPOS_CODE"][:2] in ["02", "09", "11"]:  # 공동주택, 의료시설, 노유자시설

                        print(count, end=" ")
                        count += 1

                        polygon = dic["NSDI:SHAPE"]["gml:Polygon"]["gml:exterior"]["gml:LinearRing"]["gml:posList"]
                        polygon = list(map(float, polygon.split(' ')))
                        LPG_with_away_buildings.loc[idx, "lats"].append(polygon[1::2])
                        LPG_with_away_buildings.loc[idx, "longs"].append(polygon[::2])
            print()

        LPG_with_away_buildings.to_csv(file_path, header=True, index=False)
        return LPG_with_away_buildings

if __name__ == "__main__":
    heritage = get_heritage_coords()
    school = get_school_coords()
    LPG = get_LPG_coords()
    LPG_with_away_buildings = get_lpg_with_house_polygon(LPG)
