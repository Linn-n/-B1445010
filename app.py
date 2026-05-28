import streamlit as st
import yfinance as yf
import pandas as pd
import mplfinance as mpf
import datetime
import requests
import io

# --- 1. 網頁頁面設定 ---
st.set_page_config(page_title="台股自動化分析系統", layout="wide")

# --- 2. 安全密碼鎖邏輯 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True

    st.title(" 歡迎使用台股自動化分析系統")
    st.subheader("本系統僅供報告展示使用，請輸入密碼解鎖內容。")
    user_password = st.text_input("請輸入訪問密碼", type="password")
    if st.button("確認登入"):
        if user_password == "0666": 
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ 密碼錯誤，請重新輸入！")
    return False

if not check_password():
    st.stop()

# --- 3. 核心功能函數 ---
def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 🎯 靜態核心台股中文對照字典
STOCK_NAME_DICT = {
    "2330.TW": "台積電", 
    "2317.TW": "鴻海", 
    "2454.TW": "聯發科", 
    "2303.TW": "聯電", 
    "2382.TW": "廣達", 
    "3231.TW": "緯創", 
    "2356.TW": "英業達", 
    "3037.TW": "欣興", 
    "3481.TW": "群創", 
    "2409.TW": "友達", 
    "2603.TW": "長榮", 
    "2609.TW": "陽明", 
    "2610.TW": "華航", 
    "2618.TW": "長榮航", 
    "1513.TW": "中興電",
    "1519.TW": "華城",
    "2313.TW": "華通",  
    "3016.TW": "嘉晶",  
    "6207.TWO": "雷科",   
    "6488.TWO": "環球晶"  
}

def get_market_stocks():
    """直接回傳完整的 20 檔核心股票池與證交所即時漲停股"""
    base_pool = list(STOCK_NAME_DICT.keys())
    limit_up_stocks = []
    connection_status = "SUCCESS"
    
    latest_date = datetime.date.today()
    
    try:
        sample_hist = yf.Ticker("2330.TW").history(period="5d", auto_adjust=False)
        if not sample_hist.empty:
            latest_date = sample_hist.index[-1].date()
    except:
        pass

    # 嘗試抓取證交所當日漲停板
    check_date = latest_date
    mi_data = None
    for _ in range(3):
        date_str = check_date.strftime("%Y%m%d")
        url_mi = f"https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={date_str}&type=ALLBUT0999"
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            res = requests.get(url_mi, headers=headers, timeout=3)
            if res.status_code == 200:
                temp_data = res.json()
                if temp_data.get('stat') == 'OK' and ('data9' in temp_data or 'data8' in temp_data):
                    mi_data = temp_data
                    break
        except:
            pass
        check_date -= datetime.timedelta(days=1)

    if mi_data:
        data_key = 'data9' if 'data9' in mi_data else ('data8' if 'data8' in mi_data else None)
        if data_key:
            for row in mi_data[data_key]:
                try:
                    if len(row) >= 11:
                        sign = row[9]
                        if 'red' in sign or '+' in sign:
                            close_p = float(row[8].replace(',', ''))
                            change_p = float(row[10].replace(',', ''))
                            prev_close = close_p - change_p
                            if prev_close > 0 and (change_p / prev_close) * 100 >= 9.5:
                                if len(row[0]) == 4:
                                    symbol = f"{row[0]}.TW".upper()
                                    limit_up_stocks.append(symbol)
                                    if symbol not in STOCK_NAME_DICT:
                                        STOCK_NAME_DICT[symbol] = row[1].strip()
                except:
                    continue
    else:
        connection_status = "BLOCKED"

    final_list = list(dict.fromkeys(base_pool + limit_up_stocks))
    return final_list, limit_up_stocks, latest_date, connection_status

