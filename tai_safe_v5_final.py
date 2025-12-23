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
        url = "https://data.moenv.gov.tw/api/v2/aqx_p_432?limit=1000&api_key=e8dd42e6-9b8b-43f8-991e-b3dee723a52d"
        response = requests.get(url, timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            records = data.get('records', [])
            
            tainan_data = []
            for record in records:
                county = record.get('county', '')
                if '台南' in county or '臺南' in county:
                    try:
                        lat = float(record.get('latitude', 0))
                        lon = float(record.get('longitude', 0))
                        
                        if lat == 0 or lon == 0:
                            continue
                        
                        distance = np.sqrt((lat - NCKU_CENTER['lat'])**2 + 
                                         (lon - NCKU_CENTER['lon'])**2) * 111
                        
                        pm25_val = record.get('pm2.5', '')
                        if pm25_val in ['', None, 'ND', '-']:
                            pm25_val = 0
                        else:
                            pm25_val = float(pm25_val)
                        
                        pm10_val = record.get('pm10', '')
                        if pm10_val in ['', None, 'ND', '-']:
                            pm10_val = 0
                        else:
                            pm10_val = float(pm10_val)
                        
                        tainan_data.append({
                            'sitename': record.get('sitename', 'Unknown'),
                            'lat': lat,
                            'lon': lon,
                            'pm25': pm25_val,
                            'pm10': pm10_val,
                            'aqi': record.get('aqi', 'N/A'),
                            'status': record.get('status', '良好'),
                            'o3': record.get('o3', '-'),
                            'co': record.get('co', '-'),
                            'so2': record.get('so2', '-'),
                            'no2': record.get('no2', '-'),
                            'publishtime': record.get('publishtime', ''),
                            'distance_to_ncku': distance
                        })
                    except:
                        continue
            
            if tainan_data:
                df = pd.DataFrame(tainan_data)
                df = df.sort_values('distance_to_ncku').reset_index(drop=True)
                return df, True
        
        return get_fallback_air_data(), False
        
    except:
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
    
    if scenario == 'normal':
        df['color'] = df['pm25'].apply(lambda x: 
            [0, 255, 0, 200] if x <= 35 else
            [255, 255, 0, 200] if x <= 53 else
            [255, 126, 0, 200] if x <= 70 else
            [255, 0, 0, 220]
        )
        df['radius'] = 30 + (df['pm25'] / 150) * 30
    
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
            'description': '有害氣體擴散中！請參考上方風向圖（GIF）進行避難。',
            'color': 'error',
            'actions': [
                '判斷風向：請查看畫面上的風場動態圖',
                '避難原則：移動至「上風處」或室內緊閉門窗',
                '開啟空氣清淨機，配戴 N95 口罩',
                '若位於下風處，請盡速橫向移動脫離污染路徑',
                '【室內避難】成功大學圖書館（密閉空間）(22.9978, 120.2185)',
                '【室內避難】成功大學醫學院（空調系統）(22.9958, 120.2137)'
            ],
            'gif_file': 'output1.gif',  # 使用專用的風場動態圖
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

# 視角選擇
view_mode = st.sidebar.radio(
    "👁️ 選擇視角",
    ["指揮中心", "民眾手機端"]
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
    
    # 關鍵指標
    col1, col2, col3, col4 = st.columns(4)
    
    avg_pm25 = air_data['pm25'].mean()
    max_pm25 = air_data['pm25'].max()
    active_stations = len(air_data[air_data['status'] != '設備異常'])
    
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
        if scenario != 'normal':
            st.metric("避難人數", "1,847", delta="+1,847", delta_color="inverse")
        else:
            st.metric("資料更新", "即時", delta="5 分鐘前")
    
    # 影片顯示（災害情境時）
    st.markdown("---")
    
    if scenario != 'normal':
        # 取得該情境的 GIF 檔案名稱
        gif_filename = disaster_info.get('gif_file', 'output.gif')
        
        st.subheader("📹 災害現場監控影像")
        col_video, col_map = st.columns([1, 1])
        
        with col_video:
            # 顯示對應情境的 GIF 動畫
            gif_displayed = display_gif(gif_filename, width_percent=100)
            
            if not gif_displayed:
                # 如果沒有 GIF，顯示提示
                st.markdown(f"""
                <div style="background-color: #ffe6e6; padding: 20px; border-radius: 10px; text-align: center;">
                    <h3>📹 現場監控</h3>
                    <p>將 GIF 檔案命名為 <code>{gif_filename}</code><br/>放在與程式相同的目錄即可顯示</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col_map:
            st.subheader("📍 災害分布圖")
    
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
            map_style='mapbox://styles/mapbox/light-v11'
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
    
    col_loc, col_info = st.columns([1, 2])
    
    with col_loc:
        st.image("https://api.dicebear.com/7.x/shapes/svg?seed=location", width=80)
    
    with col_info:
        st.info(f"📍 **目前位置**\n成功大學附近\n({st.session_state.user_location['lat']:.4f}, {st.session_state.user_location['lon']:.4f})")
    
    avg_pm25_mobile = air_data['pm25'].mean()
    
    if scenario != 'normal':
        st.markdown("---")
        
        if use_persona:
            col_avatar, col_message = st.columns([1, 4])
            with col_avatar:
                # AI 助理始終顯示 output.gif（不受情境影響）
                gif_displayed = display_gif("output.gif", width_percent=100)
                
                if not gif_displayed:
                    # 如果沒有 GIF，顯示原本的圖片作為後備
                    st.image("https://api.dicebear.com/7.x/bottts/svg?seed=taisafe", width=100)
            
            with col_message:
                st.error(f"### {disaster_info['title']}")
                st.markdown(f"**{disaster_info['description']}**")
                
                if disaster_info['actions']:
                    st.markdown("**請立即執行:**")
                    for action in disaster_info['actions'][:4]:  # 顯示前 4 項
                        st.markdown(f"• {action}")
        else:
            st.error(f"### {disaster_info['title']}")
            st.markdown(f"{disaster_info['description']}")
        
        # 空氣污染情境：顯示風場圖（在按鈕上方）
        if scenario == 'air_pollution':
            st.markdown("---")
            st.markdown("### 📊 風場動態參考圖")
            
            gif_displayed = display_gif("output1.gif", width_percent=80)
            
            if not gif_displayed:
                st.info("💡 請將風場動態圖命名為 `output1.gif` 並放在專案目錄")
            else:
                st.caption("⬆️ 請根據風向圖判斷安全避難方向（移動至上風處）")
            
            st.markdown("---")
        
        # 緊急聯絡按鈕
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🏃 查看避難路線", type="primary", use_container_width=True):
                st.success("✅ 正在規劃最近避難所路線...")
                # 顯示避難地點資訊
                if disaster_info['actions']:
                    st.info("**避難地點：**\n" + "\n".join([a for a in disaster_info['actions'] if '【' in a]))
        with col_b:
            if st.button("📞 緊急聯絡", use_container_width=True):
                # 顯示該情境的緊急聯絡方式
                if 'contacts' in disaster_info and disaster_info['contacts']:
                    for contact in disaster_info['contacts']:
                        st.info(contact)
                else:
                    st.info("📱 撥打 119 / 110")
    
    else:
        st.success("✅ 目前所在區域安全")
        pm25_status = "良好" if avg_pm25_mobile < 35 else "普通" if avg_pm25_mobile < 53 else "不健康"
        st.metric("即時 PM2.5", f"{avg_pm25_mobile:.1f}", pm25_status)
    
    st.markdown("---")
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

# 頁尾
st.markdown("---")
st.caption("**TAI-SAFE Project** | 國立成功大學 智慧防災系統")
st.caption(f"資料更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
