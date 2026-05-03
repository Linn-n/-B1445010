import streamlit as st
import yfinance as yf
import pandas as pd
import mplfinance as mpf
import datetime
import requests
import io

# --- 網頁頁面設定 ---
st.set_page_config(page_title="台股自動化分析系統", layout="wide")

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=3600)
def get_top_5_stocks():
    url = "https://www.twse.com.tw/exchangeReport/MI_INDEX20?response=json"
    try:
        res = requests.get(url)
        data = res.json()
        return [row[1] + ".TW" for row in data['data'][:5]]
    except:
        return ["2330.TW", "2317.TW", "2454.TW", "2881.TW", "2308.TW"]

st.title("📊 精準數據化股票分析網頁")
st.info(f"📅 系統分析時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

# --- 側邊欄控制 ---
target_stocks = get_top_5_stocks()
st.sidebar.header("分析設定")
selected_stocks = st.sidebar.multiselect("選擇標的", target_stocks, default=target_stocks)

if st.sidebar.button("開始全自動數據分析"):
    results = []
    
    for t in selected_stocks:
        st.subheader(f"🔍 標的確認：{t}")
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period="1y")
            
            if not hist.empty:
                # 數據計算
                hist['MA20'] = hist['Close'].rolling(20).mean()
                hist['RSI'] = calculate_rsi(hist['Close'])
                latest_price = hist['Close'].iloc[-1]
                info = stock.info
                
                # 整理你要求的核心數據
                pe = info.get('trailingPE')
                pb = info.get('priceToBook')
                div_rate = info.get('dividendRate', 0)
                ddm_val = round((div_rate * 1.02) / (0.08 - 0.02), 2) if div_rate and div_rate > 0 else "無法計算"
                ma_status = "多頭 (均線上)" if latest_price > hist['MA20'].iloc[-1] else "空頭 (均線下)"
                latest_rsi = hist['RSI'].iloc[-1]
                analysis_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

                # 打包成單一字典（網頁顯示與 Excel 共用）
                stock_data = {
                    "股票代碼": t,
                    "名稱": info.get('shortName', 'N/A'),
                    "收盤價": round(latest_price, 2),
                    "本益比 (P/E)": round(pe, 2) if pe else "N/A",
                    "股價淨值比 (P/B)": round(pb, 2) if pb else "N/A",
                    "DDM 估值": ddm_val,
                    "RSI(14)": round(latest_rsi, 2),
                    "MA20 狀態": ma_status,
                    "分析時間": analysis_time
                }
                results.append(stock_data)

                # --- 網頁排版設計 ---
                col1, col2 = st.columns([1.5, 1])
                
                with col1:
                    # 顯示 K 線圖
                    buf = io.BytesIO()
                    mc = mpf.make_marketcolors(up='red', down='green', inherit=True)
                    s = mpf.make_mpf_style(marketcolors=mc)
                    mpf.plot(hist.tail(60), type='candle', style=s, volume=True, mav=(20, 60), savefig=buf)
                    st.image(buf, use_container_width=True)
                
                with col2:
                    # 關鍵數據清單顯示 (使用 DataFrame 轉置顯示，更像清單)
                    st.write("📝 **即時分析數據**")
                    df_display = pd.DataFrame([stock_data]).T
                    df_display.columns = ["數值"]
                    st.table(df_display)

            st.divider()
            
        except Exception as e:
            st.error(f"{t} 分析時出錯: {e}")

    # --- 底部總覽表格 ---
    if results:
        st.header("📋 綜合分析報表總覽")
        df_all = pd.DataFrame(results)
        st.dataframe(df_all, use_container_width=True)

        # 下載按鈕
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_all.to_excel(writer, index=False)
        st.download_button(
            label="📥 下載完整 Excel 報表",
            data=output.getvalue(),
            file_name=f"Stock_Report_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("👈 請在左側側邊欄點擊按鈕，開始抓取數據。")


#pip install yfinance streamlit pandas mplfinance requests openpyxl
#streamlit run app.py
