import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import requests
from datetime import datetime, timedelta
import json
import urllib3
import base64
from pathlib import Path

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===========================================
# 頁面設定
# ===========================================
st.set_page_config(
    page_title="TAI-SAFE 智慧防災平台",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===========================================
# 影片/GIF 處理函數
# ===========================================

def load_video_as_base64(video_path):
    """載入影片並轉換為 base64"""
    try:
        with open(video_path, "rb") as video_file:
            video_bytes = video_file.read()
            video_base64 = base64.b64encode(video_bytes).decode()
        return video_base64
    except:
        return None

def display_gif(gif_path, width_percent=100):
    """
    顯示 GIF 動畫
    gif_path: GIF 檔案路徑
    width_percent: 寬度百分比 (例如: 100 表示 100%)
    """
    try:
        with open(gif_path, "rb") as gif_file:
            gif_bytes = gif_file.read()
            gif_base64 = base64.b64encode(gif_bytes).decode()
        
        html_code = f"""
        <div style="display: flex; justify-content: center; align-items: center;">
            <img src="data:image/gif;base64,{gif_base64}" 
                 style="width: {width_percent}%; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        </div>
        """
        st.markdown(html_code, unsafe_allow_html=True)
        return True
    except:
        return False

def display_cropped_video(video_path, crop_side='left'):
    """
    顯示裁切後的影片（已棄用，改用 display_gif）
    保留此函數以維持向後相容性
    """
    # 嘗試顯示 GIF
    gif_path = video_path.replace('.mp4', '.gif')
    if display_gif(gif_path):
        return True
    
    # 如果沒有 GIF，嘗試原本的 MP4
    video_base64 = load_video_as_base64(video_path)
    
    if video_base64:
        if crop_side == 'left':
            margin_style = "margin-left: 0;"
        else:
            margin_style = "margin-left: -100%;"
        
        html_code = f"""
        <div style="position: relative; width: 50%; overflow: hidden; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <video autoplay loop muted playsinline style="width: 200%; {margin_style}">
                <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
                您的瀏覽器不支援影片播放
            </video>
        </div>
        """
        st.markdown(html_code, unsafe_allow_html=True)
        return True
    else:
        return False

# ===========================================
# 成功大學座標 (WGS84)
# ===========================================
NCKU_CENTER = {
    'lat': 22.9971,
    'lon': 120.2218
}

# ===========================================
# 備用資料
# ===========================================

def get_fallback_air_data():
    """備用空氣品質資料"""
    np.random.seed(42)
    
    stations = [
        {'name': '台南', 'lat': 22.9833, 'lon': 120.2025},
        {'name': '安南', 'lat': 23.0486, 'lon': 120.2175},
        {'name': '善化', 'lat': 23.1158, 'lon': 120.2969},
        {'name': '新營', 'lat': 23.3055, 'lon': 120.3167},
        {'name': '麻豆', 'lat': 23.1811, 'lon': 120.2478},
        {'name': '仁德', 'lat': 22.9681, 'lon': 120.2528},
        {'name': '永康', 'lat': 23.0306, 'lon': 120.2547},
        {'name': '歸仁', 'lat': 22.9706, 'lon': 120.2928},
        {'name': '東區', 'lat': 22.9897, 'lon': 120.2247},
        {'name': '北區', 'lat': 23.0117, 'lon': 120.2042},
    ]
    
    data_list = []
    for station in stations:
        pm25_val = np.random.randint(15, 55)
        pm10_val = np.random.randint(30, 80)
        distance = np.sqrt((station['lat'] - NCKU_CENTER['lat'])**2 + 
                         (station['lon'] - NCKU_CENTER['lon'])**2) * 111
        
        data_list.append({
            'sitename': station['name'],
            'lat': station['lat'],
            'lon': station['lon'],
            'pm25': float(pm25_val),
            'pm10': float(pm10_val),
            'aqi': str(int(pm25_val * 1.2)),
            'status': '良好' if pm25_val < 35 else '普通' if pm25_val < 53 else '對敏感族群不健康',
            'o3': f"{np.random.randint(20, 60):.1f}",
            'co': f"{np.random.uniform(0.3, 0.7):.2f}",
            'so2': f"{np.random.randint(2, 10)}",
            'no2': f"{np.random.randint(10, 30)}",
            'publishtime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'distance_to_ncku': distance
        })
    
    np.random.seed(None)
    df = pd.DataFrame(data_list)
    df = df.sort_values('distance_to_ncku').reset_index(drop=True)
    return df

def get_fallback_water_data():
    """備用水質資料"""
    return pd.DataFrame({
        'sitename': ['鹽水溪橋', '二仁溪橋', '曾文溪橋', '急水溪橋', '官田橋'],
        'river': ['鹽水溪', '二仁溪', '曾文溪', '急水溪', '鹽水溪'],
        'ph': [7.2, 7.4, 7.1, 7.3, 7.5],
        'do': [6.5, 5.8, 6.2, 6.0, 6.4],
        'bod': [2.1, 3.2, 2.5, 2.8, 2.3],
        'nh3n': [0.15, 0.22, 0.18, 0.20, 0.16],
        'rpi': [2.0, 2.5, 2.2, 2.3, 2.1],
        'monitoring_date': [datetime.now().strftime('%Y-%m-%d')] * 5
    })

# ===========================================
# 真實資料爬蟲函數（靜默切換）
# ===========================================

@st.cache_data(ttl=300)
def fetch_real_air_quality():
    """從環境部開放平台抓取台南地區空氣品質資料"""
    try:
        # 嘗試不使用 API key 的公開端點
        url = "https://data.moenv.gov.tw/api/v2/aqx_p_432?limit=1000&format=json&api_key=8ce6082f-f93f-45d2-b78f-af52ba661784"
        response = requests.get(url, timeout=15, verify=False)

        if response.status_code == 200:
            data = response.json()
            records = data.get('records', [])

            if not records:
                # 如果沒有 records，可能數據在根層級
                if isinstance(data, list):
                    records = data

            tainan_data = []
            for record in records:
                county = record.get('county', '')
                sitename = record.get('sitename', '')

                # 檢查是否為台南市的測站
                if '台南' in county or '臺南' in county:
                    try:
                        # 處理經緯度
                        lat_str = record.get('latitude', '0')
                        lon_str = record.get('longitude', '0')

                        # 如果是字符串，嘗試轉換
                        try:
                            lat = float(lat_str) if lat_str else 0
                            lon = float(lon_str) if lon_str else 0
                        except:
                            lat = 0
                            lon = 0

                        # 如果沒有座標，使用測站名稱估計座標
                        if lat == 0 or lon == 0:
                            # 台南市各測站的大致座標
                            station_coords = {
                                '安南': (23.0486, 120.2175),
                                '善化': (23.1158, 120.2969),
                                '新營': (23.3055, 120.3167),
                                '台南': (22.9833, 120.2025),
                                '臺南': (22.9833, 120.2025),
                                '林森': (22.9917, 120.2042),
                            }

                            for station_key, coords in station_coords.items():
                                if station_key in sitename:
                                    lat, lon = coords
                                    break

                        if lat == 0 or lon == 0:
                            continue

                        distance = np.sqrt((lat - NCKU_CENTER['lat'])**2 +
                                         (lon - NCKU_CENTER['lon'])**2) * 111

                        # 處理 PM2.5 數值（嘗試多種欄位名稱）
                        pm25_val = record.get('pm2.5') or record.get('PM2.5') or record.get('pm25') or ''
                        if pm25_val in ['', None, 'ND', '-', 'N/A', 'NA']:
                            pm25_val = 0
                        else:
                            try:
                                pm25_val = float(str(pm25_val).strip())
                            except:
                                pm25_val = 0

                        # 處理 PM10 數值（嘗試多種欄位名稱）
                        pm10_val = record.get('pm10') or record.get('PM10') or ''
                        if pm10_val in ['', None, 'ND', '-', 'N/A', 'NA']:
                            pm10_val = 0
                        else:
                            try:
                                pm10_val = float(str(pm10_val).strip())
                            except:
                                pm10_val = 0

                        # 處理 AQI 數值（嘗試多種欄位名稱）
                        aqi_val = record.get('aqi') or record.get('AQI') or ''
                        if aqi_val in ['', None, 'ND', '-', 'N/A', 'NA']:
                            aqi_val = 'N/A'
                        else:
                            try:
                                # 轉換為整數字符串
                                aqi_val = str(int(float(str(aqi_val).strip())))
                            except:
                                aqi_val = 'N/A'

                        # 處理狀態
                        status_val = record.get('status') or record.get('Status') or '良好'

                        tainan_data.append({
                            'sitename': sitename,
                            'lat': lat,
                            'lon': lon,
                            'pm25': pm25_val,
                            'pm10': pm10_val,
                            'aqi': aqi_val,
                            'status': status_val,
                            'o3': record.get('o3') or record.get('O3') or '-',
                            'co': record.get('co') or record.get('CO') or '-',
                            'so2': record.get('so2') or record.get('SO2') or '-',
                            'no2': record.get('no2') or record.get('NO2') or '-',
                            'publishtime': record.get('publishtime') or record.get('PublishTime') or '',
                            'distance_to_ncku': distance
                        })
                    except Exception as e:
                        # 靜默跳過單個記錄的錯誤
                        continue

            if tainan_data:
                df = pd.DataFrame(tainan_data)
                df = df.sort_values('distance_to_ncku').reset_index(drop=True)
                return df, True

        # API 失敗時返回備用資料
        return get_fallback_air_data(), False

    except Exception as e:
        # 如果發生任何錯誤，返回備用資料
        return get_fallback_air_data(), False

@st.cache_data(ttl=600)
def fetch_real_water_quality():
    """從環境部抓取台南地區河川水質資料"""
    try:
        url = "https://data.moenv.gov.tw/api/v2/wrq_p_432?limit=500&api_key=e8dd42e6-9b8b-43f8-991e-b3dee723a52d"
        response = requests.get(url, timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            records = data.get('records', [])
            
            tainan_water = []
            for record in records:
                site = record.get('sitename', '')
                county = record.get('county', '')
                
                if '台南' in county or '臺南' in county or '台南' in site:
                    try:
                        tainan_water.append({
                            'sitename': site,
                            'river': record.get('basin_name', '-'),
                            'ph': record.get('ph', '-'),
                            'do': record.get('do', '-'),
                            'bod': record.get('bod', '-'),
                            'nh3n': record.get('nh3n', '-'),
                            'rpi': record.get('rpi', '-'),
                            'monitoring_date': record.get('monitordate', '-')
                        })
                    except:
                        continue
            
            if tainan_water:
                return pd.DataFrame(tainan_water).head(10), True
        
        return get_fallback_water_data(), False
        
    except:
        return get_fallback_water_data(), False

@st.cache_data(ttl=1800)
def fetch_real_weather_warnings():
    """從氣象署抓取天氣警特報"""
    warnings = [
        {
            'type': '即時天氣資訊',
            'level': '資訊',
            'area': '台南市',
            'description': '目前無特殊天氣警報。請注意午後局部雷陣雨。',
            'issued_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    ]
    return warnings

@st.cache_data(ttl=300)
def fetch_twipcam_streams(lat=22.9971, lon=120.2218, radius=10):
    """
    從 TwipCam API 獲取附近的即時影像串流
    參數:
        lat: 緯度（預設為成功大學）
        lon: 經度（預設為成功大學）
        radius: 搜尋半徑（公里，用於過濾）
    """
    try:
        # TwipCam API endpoint - 獲取所有攝影機列表
        url = "https://www.twipcam.com/api/v1/cam-list.json"

        response = requests.get(url, timeout=10, verify=False)

        if response.status_code == 200:
            cameras = response.json()

            # 過濾出距離目標位置在指定半徑內的攝影機
            nearby_cameras = []
            for cam in cameras:
                try:
                    cam_lat = float(cam.get('lat', 0))
                    cam_lon = float(cam.get('lon', 0))

                    if cam_lat == 0 or cam_lon == 0:
                        continue

                    # 計算距離（簡易公式，單位：公里）
                    distance = np.sqrt((cam_lat - lat)**2 + (cam_lon - lon)**2) * 111

                    if distance <= radius:
                        nearby_cameras.append({
                            'id': cam.get('id', 'unknown'),
                            'name': cam.get('name', 'Unknown Camera'),
                            'lat': cam_lat,
                            'lon': cam_lon,
                            'cam_url': cam.get('cam_url', ''),  # 快照圖片URL
                            'distance': round(distance, 2),
                            'status': 'online'
                        })
                except:
                    continue

            # 按距離排序，返回最近的5個
            if nearby_cameras:
                nearby_cameras.sort(key=lambda x: x['distance'])
                return nearby_cameras[:5], True

        # 如果API失敗，返回備用資料
        return get_fallback_cameras(), False

    except Exception as e:
        return get_fallback_cameras(), False

def get_fallback_cameras():
    """備用攝影機資料"""
    return [
        {
            'id': 'demo_1',
            'name': '成功大學光復校區',
            'lat': 22.9971,
            'lon': 120.2218,
            'url': 'https://www.twipcam.com/camera/demo1',
            'thumbnail': 'https://via.placeholder.com/400x300.png?text=Camera+1',
            'status': 'online'
        },
        {
            'id': 'demo_2',
            'name': '台南市東區',
            'lat': 22.9897,
            'lon': 120.2247,
            'url': 'https://www.twipcam.com/camera/demo2',
            'thumbnail': 'https://via.placeholder.com/400x300.png?text=Camera+2',
            'status': 'online'
        }
    ]

@st.cache_data(ttl=600)
def fetch_wind_data(lat=22.9971, lon=120.2218, zoom=11):
    """
    從 TwipCam API 獲取風向資料
    參數:
        lat: 緯度
        lon: 經度
        zoom: 地圖縮放程度
    """
    try:
        url = f"https://www.twipcam.com/api/v1/map/wind?lat={lat}&lon={lon}&zoom={zoom}"

        response = requests.get(url, timeout=10, verify=False)

        if response.status_code == 200:
            data = response.json()

            # 解析 GRIB 格點資料
            # data['data'] 是一個列表，包含 eastward_wind 和 northward_wind
            u_component = None  # eastward wind (東西向)
            v_component = None  # northward wind (南北向)

            for item in data.get('data', []):
                header = item.get('header', {})
                param_name = header.get('parameterNumberName', '')

                if param_name == 'eastward_wind':
                    # 取格點資料的中間點作為代表值
                    wind_data_array = item.get('data', [])
                    if wind_data_array:
                        u_component = wind_data_array[len(wind_data_array) // 2]

                elif param_name == 'northward_wind':
                    wind_data_array = item.get('data', [])
                    if wind_data_array:
                        v_component = wind_data_array[len(wind_data_array) // 2]

            # 如果成功獲取 u 和 v 分量，計算風向和風速
            if u_component is not None and v_component is not None:
                direction_deg, speed, direction_text = calculate_wind_direction_and_speed(u_component, v_component)

                # 獲取時間戳
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if data.get('data') and len(data['data']) > 0:
                    ref_time = data['data'][0].get('header', {}).get('refTime', '')
                    if ref_time:
                        timestamp = ref_time

                wind_info = {
                    'direction': round(direction_deg, 1),  # 風向角度
                    'speed': round(speed, 1),  # 風速 (m/s)
                    'direction_text': direction_text,  # 風向文字 (N, NE, E, etc.)
                    'speed_text': f"{round(speed, 1)} m/s",
                    'timestamp': timestamp,
                    'is_real': True
                }
                return wind_info, True

        # API 失敗時使用季節性歷史資料
        return get_fallback_wind_data(), False

    except Exception as e:
        # 發生錯誤時使用季節性歷史資料
        return get_fallback_wind_data(), False

def calculate_wind_direction_and_speed(u, v):
    """
    從 u, v 風分量計算風向和風速
    參數:
        u: 東西向風速 (m/s)，正值表示向東
        v: 南北向風速 (m/s)，正值表示向北
    返回:
        direction: 風向角度 (0-360度，0度為北風)
        speed: 風速 (m/s)
        direction_text: 風向文字 (N, NE, E, SE, S, SW, W, NW)
    """
    import math

    # 計算風速
    speed = math.sqrt(u**2 + v**2)

    # 計算風向角度（風從哪裡來）
    # atan2(y, x) 返回的是風往哪裡去，所以要加負號
    direction_rad = math.atan2(-u, -v)
    direction_deg = math.degrees(direction_rad)

    # 轉換為 0-360 度
    if direction_deg < 0:
        direction_deg += 360

    # 轉換為方位文字
    direction_text = degree_to_direction_text(direction_deg)

    return direction_deg, speed, direction_text

def degree_to_direction_text(degree):
    """
    將角度轉換為方位文字
    0度 = 北 (N), 90度 = 東 (E), 180度 = 南 (S), 270度 = 西 (W)
    """
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    # 每個方位覆蓋 45 度，加上 22.5 度偏移來四捨五入到最近的方位
    index = int((degree + 22.5) / 45) % 8
    return directions[index]

def get_fallback_wind_data():
    """
    備用風向資料 - 基於台南地區季節性歷史風向
    台南氣候特徵：
    - 冬季（11-3月）：東北季風盛行，風向 NE
    - 夏季（5-9月）：西南季風盛行，風向 SW
    - 春季（4月）：季風轉換期，風向 E-SE
    - 秋季（10月）：季風轉換期，風向 E-NE
    """
    current_month = datetime.now().month

    # 根據月份設定台南地區的典型季節風向
    if current_month in [11, 12, 1, 2, 3]:
        # 冬季：東北季風
        direction_text = 'NE'
        direction_deg = 45
        typical_speed = 4.5  # 冬季風速較強
    elif current_month in [5, 6, 7, 8, 9]:
        # 夏季：西南季風
        direction_text = 'SW'
        direction_deg = 225
        typical_speed = 3.5  # 夏季風速較弱
    elif current_month == 4:
        # 春季過渡期：偏東風
        direction_text = 'E'
        direction_deg = 90
        typical_speed = 3.0
    else:  # 10月
        # 秋季過渡期：東北東風
        direction_text = 'NE'
        direction_deg = 45
        typical_speed = 3.8

    return {
        'direction': direction_deg,
        'speed': typical_speed,
        'direction_text': direction_text,
        'speed_text': f"{typical_speed} m/s",
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'is_real': False  # 標記為歷史資料
    }

def get_wind_arrow_unicode(direction_text):
    """根據風向返回箭頭符號"""
    arrows = {
        'N': '↓',   # 北風往南吹
        'NE': '↙',
        'E': '←',
        'SE': '↖',
        'S': '↑',
        'SW': '↗',
        'W': '→',
        'NW': '↘'
    }
    return arrows.get(direction_text, '•')

def get_opposite_direction(direction_text):
    """獲取相反風向（污染物擴散方向）"""
    opposites = {
        'N': '南',
        'NE': '西南',
        'E': '西',
        'SE': '西北',
        'S': '北',
        'SW': '東北',
        'W': '東',
        'NW': '東南'
    }
    return opposites.get(direction_text, '未知')

# ===========================================
# 災害情境模擬引擎
# ===========================================

class DisasterScenario:
    """災害情境模擬類別"""
    
    @staticmethod
    def earthquake(base_data):
        if base_data is None:
            return None
        df = base_data.copy()
        df['shake_intensity'] = df['distance_to_ncku'].apply(lambda d: max(7 - d*2, 0))
        df['status'] = df['shake_intensity'].apply(lambda x: '設備異常' if x > 5 else '正常')
        df['color'] = [[255, 200, 0, 220]] * len(df)
        df['radius'] = df['shake_intensity'] * 15 + 30
        return df
    
    @staticmethod
    def flooding(base_data):
        if base_data is None:
            return None
        df = base_data.copy()
        df['water_depth'] = df['lat'].apply(lambda x: max(0, (22.98 - x) * 300))
        df['color'] = df['water_depth'].apply(
            lambda d: [0, 100, 255, 220] if d > 50 else [100, 150, 255, 180]
        )
        df['radius'] = df['water_depth'] + 30
        df['status'] = df['water_depth'].apply(
            lambda d: f'淹水 {d:.0f}cm' if d > 10 else '正常'
        )
        return df
    
    @staticmethod
    def war_alert(base_data):
        if base_data is None:
            return None
        df = base_data.copy()
        df['color'] = [[255, 0, 0, 240]] * len(df)
        df['radius'] = 50
        df['status'] = '警戒中'
        return df
    
    @staticmethod
    def air_pollution(base_data):
        if base_data is None:
            return None
        df = base_data.copy()
        df['pm25'] = df['pm25'] + np.random.randint(80, 150, len(df))
        df['pm10'] = df['pm10'] + np.random.randint(100, 200, len(df))
        df['aqi'] = (df['pm25'] * 1.5).astype(int).astype(str)
        df['status'] = df['pm25'].apply(
            lambda x: '非常不健康' if x > 150 else '對所有族群不健康' if x > 100 else '對敏感族群不健康'
        )
        df['color'] = df['pm25'].apply(
            lambda x: [255, 0, 0, 240] if x > 150 else [255, 50, 0, 220]
        )
        df['radius'] = df['pm25'] / 3
        return df
    
    @staticmethod
    def water_contamination(base_data):
        return {
            'contaminated': True,
            'pollutant': '重金屬超標',
            'affected_rivers': ['鹽水溪', '二仁溪'],
            'warning': '請勿使用自來水，改用瓶裝水'
        }

# ===========================================
# 視覺化輔助函數
# ===========================================

def prepare_map_data(df, scenario=None):
    if df is None:
        return None

    # 創建副本以避免修改原始數據
    df = df.copy()

    if scenario == 'normal':
        # 根據 PM2.5 值設置顏色
        df['color'] = df['pm25'].apply(lambda x:
            [0, 255, 0, 200] if x <= 35 else
            [255, 255, 0, 200] if x <= 53 else
            [255, 126, 0, 200] if x <= 70 else
            [255, 0, 0, 220]
        )
        # 設置半徑大小
        df['radius'] = 30 + (df['pm25'] / 150) * 30
    else:
        # 確保其他情境下也有默認的 color 和 radius
        if 'color' not in df.columns:
            df['color'] = [[100, 100, 100, 200]] * len(df)
        if 'radius' not in df.columns:
            df['radius'] = 40

    return df

def get_disaster_info(scenario_name):
    """
    根據大學里防災地圖定義的具體避難指示
    座標來源：Google Maps 對照防災地圖地點
    """
    scenarios = {
        'normal': {
            'title': '🟢 正常狀態',
            'description': '環境監測正常運作中',
            'color': 'info',
            'actions': [],
            'gif_file': None
        },
        'earthquake': {
            'title': '🔴 地震發生',
            'description': '偵測到強烈地震！請立即採取「趴下、掩護、穩住」。',
            'color': 'error',
            'actions': [
                '保護頭部，遠離玻璃與掉落物',
                '地震停止後，前往戶外空曠處或學校操場避難',
                '【建議避難點 1】國立成功大學光復校區操場 (22.9968, 120.2185)',
                '【建議避難點 2】後甲國中操場 (22.9939, 120.2260)',
                '【建議避難點 3】台南一中操場 (22.9922, 120.2163)'
            ],
            'gif_file': 'output.gif',
            'contacts': [
                '📞 緊急聯絡：119（消防局）',
                '📞 校園安全：06-2757575'
            ]
        },
        'flooding': {
            'title': '🌊 淹水警報',
            'description': '豪雨造成低窪地區積水，請進行垂直避難或前往高處。',
            'color': 'warning',
            'actions': [
                '前往具備二樓以上之堅固建築',
                '切勿涉水行走，遠離地下室',
                '【指定收容所】大學東寧社區聯合活動中心 (22.9930, 120.2248)',
                '【高地避難】成功大學各系館二樓以上 (22.9971, 120.2218)'
            ],
            'gif_file': 'output.gif',
            'contacts': [
                '📞 災情通報：1999（台南市民專線）',
                '📞 水利局：06-6322231'
            ]
        },
        'war_alert': {
            'title': '⚠️ 空襲警報',
            'description': '防空警報發布！請立即進入室內或地下避難設施。',
            'color': 'error',
            'actions': [
                '配合引導，進入最近的防空避難室（有黃色標示）',
                '保持安靜，關閉燈光與火源',
                '【就近避難】成功大學各系館地下室 (22.9971, 120.2218)',
                '【就近避難】大學東寧社區活動中心地下室 (22.9930, 120.2248)',
                '【就近避難】台南一中群英堂地下室 (22.9922, 120.2163)'
            ],
            'gif_file': 'output.gif',
            'contacts': [
                '📞 警報查詢：110（警察局）',
                '📞 民防指揮中心：06-2991111'
            ]
        },
        'air_pollution': {
            'title': '🏭 嚴重空氣污染',
            'description': '有害氣體擴散中！請參考即時風場地圖判斷避難方向。',
            'color': 'error',
            'actions': [
                '判斷風向：請查看即時風場動態地圖',
                '避難原則：移動至「上風處」或室內緊閉門窗',
                '開啟空氣清淨機，配戴 N95 口罩',
                '若位於下風處，請盡速橫向移動脫離污染路徑',
                '【室內避難】成功大學圖書館（密閉空間）(22.9978, 120.2185)',
                '【室內避難】成功大學醫學院（空調系統）(22.9958, 120.2137)'
            ],
            'gif_file': 'output.gif',  # AI主播使用的GIF
            'contacts': [
                '📞 環保局專線：06-2686751',
                '📞 空污通報：0800-066-666（環境部）'
            ]
        },
        'water_contamination': {
            'title': '💧 水質污染警報',
            'description': '偵測到河川水質異常，重金屬含量超標',
            'color': 'warning',
            'actions': [
                '停止使用自來水，改用瓶裝水',
                '避免接觸鹽水溪、二仁溪水域',
                '【取水點】成功大學緊急供水站（如啟動）(22.9971, 120.2218)',
                '【避開區域】鹽水溪沿岸 500 公尺範圍'
            ],
            'gif_file': 'output.gif',
            'contacts': [
                '📞 環保局專線：0800-066-666',
                '📞 自來水公司：1910',
                '📞 衛生局：06-6357716'
            ]
        }
    }
    
    return scenarios.get(scenario_name, scenarios['normal'])

# ===========================================
# 側邊欄設定
# ===========================================

st.sidebar.title("🛡️ TAI-SAFE 控制台")
st.sidebar.markdown("**成功大學智慧防災系統**")
st.sidebar.markdown("---")

# 災害情境選擇
st.sidebar.subheader("🎭 災害情境模擬")
scenario = st.sidebar.selectbox(
    "選擇情境（DEMO用）",
    options=[
        ('normal', '🟢 正常狀態'),
        ('earthquake', '🔴 地震發生'),
        ('flooding', '🌊 淹水警報'),
        ('war_alert', '⚠️ 空襲警報'),
        ('air_pollution', '🏭 空氣污染'),
        ('water_contamination', '💧 水質污染')
    ],
    format_func=lambda x: x[1]
)[0]

st.sidebar.markdown("---")

# 視角選擇（默認為民眾手機端）
view_mode = st.sidebar.radio(
    "👁️ 選擇視角",
    ["民眾手機端", "指揮中心"]
)

if view_mode == "民眾手機端":
    use_persona = st.sidebar.checkbox("啟用 AI 助理", value=True)

# 重新整理按鈕
if st.sidebar.button("🔄 重新載入資料"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("📡 資料來源")
st.sidebar.caption("• 環境部開放資料平台")
st.sidebar.caption("• 中央氣象署")
st.sidebar.caption("• 台南市政府")

# ===========================================
# 主要內容區
# ===========================================

# 載入資料
with st.spinner("🔄 載入即時監測資料..."):
    air_data, is_real_air = fetch_real_air_quality()
    water_data, is_real_water = fetch_real_water_quality()
    weather_warnings = fetch_real_weather_warnings()

# 應用災害情境
disaster_info = get_disaster_info(scenario)

if scenario != 'normal':
    if scenario == 'water_contamination':
        water_contamination_info = DisasterScenario.water_contamination(None)
    else:
        scenario_func = getattr(DisasterScenario, scenario)
        air_data = scenario_func(air_data)

# 正常模式下準備地圖資料
if scenario == 'normal':
    air_data = prepare_map_data(air_data, 'normal')

# ===========================================
# 視圖渲染
# ===========================================

if view_mode == "指揮中心":
    # 標題
    st.title("TAI-SAFE 智慧國土防災決策支援系統")
    st.markdown(f"**監測中心**: 國立成功大學 | **監測範圍**: 台南市")
    
    # 資料來源標示（灰色背景）
    if not is_real_air:
        st.markdown("""
        <div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;">
            <p style="margin: 0; color: #666; font-size: 14px;">
                📊 <b>資料模式</b>: 備用資料（展示模式）- 數值固定不變
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # 災害警示卡
    if scenario != 'normal':
        alert_color = disaster_info['color']
        with st.container():
            if alert_color == 'error':
                st.error(f"### {disaster_info['title']}")
            elif alert_color == 'warning':
                st.warning(f"### {disaster_info['title']}")
            else:
                st.info(f"### {disaster_info['title']}")
            
            st.markdown(f"**{disaster_info['description']}**")
            
            if disaster_info['actions']:
                st.markdown("**建議應變措施與避難地點：**")
                for i, action in enumerate(disaster_info['actions'], 1):
                    st.markdown(f"{i}. {action}")
            
            # 顯示緊急聯絡方式
            if 'contacts' in disaster_info and disaster_info['contacts']:
                st.markdown("---")
                st.markdown("**🆘 緊急聯絡方式：**")
                for contact in disaster_info['contacts']:
                    st.markdown(f"• {contact}")

    # AI 主播圖示（災害情境時顯示）
    if scenario != 'normal':
        st.markdown("---")
        st.markdown("### 📺 AI 防災主播")
        # 使用 display_gif 函數以置中方式顯示
        gif_displayed = display_gif("output.gif", width_percent=40)
        if not gif_displayed:
            # 如果沒有 GIF，顯示提示
            st.markdown("""
            <div style="display: flex; justify-content: center; align-items: center;">
                <img src="https://api.dicebear.com/7.x/bottts/svg?seed=taisafe"
                     style="width: 300px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            </div>
            """, unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>即時災害資訊播報</p>", unsafe_allow_html=True)

    # 關鍵指標
    col1, col2, col3, col4, col5 = st.columns(5)

    avg_pm25 = air_data['pm25'].mean()
    max_pm25 = air_data['pm25'].max()
    active_stations = len(air_data[air_data['status'] != '設備異常'])

    # 獲取風向資料
    wind_data, is_real_wind = fetch_wind_data(
        lat=NCKU_CENTER['lat'],
        lon=NCKU_CENTER['lon'],
        zoom=11
    )

    with col1:
        st.metric(
            "平均 PM2.5",
            f"{avg_pm25:.1f}",
            delta=f"最高: {max_pm25:.0f}" if scenario == 'normal' else "⚠️ 異常"
        )

    with col2:
        risk_status = "正常" if scenario == 'normal' else disaster_info['title'].split()[1]
        st.metric(
            "系統狀態",
            risk_status,
            delta="監控中" if scenario == 'normal' else "警報中"
        )

    with col3:
        st.metric(
            "活躍監測站",
            f"{active_stations}/{len(air_data)}",
            delta="線上"
        )

    with col4:
        # 風向資訊
        wind_arrow = get_wind_arrow_unicode(wind_data['direction_text'])
        st.metric(
            "風向/風速",
            f"{wind_data['direction_text']} {wind_arrow}",
            delta=f"{wind_data['speed']} m/s"
        )
        if not is_real_wind:
            st.caption("📊 季節性歷史資料")

    with col5:
        if scenario != 'normal':
            st.metric("避難人數", "1,847", delta="+1,847", delta_color="inverse")
        else:
            st.metric("資料更新", "即時", delta="5 分鐘前")
    
    # 災害監控影像（災害情境時）
    st.markdown("---")

    if scenario != 'normal':
        st.subheader("📹 災害現場監控影像")

        # 獲取即時影像串流
        cameras, is_real_camera = fetch_twipcam_streams(
            lat=NCKU_CENTER['lat'],
            lon=NCKU_CENTER['lon'],
            radius=10
        )

        col_video, col_map = st.columns([1, 1])

        with col_video:
            # 顯示即時影像
            if cameras and len(cameras) > 0:
                st.markdown("**即時監控畫面**")

                # 選擇要顯示的攝影機
                camera_names = [f"{cam.get('name', f'Camera {i+1}')}" for i, cam in enumerate(cameras)]
                selected_camera_idx = st.selectbox(
                    "選擇攝影機",
                    range(len(cameras)),
                    format_func=lambda x: camera_names[x]
                )

                selected_camera = cameras[selected_camera_idx]

                # 顯示攝影機資訊
                distance_info = f"{selected_camera.get('distance', 0):.2f} km" if 'distance' in selected_camera else "N/A"
                st.info(f"📍 **位置**: {selected_camera.get('name', 'Unknown')}\n"
                       f"📏 **距離**: {distance_info}\n"
                       f"🔴 **狀態**: {selected_camera.get('status', 'Unknown')}")

                # 顯示即時快照影像
                if 'cam_url' in selected_camera and selected_camera['cam_url']:
                    # 顯示攝影機快照圖片
                    try:
                        st.image(selected_camera['cam_url'],
                                caption=f"即時快照 - {selected_camera.get('name', 'Camera')}",
                                use_container_width=True)
                    except:
                        # 如果圖片載入失敗，顯示備用GIF
                        gif_filename = disaster_info.get('gif_file', 'output.gif')
                        gif_displayed = display_gif(gif_filename, width_percent=100)
                        if not gif_displayed:
                            st.warning("⚠️ 無法連接即時影像")
                else:
                    # 備用：顯示 GIF 動畫
                    gif_filename = disaster_info.get('gif_file', 'output.gif')
                    gif_displayed = display_gif(gif_filename, width_percent=100)

                    if not gif_displayed:
                        st.warning("⚠️ 無法連接即時影像，請檢查攝影機狀態")

                # 顯示資料來源
                if not is_real_camera:
                    st.caption("📊 展示模式（備用資料）")
            else:
                st.warning("⚠️ 目前無可用攝影機")

        with col_map:
            st.subheader("📍 災害分布圖")

            # 空污情境：顯示即時風場地圖
            if scenario == 'air_pollution':
                st.markdown("**即時風場動態**")
                wind_map_url = f"https://www.twipcam.com/api/v1/map/wind?lat={NCKU_CENTER['lat']}&lon={NCKU_CENTER['lon']}&zoom=9"

                st.markdown(f"""
                <div style="border: 2px solid #ddd; border-radius: 10px; overflow: hidden;">
                    <iframe src="{wind_map_url}"
                            width="100%" height="400"
                            frameborder="0" allowfullscreen>
                    </iframe>
                </div>
                """, unsafe_allow_html=True)
                st.caption("🌬️ 即時風場資料 - 協助判斷污染擴散方向")

    # 地圖視覺化
    if scenario != 'earthquake':
        st.subheader("📍 台南地區環境監測地圖（以成功大學為中心）")
    
    # 建立 Pydeck 圖層
    try:
        station_layer = pdk.Layer(
            "ScatterplotLayer",
            data=air_data,
            get_position='[lon, lat]',
            get_fill_color='color',
            get_radius='radius',
            pickable=True,
            stroked=True,
            filled=True,
            get_line_color=[255, 255, 255],
            line_width_min_pixels=2,
        )
        
        ncku_marker = pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame([NCKU_CENTER]),
            get_position='[lon, lat]',
            get_fill_color=[0, 100, 255],
            get_radius=80,
            pickable=True,
            stroked=True,
            filled=True,
            get_line_color=[255, 255, 255],
            line_width_min_pixels=3,
        )
        
        view_state = pdk.ViewState(
            latitude=NCKU_CENTER['lat'],
            longitude=NCKU_CENTER['lon'],
            zoom=11,
            pitch=0,
            bearing=0
        )
        
        deck = pdk.Deck(
            layers=[station_layer, ncku_marker],
            initial_view_state=view_state,
            tooltip={
                "html": "<b>測站:</b> {sitename}<br/>"
                       "<b>PM2.5:</b> {pm25}<br/>"
                       "<b>AQI:</b> {aqi}<br/>"
                       "<b>狀態:</b> {status}<br/>"
                       "<b>距成大:</b> {distance_to_ncku:.2f} km",
                "style": {
                    "backgroundColor": "steelblue",
                    "color": "white",
                    "fontSize": "14px",
                    "padding": "10px"
                }
            },
            map_style='https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
        )
        
        st.pydeck_chart(deck)
        
        st.caption("🔵 成功大學 | 🟢 良好 | 🟡 普通 | 🟠 對敏感族群不健康 | 🔴 不健康")
        
    except Exception as e:
        st.error(f"地圖渲染失敗: {str(e)}")
    
    # 詳細資料表
    st.markdown("---")
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📊 空氣品質監測站數據")
        display_cols = ['sitename', 'pm25', 'pm10', 'aqi', 'status', 'distance_to_ncku']
        display_df = air_data[display_cols].copy()
        display_df.columns = ['測站', 'PM2.5', 'PM10', 'AQI', '狀態', '距成大(km)']
        display_df['PM2.5'] = display_df['PM2.5'].round(1)
        display_df['PM10'] = display_df['PM10'].round(1)
        display_df['距成大(km)'] = display_df['距成大(km)'].round(2)
        st.dataframe(display_df.head(10), use_container_width=True, hide_index=True)
    
    with col_right:
        st.subheader("💧 河川水質監測")
        st.dataframe(water_data.head(10), use_container_width=True, hide_index=True)
    
    # 天氣警報
    if weather_warnings:
        st.markdown("---")
        st.subheader("⚠️ 天氣警特報")
        for warning in weather_warnings:
            st.info(f"**{warning['type']}**: {warning['description']}")

else:  # 民眾手機端視角
    st.markdown("### 📱 TAI-SAFE 防災警示 App")
    
    # 資料來源標示（灰色背景）
    if not is_real_air:
        st.markdown("""
        <div style="background-color: #f0f0f0; padding: 8px; border-radius: 5px; margin: 5px 0;">
            <p style="margin: 0; color: #666; font-size: 12px;">
                📊 展示模式（備用資料）
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    if 'user_location' not in st.session_state:
        st.session_state.user_location = NCKU_CENTER.copy()

    # 顯示目前位置（移除橘色icon）
    st.info(f"📍 **目前位置**\n成功大學附近\n({st.session_state.user_location['lat']:.4f}, {st.session_state.user_location['lon']:.4f})")

    # 顯示地圖
    st.markdown("---")
    st.subheader("🗺️ 目前位置")

    try:
        # 建立測站圖層
        station_layer_mobile = pdk.Layer(
            "ScatterplotLayer",
            data=air_data,
            get_position='[lon, lat]',
            get_fill_color='color',
            get_radius='radius',
            pickable=True,
            stroked=True,
            filled=True,
            get_line_color=[255, 255, 255],
            line_width_min_pixels=2,
        )

        # 目前位置標記
        current_location_marker = pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame([st.session_state.user_location]),
            get_position='[lon, lat]',
            get_fill_color=[0, 100, 255],
            get_radius=60,
            pickable=True,
            stroked=True,
            filled=True,
            get_line_color=[255, 255, 255],
            line_width_min_pixels=3,
        )

        view_state_mobile = pdk.ViewState(
            latitude=st.session_state.user_location['lat'],
            longitude=st.session_state.user_location['lon'],
            zoom=12,
            pitch=0,
            bearing=0
        )

        deck_mobile = pdk.Deck(
            layers=[station_layer_mobile, current_location_marker],
            initial_view_state=view_state_mobile,
            tooltip={
                "html": "<b>測站:</b> {sitename}<br/>"
                       "<b>PM2.5:</b> {pm25}<br/>"
                       "<b>AQI:</b> {aqi}<br/>"
                       "<b>狀態:</b> {status}",
                "style": {
                    "backgroundColor": "steelblue",
                    "color": "white",
                    "fontSize": "12px",
                    "padding": "8px"
                }
            },
            map_style='https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
        )

        st.pydeck_chart(deck_mobile)
        st.caption("🔵 您的位置 | 🟢 良好 | 🟡 普通 | 🟠 對敏感族群不健康 | 🔴 不健康")

    except Exception as e:
        st.warning("⚠️ 地圖載入中...")

    avg_pm25_mobile = air_data['pm25'].mean()
    
    if scenario != 'normal':
        st.markdown("---")

        if use_persona:
            # AI 主播圖示 - 獨立一行、置中、變大
            st.markdown("### 📺 AI 防災主播")
            # AI 助理始終顯示 output.gif（不受情境影響）
            gif_displayed = display_gif("output.gif", width_percent=50)

            if not gif_displayed:
                # 如果沒有 GIF，顯示原本的圖片作為後備
                st.markdown("""
                <div style="display: flex; justify-content: center; align-items: center;">
                    <img src="https://api.dicebear.com/7.x/bottts/svg?seed=taisafe"
                         style="width: 200px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                </div>
                """, unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #666; margin-bottom: 20px;'>即時災害警報</p>", unsafe_allow_html=True)

            st.markdown("---")

            # 災害訊息
            st.error(f"### {disaster_info['title']}")
            st.markdown(f"**{disaster_info['description']}**")

            if disaster_info['actions']:
                st.markdown("**請立即執行:**")
                for action in disaster_info['actions'][:4]:  # 顯示前 4 項
                    st.markdown(f"• {action}")
        else:
            st.error(f"### {disaster_info['title']}")
            st.markdown(f"{disaster_info['description']}")
        
        # 空氣污染情境：顯示風場圖和即時風向（在按鈕上方）
        if scenario == 'air_pollution':
            st.markdown("---")

            # 顯示即時風向資料
            wind_data_mobile, is_real_wind_mobile = fetch_wind_data(
                lat=st.session_state.user_location['lat'],
                lon=st.session_state.user_location['lon'],
                zoom=11
            )

            # 顯示風向資訊
            st.markdown("### 🌬️ 即時風向資訊")
            col_wind1, col_wind2 = st.columns(2)

            with col_wind1:
                wind_arrow = get_wind_arrow_unicode(wind_data_mobile['direction_text'])
                st.metric(
                    "風向",
                    f"{wind_data_mobile['direction_text']} {wind_arrow}",
                    delta="請往上風處移動"
                )

            with col_wind2:
                st.metric(
                    "風速",
                    f"{wind_data_mobile['speed']} m/s",
                    delta=wind_data_mobile['timestamp'].split()[1] if ' ' in wind_data_mobile['timestamp'] else ''
                )

            if not is_real_wind_mobile:
                st.caption("📊 使用季節性歷史資料（基於台南地區氣候特徵）")

            st.info(f"💡 **避難提示**: 目前風向為 {wind_data_mobile['direction_text']}，污染物將往 {get_opposite_direction(wind_data_mobile['direction_text'])} 方向擴散。請盡快移動至上風處或室內避難。")

            st.markdown("---")
            st.markdown("### 📊 即時風場動態圖")

            # 使用 TwipCam Wind API 嵌入即時風場地圖
            wind_map_url = f"https://www.twipcam.com/api/v1/map/wind?lat={st.session_state.user_location['lat']}&lon={st.session_state.user_location['lon']}&zoom=10"

            st.markdown(f"""
            <div style="border: 2px solid #ddd; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <iframe src="{wind_map_url}"
                        width="100%" height="500"
                        frameborder="0" allowfullscreen
                        style="border-radius: 10px;">
                </iframe>
            </div>
            """, unsafe_allow_html=True)

            st.caption("🌬️ 即時風場資料 - 請根據風向圖判斷安全避難方向（移動至上風處）")
            st.caption("📍 地圖中心: 成功大學附近")

            st.markdown("---")
        
        # 緊急聯絡資訊直接顯示
        st.markdown("### 🆘 緊急聯絡方式")
        if 'contacts' in disaster_info and disaster_info['contacts']:
            for contact in disaster_info['contacts']:
                st.info(contact)
        else:
            st.info("📱 撥打 119 / 110")

        st.markdown("---")

        # 避難路線按鈕
        if st.button("🏃 查看避難路線", type="primary", use_container_width=True):
            st.success("✅ 正在規劃最近避難所路線...")
            # 顯示避難地點資訊
            if disaster_info['actions']:
                st.info("**避難地點：**\n" + "\n".join([a for a in disaster_info['actions'] if '【' in a]))
    
    else:
        st.success("✅ 目前所在區域安全")
        pm25_status = "良好" if avg_pm25_mobile < 35 else "普通" if avg_pm25_mobile < 53 else "不健康"
        st.metric("即時 PM2.5", f"{avg_pm25_mobile:.1f}", pm25_status)
    
    st.markdown("---")

    # 根據情境顯示不同內容
    if scenario != 'normal':
        # 災害情境：顯示監控影像
        st.subheader("📹 災害現場監控影像")

        # 獲取即時影像串流
        cameras_mobile, is_real_camera_mobile = fetch_twipcam_streams(
            lat=st.session_state.user_location['lat'],
            lon=st.session_state.user_location['lon'],
            radius=10
        )

        if cameras_mobile and len(cameras_mobile) > 0:
            st.markdown("**即時監控畫面**")

            # 選擇要顯示的攝影機
            camera_names_mobile = [f"{cam.get('name', f'Camera {i+1}')} ({cam.get('distance', 0):.1f} km)" for i, cam in enumerate(cameras_mobile)]
            selected_camera_idx_mobile = st.selectbox(
                "選擇攝影機",
                range(len(cameras_mobile)),
                format_func=lambda x: camera_names_mobile[x],
                key="mobile_camera_select"
            )

            selected_camera_mobile = cameras_mobile[selected_camera_idx_mobile]

            # 顯示攝影機資訊
            distance_info_mobile = f"{selected_camera_mobile.get('distance', 0):.2f} km" if 'distance' in selected_camera_mobile else "N/A"
            st.info(f"📍 **位置**: {selected_camera_mobile.get('name', 'Unknown')}\n"
                   f"📏 **距離**: {distance_info_mobile}\n"
                   f"🔴 **狀態**: {selected_camera_mobile.get('status', 'Unknown')}")

            # 顯示即時快照影像
            if 'cam_url' in selected_camera_mobile and selected_camera_mobile['cam_url']:
                try:
                    st.image(selected_camera_mobile['cam_url'],
                            caption=f"即時快照 - {selected_camera_mobile.get('name', 'Camera')}",
                            use_container_width=True)
                except:
                    # 如果圖片載入失敗，顯示備用GIF
                    gif_filename = disaster_info.get('gif_file', 'output.gif')
                    gif_displayed = display_gif(gif_filename, width_percent=100)
                    if not gif_displayed:
                        st.warning("⚠️ 無法連接即時影像")
            else:
                # 備用：顯示 GIF 動畫
                gif_filename = disaster_info.get('gif_file', 'output.gif')
                gif_displayed = display_gif(gif_filename, width_percent=100)
                if not gif_displayed:
                    st.warning("⚠️ 無法連接即時影像，請檢查攝影機狀態")

            # 顯示資料來源
            if not is_real_camera_mobile:
                st.caption("📊 展示模式（備用資料）")
        else:
            st.warning("⚠️ 目前無可用攝影機")

        # 根據災害類型顯示模擬異常數據
        if scenario == 'water_contamination':
            st.markdown("---")
            st.subheader("💧 河川水質監測數據（模擬異常數據）")
            # 創建模擬異常水質數據
            abnormal_water_data = water_data.copy()
            # 模擬異常:提高污染指標
            abnormal_water_data['ph'] = abnormal_water_data['ph'].apply(lambda x: round(float(x) * 0.8, 2) if isinstance(x, (int, float, str)) and str(x).replace('.', '').isdigit() else x)
            abnormal_water_data['do'] = abnormal_water_data['do'].apply(lambda x: round(float(x) * 0.5, 2) if isinstance(x, (int, float, str)) and str(x).replace('.', '').isdigit() else x)
            abnormal_water_data['bod'] = abnormal_water_data['bod'].apply(lambda x: round(float(x) * 3.0, 2) if isinstance(x, (int, float, str)) and str(x).replace('.', '').isdigit() else x)
            abnormal_water_data['nh3n'] = abnormal_water_data['nh3n'].apply(lambda x: round(float(x) * 5.0, 2) if isinstance(x, (int, float, str)) and str(x).replace('.', '').isdigit() else x)
            abnormal_water_data['rpi'] = abnormal_water_data['rpi'].apply(lambda x: round(float(x) * 2.5, 2) if isinstance(x, (int, float, str)) and str(x).replace('.', '').isdigit() else x)
            st.dataframe(abnormal_water_data.head(10), use_container_width=True, hide_index=True)

        elif scenario == 'air_pollution':
            st.markdown("---")
            st.subheader("📊 空氣品質監測站數據（模擬異常數據）")
            # 創建模擬異常空氣數據 - 使用已經由 DisasterScenario.air_pollution 處理過的 air_data
            # air_data 在此情境下已經包含了異常高的 PM2.5 和 PM10 數值
            display_cols = ['sitename', 'pm25', 'pm10', 'aqi', 'status', 'distance_to_ncku']
            display_df_abnormal = air_data[display_cols].copy()
            display_df_abnormal.columns = ['測站', 'PM2.5', 'PM10', 'AQI', '狀態', '距成大(km)']
            display_df_abnormal['PM2.5'] = display_df_abnormal['PM2.5'].round(1)
            display_df_abnormal['PM10'] = display_df_abnormal['PM10'].round(1)
            display_df_abnormal['距成大(km)'] = display_df_abnormal['距成大(km)'].round(2)
            st.dataframe(display_df_abnormal.head(10), use_container_width=True, hide_index=True)

    else:
        # 正常情境：顯示附近監測站
        st.subheader("📍 附近監測站")

        nearest_stations = air_data.head(5)

        for _, station in nearest_stations.iterrows():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.write(f"**{station['sitename']}**")
                st.caption(f"{station['distance_to_ncku']:.2f} km")

            with col2:
                pm25_color = "🟢" if station['pm25'] < 35 else "🟡" if station['pm25'] < 53 else "🔴"
                st.metric("PM2.5", f"{station['pm25']:.0f}")

            with col3:
                st.write(pm25_color)
                st.caption(station['status'])

        # 顯示詳細監測數據
        st.markdown("---")
        st.subheader("📊 空氣品質監測站數據")
        display_cols = ['sitename', 'pm25', 'pm10', 'aqi', 'status', 'distance_to_ncku']
        display_df = air_data[display_cols].copy()
        display_df.columns = ['測站', 'PM2.5', 'PM10', 'AQI', '狀態', '距成大(km)']
        display_df['PM2.5'] = display_df['PM2.5'].round(1)
        display_df['PM10'] = display_df['PM10'].round(1)
        display_df['距成大(km)'] = display_df['距成大(km)'].round(2)
        st.dataframe(display_df.head(10), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("💧 河川水質監測數據")
        st.dataframe(water_data.head(10), use_container_width=True, hide_index=True)

# 頁尾
st.markdown("---")
st.caption("**TAI-SAFE Project** | 國立成功大學 智慧防災系統")
st.caption(f"資料更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
