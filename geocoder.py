import requests
from pyproj import transform, Proj
import warnings
warnings.filterwarnings('ignore')

parcel_to_road_key = "devU01TX0FVVEgyMDIxMDUxNzE5Mjc0NDExMTE3MzE="


def parcel_to_road(address):
    url = f"https://www.juso.go.kr/addrlink/addrLinkApi.do?currentPage=1&countPerPage=1&keyword={address}&confmKey={parcel_to_road_key}&hstryYn=Y&resultType=json"
    res = requests.get(url)
    if res.json()['results']['juso']:
        return res.json()['results']['juso'][0]['roadAddr']
    else:
        print(address)
        raise KeyError('wrong address')


address_to_coords_key = "BFFDEB79-7B96-3F53-B315-DF642A1B4B47"


def address_to_coords(address, road_or_parcel):
    if road_or_parcel == 'road':
        type = "ROAD"
    elif road_or_parcel == 'parcel':
        type = 'PARCEL'
    else:
        raise KeyError("'road_or_parcel' can only be either 'road' or 'parcel")
    url = f"http://api.vworld.kr/req/address?service=address&request=getCoord&key={address_to_coords_key}&format=json&type={type}&address={address}"
    res = requests.get(url)
    if res.json()['response']['status'] == 'OK':
        xy_coords = res.json()['response']['result']['point']
        return [float(xy_coords['y']), float(xy_coords['x'])]
    else:
        if road_or_parcel == "parcel":
            return address_to_coords(parcel_to_road(address), 'road')
        else:
            raise KeyError('wrong address')


def search_road_address(search_keyword):
    search_road_address_key = "devU01TX0FVVEgyMDIxMDYxMzAwNTg1MTExMTI3NjQ="
    url = "https://www.juso.go.kr/addrlink/addrLinkApi.do"
    params = {
        "confmKey": search_road_address_key,
        "currentPage": "1",
        "countPerPage": "1",
        "keyword": search_keyword,
        "resultType": "json"
    }
    res = requests.get(url, params=params)
    if res.json()['results']['juso']:
        juso = res.json()['results']['juso'][0]
        return juso['roadAddrPart1'], (juso['admCd'], juso['rnMgtSn'], juso["udrtYn"], juso['buldMnnm'], juso['buldSlno'])
    else:
        raise KeyError(search_keyword + '를 찾을 수 없음 from search_road_address')


def road_code_to_coords(admin_code, road_code, underground, buld_main, buld_sub):
    road_code_to_coords_key = "devU01TX0FVVEgyMDIxMDYxMzAxMDI0OTExMTI3NjU="

    url = "https://www.juso.go.kr/addrlink/addrCoordApi.do"
    params = {
        "confmKey": road_code_to_coords_key,
        "admCd": admin_code,
        "rnMgtSn": road_code,
        "udrtYn": underground,
        "buldMnnm": buld_main,
        "buldSlno": buld_sub,
        "resultType": "json"
    }
    res = requests.get(url, params=params)
    if res.json()['results']['juso']:
        data = res.json()['results']['juso'][0]
        x, y = transform(Proj(init='epsg:5179'), Proj(init='epsg:4326'), data['entX'], data['entY'])
        return [y, x]
    else:
        raise KeyError(' '.join([admin_code, road_code, underground, buld_main, buld_sub]) +\
                       '를 찾을 수 없음. from road_code_to_coords')

'''res = requests.post("https://eminwon.qia.go.kr/departure/popup/Beobjung.jsp",
                    data={"schCd": "1",
                          "OPTSTR": "영동대로3길"},
                    verify=False)
res.encoding = "utf-8"
idx = res.text.find("javascript:fnSend") + len("javascript:fnSend")
road_code = res.text[idx + 2: idx + 2 + 12]'''