# --- 4. 網頁主畫面排版 ---
st.title(" 精準數據化股票分析網頁")
st.info(f" 系統分析時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

target_stocks, todays_limit_up, data_date, api_status = get_market_stocks()

# --- 5. 側邊欄控制 ---
st.sidebar.header(" 分析設定")
st.sidebar.write(f" 數據庫最新交易日：`{data_date}`")

if api_status == "BLOCKED":
    st.sidebar.warning("已直接載入「焦點大盤選單」（共計 20 檔中文標的）")
else:
    if todays_limit_up:
        st.sidebar.success(f" 證交所連線成功！當日即時偵測到 {len(todays_limit_up)} 檔強勢漲停股！")
    else:
        st.sidebar.info("ℹ 最新交易日暫無即時漲停數據，已自動為您展示核心大盤選單。")

# 建立漂亮的中文顯示選單
display_options = {}
for t in target_stocks:
    name = STOCK_NAME_DICT.get(t.upper(), "台灣個股")
    display_options[t] = f"{t.upper()} ({name})"

selected_stocks = st.sidebar.multiselect(
    "選擇分析標的（已整合：大盤核心焦點股 + 當日最新漲停股）", 
    options=list(display_options.keys()), 
    default=["2313.TW", "3016.TW", "6207.TWO", "6488.TWO"], 
    format_func=lambda x: display_options[x]
)

if st.sidebar.button("開始全自動數據分析"):
    if not selected_stocks:
        st.warning(" 請至少選擇一檔股票進行分析！")
    else:
        results = []
        
        for t in selected_stocks:
            full_display_name = display_options[t]
            st.subheader(f" 標的確認：{full_display_name}")
            try:
                stock = yf.Ticker(t)
                hist = stock.history(period="1y", auto_adjust=False)
                
                if not hist.empty and len(hist) >= 20:
                    hist = hist.dropna(subset=['Open', 'High', 'Low', 'Close'])
                    
                    hist['MA5'] = hist['Close'].rolling(5).mean()
                    hist['MA10'] = hist['Close'].rolling(10).mean()
                    hist['MA20'] = hist['Close'].rolling(20).mean()
                    hist['RSI'] = calculate_rsi(hist['Close'])
                    
                    latest_price = hist['Close'].iloc[-1]
                    if pd.isna(latest_price) or latest_price == 0:
                        latest_price = hist['Close'].iloc[-2]
                        
                    try:
                        info = stock.info
                        pe = info.get('trailingPE')
                        pb = info.get('priceToBook')
                        div_rate = info.get('dividendRate', 0)
                    except:
                        pe, pb, div_rate = None, None, 0
                    
                    stock_real_name = STOCK_NAME_DICT.get(t.upper(), "台灣個股")
                    ddm_val = round((div_rate * 1.02) / (0.08 - 0.02), 2) if div_rate and div_rate > 0 else "無法計算"
                    
                    ma5_last = hist['MA5'].dropna().iloc[-1]
                    ma10_last = hist['MA10'].dropna().iloc[-1]
                    ma20_last = hist['MA20'].dropna().iloc[-1]
                    
                    if latest_price > ma5_last and latest_price > ma10_last and latest_price > ma20_last:
                        ma_status = " 強勢多頭 (站上所有均線)"
                    elif latest_price < ma5_last and latest_price < ma10_last and latest_price < ma20_last:
                        ma_status = " 弱勢空頭 (均線之下)"
                    else:
                        ma_status = " 高檔震盪 / 均線糾結"
                    
                    latest_rsi = hist['RSI'].dropna().iloc[-1]
                    analysis_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

                    stock_data = {
                        "股票代碼": t,
                        "股票名稱": stock_real_name,
                        "收盤價": round(float(latest_price), 2),
                        "本益比 (P/E)": round(pe, 2) if pe else "N/A",
                        "股價淨值比 (P/B)": round(pb, 2) if pb else "N/A",
                        "DDM 估值": ddm_val,
                        "RSI(14)": round(latest_rsi, 2) if not pd.isna(latest_rsi) else "計算中",
                        "均線狀態": ma_status,
                        "分析時間": analysis_time
                    }
                    results.append(stock_data)

                    col1, col2 = st.columns([1.5, 1])
                    with col1:
                        plot_df = hist.tail(60)
                        
                        buf = io.BytesIO()
                        mc = mpf.make_marketcolors(up='red', down='green', inherit=True)
                        s = mpf.make_mpf_style(marketcolors=mc)
                        
                        # 🎨 建立獨立的三條均線線條物件
                        apds = [
                            mpf.make_addplot(plot_df['MA5'], color='red', width=1.5),      # MA5 設為紅色
                            mpf.make_addplot(plot_df['MA10'], color='orange', width=1.5),  # MA10 設為橘色
                            mpf.make_addplot(plot_df['MA20'], color='blue', width=1.5)     # MA20 設為藍色
                        ]
                        
                        fig, axlist = mpf.plot(
                            plot_df, 
                            type='candle', 
                            style=s, 
                            volume=True, 
                            addplot=apds,
                            returnfig=True
                        )
                        
                        # ✨【精準修復核心】：從畫布主軸上直接抓取最後附加的三條均線線條物件
                        lines = axlist[0].get_lines()
                        # mplfinance 繪圖後，最後加進去的三條線就是我們的 MA5, MA10, MA20
                        ma_lines = lines[-3:] 
                        
                        # 將圖例精確地跟這三條線進行一對一顏色綁定
                        axlist[0].legend(ma_lines, ['MA 5', 'MA 10', 'MA 20'], loc='upper left')
                        
                        fig.savefig(buf, format='png', bbox_inches='tight')
                        st.image(buf, use_container_width=True)
                    
                    with col2:
                        st.write("L **即時分析數據**")
                        df_display = pd.DataFrame([stock_data]).T
                        df_display.columns = ["數值"]
                        st.table(df_display)
                else:
                    st.error(f"❌ 無法取得 {t} 的足夠歷史數據（交易日不足）。")
                st.divider()
            except Exception as e:
                st.error(f"{t} 分析時出錯: {e}")

        if results:
            st.header("L 綜合分析報表總覽")
            df_all = pd.DataFrame(results)
            st.dataframe(df_all, use_container_width=True)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_all.to_excel(writer, index=False)
            st.download_button(
                label="L 下載完整 Excel 中文報表",
                data=output.getvalue(),
                file_name=f"Stock_Report_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
else:
    st.info("L 左側側邊欄點擊按鈕，開始抓取數據")

#cd C:\Users\USER\OneDrive\Desktop
#pip install yfinance streamlit pandas mplfinance requests openpyxl
#streamlit run app.py
