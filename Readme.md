# TAI-SAFE V5 Final - UI 優化 + 影片支援版

## ✨ 新功能

### 1. ✅ 移除干擾性警告訊息
**改進前**:
```
⚠️ 網路連線問題，使用備用資料
ℹ️ 備用資料為固定數值，不會隨時間變化（僅供展示）
ℹ️ 水質資料暫時無法取得，使用備用資料
```
↓
**改進後**: 完全移除，改用優雅的灰色背景標示

### 2. ✅ 灰色背景標示備用資料

#### 指揮中心模式
```
┌────────────────────────────────────────┐
│ 📊 資料模式: 備用資料（展示模式）      │
│    數值固定不變                        │
└────────────────────────────────────────┘
```
- 背景色: 淺灰色 (#f0f0f0)
- 文字色: 深灰色 (#666)
- 清楚但不干擾

#### 民眾手機端模式
```
┌───────────────────────┐
│ 📊 展示模式（備用資料）│
└───────────────────────┘
```
- 更簡潔的版本
- 不影響主要內容

### 3. ✅ 影片播放支援（只顯示左側）

#### 功能說明
- 在**地震情境**時自動顯示災害監控影片
- 使用 HTML5 video 標籤
- CSS 裁切只顯示影片左半部
- 自動循環播放、靜音

#### 使用方法
```bash
# 1. 將影片檔案重新命名
mv your_video.mp4 disaster_video.mp4

# 2. 放在與程式相同的目錄
project/
├── tai_safe_v5_final.py
└── disaster_video.mp4  ← 這裡

# 3. 執行程式
streamlit run tai_safe_v5_final.py

# 4. 選擇「地震發生」情境
# 影片會自動顯示在左側欄位
```

#### 技術實作
```python
# 影片裁切 CSS
<div style="width: 50%; overflow: hidden;">
    <video style="width: 200%; margin-left: 0;">
        <!-- 這會只顯示左半部 -->
    </video>
</div>
```

**裁切說明**:
```
原始影片 (100%)
├─────────┼─────────┤
│  左半部  │  右半部  │  
│ (顯示)  │ (隱藏)  │
└─────────┴─────────┘

顯示效果
├─────────┤
│  左半部  │
└─────────┘
```

#### 如果沒有影片檔案
程式會顯示替代內容：
```
┌─────────────────────────┐
│   📹 現場監控            │
│                         │
│ 將影片檔案命名為        │
│ disaster_video.mp4      │
│ 放在與程式相同的目錄    │
│ 即可顯示                │
└─────────────────────────┘
```

---

## 🎨 UI 對比

### 改進前 vs 改進後

#### 情境 1: 使用備用資料時

**改進前** ❌:
```
⚠️ 網路連線問題，使用備用資料
ℹ️ 備用資料為固定數值，不會隨時間變化（僅供展示）
✅ 成功載入真實水質資料
ℹ️ 水質資料暫時無法取得，使用備用資料

TAI-SAFE 智慧國土防災決策支援系統
...
```

**改進後** ✅:
```
TAI-SAFE 智慧國土防災決策支援系統
監測中心: 國立成功大學 | 監測範圍: 台南市

╔════════════════════════════════════╗
║ 📊 資料模式: 備用資料（展示模式） ║
║    數值固定不變                    ║
╚════════════════════════════════════╝

[儀表板內容...]
```

#### 情境 2: 地震發生時

**改進前** ❌:
```
🔴 地震發生
[地圖]
```

**改進後** ✅:
```
🔴 地震發生

📹 災害現場監控影像          📍 地震震度分布圖
┌──────────────────┐    ┌──────────────────┐
│                  │    │                  │
│  [影片左半部]    │    │    [地圖]        │
│                  │    │                  │
└──────────────────┘    └──────────────────┘
```

---

## 🚀 快速使用

### 安裝
```bash
pip install streamlit pandas numpy pydeck requests urllib3
```

### 執行（無影片）
```bash
streamlit run tai_safe_v5_final.py
```
- ✅ 所有功能正常
- ⚠️ 地震情境會顯示提示訊息

### 執行（有影片）
```bash
# 1. 準備影片
cp your_disaster_video.mp4 disaster_video.mp4

# 2. 確認檔案位置
ls -la
# 應該看到:
# tai_safe_v5_final.py
# disaster_video.mp4

# 3. 執行
streamlit run tai_safe_v5_final.py

# 4. 選擇「地震發生」情境
# 影片會在左側顯示
```

---

## 📹 影片處理詳細說明

### 支援的影片格式
- ✅ MP4 (H.264)
- ✅ WebM
- ⚠️ 建議使用 MP4 (相容性最佳)

### 影片大小建議
- 檔案大小: < 50MB (載入較快)
- 解析度: 1280x720 或 1920x1080
- 位元率: 2-5 Mbps

### 影片轉換（如果需要）
```bash
# 使用 ffmpeg 轉換影片
ffmpeg -i input.mov -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k disaster_video.mp4

# 參數說明:
# -crf 23: 品質設定 (18-28, 數字越小品質越好)
# -preset medium: 編碼速度
# -c:a aac: 音訊編碼
```

### 影片裁切選項

#### 顯示左側（預設）
```python
display_cropped_video("disaster_video.mp4", crop_side='left')
```

#### 顯示右側
```python
display_cropped_video("disaster_video.mp4", crop_side='right')
```

### 自訂裁切位置
如需更精細控制，可修改程式碼：
```python
# 顯示左側 30%
<video style="width: 333%; margin-left: 0;">

# 顯示中間 50%
<video style="width: 200%; margin-left: -50%;">

# 顯示右側 30%
<video style="width: 333%; margin-left: -233%;">
```

---

## 🎯 功能測試清單

### ✅ 基本功能
- [ ] 程式正常啟動
- [ ] 地圖正常顯示
- [ ] 資料表正常顯示
- [ ] 災害情境切換正常

### ✅ UI 改進
- [ ] 備用資料時顯示灰色背景（不顯示警告）
- [ ] 真實資料時無任何提示（乾淨）
- [ ] 手機端也有灰色背景標示

### ✅ 影片功能
- [ ] 地震情境自動顯示影片區塊
- [ ] 有影片時正常播放左半部
- [ ] 無影片時顯示提示訊息
- [ ] 影片自動循環、靜音

---

## 📊 版本比較

| 功能 | V4 Fixed | V5 Final |
|------|----------|----------|
| SSL 錯誤處理 | ✅ | ✅ |
| 自動降級 | ✅ | ✅ |
| 警告訊息 | ⚠️ 多條 | ✅ 移除 |
| 資料來源標示 | 文字 | ✅ 灰色背景 |
| 影片支援 | ❌ | ✅ 裁切播放 |
| DEMO 觀感 | 普通 | ✅ 專業 |

---

## 🎨 CSS 樣式說明

### 灰色背景標示
```css
background-color: #f0f0f0;  /* 淺灰色背景 */
padding: 10px;              /* 內距 */
border-radius: 5px;         /* 圓角 */
margin: 10px 0;             /* 外距 */
color: #666;                /* 深灰色文字 */
font-size: 14px;            /* 字體大小 */
```

### 影片容器
```css
position: relative;          /* 相對定位 */
width: 50%;                  /* 容器寬度 50% */
overflow: hidden;            /* 隱藏超出部分 */
border-radius: 10px;         /* 圓角 */
box-shadow: 0 4px 6px rgba(0,0,0,0.1);  /* 陰影 */
```

### 影片裁切
```css
width: 200%;                 /* 影片寬度 200% */
margin-left: 0;              /* 從左側 0 開始（顯示左半部） */
/* 或 */
margin-left: -100%;          /* 從左側 -100% 開始（顯示右半部） */
```

---

## 🐛 疑難排解

### Q1: 影片無法播放
**檢查項目**:
1. 檔案名稱是否正確: `disaster_video.mp4`
2. 檔案是否在正確位置（與 .py 同目錄）
3. 影片格式是否為 MP4
4. 瀏覽器是否支援 HTML5 video

**解決方法**:
```bash
# 確認檔案存在
ls -la disaster_video.mp4

# 轉換影片格式
ffmpeg -i input.mov -c:v libx264 disaster_video.mp4
```

### Q2: 影片只顯示右側
**原因**: `crop_side` 參數設定錯誤

**解決**:
```python
# 確認程式碼中
display_cropped_video("disaster_video.mp4", crop_side='left')  # 左側
```

### Q3: 灰色背景沒出現
**原因**: 正在使用真實資料（API 連線成功）

**確認**:
- 灰色背景只在備用資料時顯示
- 這是正常行為

### Q4: 影片太大載入慢
**解決**:
```bash
# 壓縮影片
ffmpeg -i disaster_video.mp4 -vf scale=1280:720 -c:v libx264 -crf 28 disaster_video_small.mp4
```

---

## 💡 進階自訂

### 自訂灰色背景顏色
```python
# 修改顏色
background-color: #e8f4f8;  # 淡藍色
background-color: #fff9e6;  # 淡黃色
background-color: #f0f0f0;  # 淡灰色（預設）
```

### 在其他情境也顯示影片
```python
# 修改條件
if scenario in ['earthquake', 'flooding']:  # 地震和淹水都顯示
    display_cropped_video("disaster_video.mp4")
```

### 使用不同影片
```python
# 根據情境切換影片
video_files = {
    'earthquake': 'earthquake.mp4',
    'flooding': 'flooding.mp4',
    'war_alert': 'war.mp4'
}

if scenario in video_files:
    display_cropped_video(video_files[scenario])
```

---

## 🎉 完成檢查清單

- ✅ 移除所有干擾性警告訊息
- ✅ 加入優雅的灰色背景標示
- ✅ 支援影片播放（裁切左側）
- ✅ 地震情境自動顯示影片
- ✅ 無影片時顯示替代內容
- ✅ 所有原有功能正常運作

---

**TAI-SAFE V5 Final | 專業、簡潔、功能完整 🛡️**
