import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta, date as dt_date
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import json
import requests as _req

st.set_page_config(page_title="⚔️ 債券投組 vs 基金", layout="wide", page_icon="⚔️")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CSS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');
* { font-family: 'Noto Sans TC', sans-serif; }
.stApp { background: #f4f6fb; }
.block-container { padding: 1.5rem 2.5rem !important; max-width: 1400px !important; }
#MainMenu, footer, header { visibility: hidden; }

.section-hd {
    font-size: 1rem; font-weight: 700; color: #1a2744;
    padding: 8px 14px; background: linear-gradient(90deg,#e8eef8,#f5f7fc);
    border-left: 4px solid #1565c0; border-radius: 0 8px 8px 0;
    margin: 20px 0 12px 0;
}
.section-hd.purple { border-left-color: #7b1fa2; }
.section-hd.green  { border-left-color: #2e7d32; }

.metric-box {
    background: #fff; border: 1px solid #e0e4ef;
    border-radius: 10px; padding: 14px 16px; text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.metric-label { font-size: 0.72rem; color: #667; margin-bottom: 4px; }
.metric-value { font-size: 1.4rem; font-weight: 700; color: #1a2744; }
.metric-sub   { font-size: 0.75rem; color: #4a6080; margin-top:2px; }

.ptable { width:100%; border-collapse:collapse; font-size:0.84rem; border-radius:10px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.06); }
.ptable th { background:#1a2744; color:#fff; padding:9px 12px; text-align:center; }
.ptable th.left { text-align:left; }
.ptable td { padding:8px 12px; text-align:center; border-bottom:1px solid #f0f2f8; background:#fff; }
.ptable td.left { text-align:left; }
.ptable tr:last-child td { background:#fffbf0; font-weight:700; border-top:2px solid #c8a84b; }
.pos { color:#2e7d32; font-weight:600; }
.neg { color:#c62828; font-weight:600; }
.neu { color:#888; }
</style>""", unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 常數
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MASTER_SHEET_ID = "1PVXcY12Dly5l0HlOyOAKdRzegt4K6gAAQFj1YnhiHqw"
FUND_FOLDER_ID  = "1i1-zUzLNnuwo2NVWijubvBICLbladZQO"

FUND_DB = {
    "F00001DRQQ_FO": "PIMCO收益增長",
    "F0GBR04SG1_FO": "AV04駿利亨德森平衡基金",
    "F00000ZXFV_FO": "施羅德環球收息債券",
    "F00000PR1I_FO": "富達全球優質債券基金",
    "F0000176Y4_FO": "富達永續發展全球存股優勢基金",
    "F000011JGT_FO": "群益潛力收益多重",
    "F0GBR04MRL_FO": "聯博美國收益EA穩定月配",
    "FOGBR05KHT_FO": "PIMCO多元收益",
    "F0000000P6_FO": "貝萊德全球智慧數據股票入息基金",
    "F0GBR04AMK_FO": "貝萊德環球資產配置基金",
    "F00000MLER_FO": "聯博-新興市場多元收益基金",
    "F0GBR04MRF_FO": "聯博-美國成長基金",
    "F00000PA64_FO": "聯博-優化波動股票基金",
    "F00000V557_FO": "聯博全球多元",
    "F00001EQPP_FO": "富邦台美雙星多重",
    "F0HKG05X22_FO": "安聯台灣科技",
    "F00001EBH4_FO": "元大全球優質龍頭平衡基金",
}

LOCAL_DB = {
    "US02079KBP12": {"issuer": "Alphabet 公司債6",       "coupon": 5.65,  "maturity": "2056"},
    "US30303MAE21": {"issuer": "Meta平台公司債9",          "coupon": 5.625, "maturity": "2055"},
    "US64110LBA35": {"issuer": "網飛公司債3",              "coupon": 5.4,   "maturity": "2054"},
    "US03769MAC01": {"issuer": "阿波羅全球公司債1",        "coupon": 5.8,   "maturity": "2054"},
    "US191216DS69": {"issuer": "可口可樂公司債5",          "coupon": 5.3,   "maturity": "2054"},
    "US92343VGW81": {"issuer": "威瑞森電信公司債12",       "coupon": 5.5,   "maturity": "2054"},
    "XS2747599509": {"issuer": "沙烏地阿拉伯債7",          "coupon": 5.75,  "maturity": "2054"},
    "US29736RAU41": {"issuer": "雅詩蘭黛公司債3",          "coupon": 5.15,  "maturity": "2053"},
    "US037833EW60": {"issuer": "蘋果公司債14",             "coupon": 4.85,  "maturity": "2053"},
    "US91324PEW86": {"issuer": "聯合健康集團債9",          "coupon": 5.05,  "maturity": "2053"},
    "US532457CG18": {"issuer": "禮來公司債1",              "coupon": 4.875, "maturity": "2053"},
    "US91324PES74": {"issuer": "聯合健康集團債5",          "coupon": 5.875, "maturity": "2053"},
    "US459200KZ37": {"issuer": "國際商業機器債4",          "coupon": 5.1,   "maturity": "2053"},
    "US459200KV23": {"issuer": "國際商業機器公司債1",      "coupon": 4.9,   "maturity": "2052"},
    "US45866FAX24": {"issuer": "洲際交易所公司債1",        "coupon": 4.95,  "maturity": "2052"},
    "US872898AJ06": {"issuer": "TSMC公司債4",              "coupon": 4.5,   "maturity": "2052"},
    "US084664DB47": {"issuer": "波克夏金融公司債2",        "coupon": 3.85,  "maturity": "2052"},
    "US92343VGP31": {"issuer": "威瑞森電信公司債11",       "coupon": 3.875, "maturity": "2052"},
    "US828807DJ39": {"issuer": "賽門房地產集團債1",        "coupon": 3.8,   "maturity": "2050"},
    "US191216CQ13": {"issuer": "可口可樂公司債2",          "coupon": 4.2,   "maturity": "2050"},
    "US92343VFD10": {"issuer": "威瑞森電信公司債9",        "coupon": 4.0,   "maturity": "2050"},
    "US254687FM36": {"issuer": "迪士尼公司債2",            "coupon": 2.75,  "maturity": "2049"},
    "XS1982116136": {"issuer": "沙烏地阿拉伯石油公司債4", "coupon": 4.375, "maturity": "2049"},
    "US58933YAW57": {"issuer": "默克藥廠公司債1",          "coupon": 4.0,   "maturity": "2049"},
    "US125523AK66": {"issuer": "信諾公司債1",              "coupon": 4.9,   "maturity": "2048"},
    "US88579YBD22": {"issuer": "3M公司債1",                "coupon": 4.0,   "maturity": "2048"},
    "US084664CQ25": {"issuer": "波克夏海瑟威金融公司債1", "coupon": 4.2,   "maturity": "2048"},
    "XS1807174559": {"issuer": "卡達政府國際債1",          "coupon": 5.103, "maturity": "2048"},
    "US023135BJ40": {"issuer": "亞馬遜公司債1",            "coupon": 4.05,  "maturity": "2047"},
    "US375558BK80": {"issuer": "吉利德科學公司債1",        "coupon": 4.15,  "maturity": "2047"},
    "US037833CH12": {"issuer": "蘋果公司債6",              "coupon": 4.25,  "maturity": "2047"},
    "US002824BH26": {"issuer": "亞培公司債2",              "coupon": 4.9,   "maturity": "2046"},
    "XS1508675508": {"issuer": "沙烏地阿拉伯政府國際債5", "coupon": 4.5,   "maturity": "2046"},
    "US02209SAV51": {"issuer": "高特利集團公司債1",        "coupon": 3.875, "maturity": "2046"},
    "US92343VCK89": {"issuer": "威瑞森電信公司債1",        "coupon": 4.862, "maturity": "2046"},
    "US594918BT09": {"issuer": "微軟公司債2",              "coupon": 3.7,   "maturity": "2046"},
    "US125523CF53": {"issuer": "信諾公司債2",              "coupon": 4.8,   "maturity": "2046"},
    "US20030NBU46": {"issuer": "康卡斯特公司債1",          "coupon": 3.4,   "maturity": "2046"},
    "US375558BD48": {"issuer": "吉利德科學公司債2",        "coupon": 4.75,  "maturity": "2046"},
    "US02079KBN63": {"issuer": "Alphabet 公司債5",         "coupon": 5.5,   "maturity": "2046"},
    "US30303M8X35": {"issuer": "Meta平台公司債10",         "coupon": 5.5,   "maturity": "2045"},
    "US747525AK99": {"issuer": "高通公司債3",              "coupon": 4.8,   "maturity": "2045"},
    "US25468PDB94": {"issuer": "華德迪士尼公司債1",        "coupon": 4.125, "maturity": "2044"},
    "US717081DK61": {"issuer": "輝瑞藥廠公司債2",          "coupon": 4.4,   "maturity": "2044"},
    "US449276AF17": {"issuer": "IBM金融公司債1",           "coupon": 5.25,  "maturity": "2044"},
    "US02209SAR40": {"issuer": "高特利集團公司債2",        "coupon": 5.375, "maturity": "2044"},
    "US12572QAF28": {"issuer": "芝加哥期交所債1",          "coupon": 5.3,   "maturity": "2043"},
    "US037833AL42": {"issuer": "蘋果公司債2",              "coupon": 3.85,  "maturity": "2043"},
    "US084670BK32": {"issuer": "波克夏公司債1",            "coupon": 4.5,   "maturity": "2043"},
    "US594918BZ68": {"issuer": "微軟公司債7",              "coupon": 4.1,   "maturity": "2037"},
    "US717081EC37": {"issuer": "輝瑞藥廠公司債1",          "coupon": 4.0,   "maturity": "2036"},
    "US035242AM81": {"issuer": "百威英博(金融)公司債2",    "coupon": 4.7,   "maturity": "2036"},
    "US91159HJN17": {"issuer": "美國合眾銀公司債2",        "coupon": 5.836, "maturity": "2034"},
    "US55608KBG94": {"issuer": "麥格理集團公司債10",       "coupon": 5.491, "maturity": "2033"},
    "US686330AR22": {"issuer": "歐力士公司債2",            "coupon": 5.2,   "maturity": "2032"},
    "USG91139AL26": {"issuer": "TSMC全球公司債6",          "coupon": 4.625, "maturity": "2032"},
    "US92556HAC16": {"issuer": "維康公司債3",              "coupon": 4.95,  "maturity": "2050"},
    "US31428XCA28": {"issuer": "聯邦快遞公司債1",          "coupon": 5.25,  "maturity": "2050"},
    "US09062XAG88": {"issuer": "生物基因公司債2",          "coupon": 3.15,  "maturity": "2050"},
    "US37045VAT70": {"issuer": "通用汽車公司債7",          "coupon": 5.95,  "maturity": "2049"},
    "US854502AJ02": {"issuer": "史丹利百得公司債3",        "coupon": 4.85,  "maturity": "2048"},
    "US00206RCU41": {"issuer": "AT&T公司債12",             "coupon": 5.65,  "maturity": "2047"},
    "US94974BGU89": {"issuer": "富國銀行公司債10",         "coupon": 4.75,  "maturity": "2046"},
    "US172967KR13": {"issuer": "花旗集團公司債14",         "coupon": 4.75,  "maturity": "2046"},
    "US00206RCQ39": {"issuer": "AT&T公司債5",              "coupon": 4.75,  "maturity": "2046"},
    "US58013MFA71": {"issuer": "麥當勞公司債2",            "coupon": 4.875, "maturity": "2045"},
    "US42824CAY57": {"issuer": "慧與公司債1",              "coupon": 6.35,  "maturity": "2045"},
    "US09062XAD57": {"issuer": "生物基因公司債1",          "coupon": 5.2,   "maturity": "2045"},
    "US37045VAJ98": {"issuer": "通用汽車公司債4",          "coupon": 5.2,   "maturity": "2045"},
    "US61747YDY86": {"issuer": "摩根士丹利債20",           "coupon": 4.3,   "maturity": "2045"},
    "US94974BGE48": {"issuer": "富國銀行債9",              "coupon": 4.65,  "maturity": "2044"},
    "US172967HS33": {"issuer": "花旗集團債12",             "coupon": 5.3,   "maturity": "2044"},
    "XS1049699926": {"issuer": "渣打集團債6",              "coupon": 5.7,   "maturity": "2044"},
    "US404280AQ21": {"issuer": "匯豐控股公司債8",          "coupon": 5.25,  "maturity": "2044"},
    "US37045VAF76": {"issuer": "通用汽車公司債3",          "coupon": 6.25,  "maturity": "2043"},
    "US92553PAP71": {"issuer": "維康公司債2",              "coupon": 4.375, "maturity": "2043"},
    "US00206RBH49": {"issuer": "AT&T公司債1",              "coupon": 4.3,   "maturity": "2042"},
    "US71568QAB32": {"issuer": "印尼國家電力債2",          "coupon": 5.25,  "maturity": "2042"},
    "US854502AA92": {"issuer": "史丹利百得公司債2",        "coupon": 5.2,   "maturity": "2040"},
    "US50076QAN60": {"issuer": "卡夫亨氏公司債1",          "coupon": 6.5,   "maturity": "2040"},
    "XS2885079702": {"issuer": "國泰人壽公司債2",          "coupon": 5.3,   "maturity": "2039"},
    "US46625HHF01": {"issuer": "摩根大通銀行債3",          "coupon": 6.4,   "maturity": "2038"},
    "US37045VAP58": {"issuer": "通用汽車公司債2",          "coupon": 5.15,  "maturity": "2038"},
    "US126650CY46": {"issuer": "CVS公司債1",               "coupon": 4.78,  "maturity": "2038"},
    "US38141GFD16": {"issuer": "美高盛公司債14",           "coupon": 6.75,  "maturity": "2037"},
    "US00206RDR03": {"issuer": "AT&T公司債3",              "coupon": 5.25,  "maturity": "2037"},
    "US404280AG49": {"issuer": "匯豐銀行公司債4",          "coupon": 6.5,   "maturity": "2036"},
    "US38143YAC75": {"issuer": "美商高盛證券公司債16",     "coupon": 6.45,  "maturity": "2036"},
    "US925524AX89": {"issuer": "維康公司債1",              "coupon": 6.875, "maturity": "2036"},
    "US37045VAK61": {"issuer": "通用汽車公司債1",          "coupon": 6.6,   "maturity": "2036"},
    "XS3151416727": {"issuer": "富邦人壽(新加坡)1",       "coupon": 5.45,  "maturity": "2035"},
    "US06051GLU12": {"issuer": "美國銀行公司債6",          "coupon": 5.872, "maturity": "2034"},
    "XS2852920342": {"issuer": "國泰人壽公司債1",          "coupon": 5.95,  "maturity": "2034"},
    "US458140CA64": {"issuer": "英特爾公司債5",            "coupon": 4.15,  "maturity": "2032"},
}

FUND_COLORS     = ["#9c27b0","#e65100","#2e7d32","#c62828","#00838f","#827717","#37474f"]
BOND_IND_COLORS = ["#00695c","#00838f","#006064","#4527a0","#283593",
                   "#558b2f","#e65100","#ad1457","#6d4c41","#37474f"]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Google Sheets 函數
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@st.cache_resource
def get_gs_client():
    creds = Credentials.from_service_account_info(
        json.loads(st.secrets["GOOGLE_CREDENTIALS"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly"])
    return gspread.authorize(creds)

def _get_token():
    from google.auth.transport.requests import Request
    creds = Credentials.from_service_account_info(
        json.loads(st.secrets["GOOGLE_CREDENTIALS"]),
        scopes=["https://www.googleapis.com/auth/drive.readonly"])
    creds.refresh(Request())
    return creds.token

@st.cache_data(ttl=600)
def list_folder(folder_id):
    token = _get_token()
    resp = _req.get("https://www.googleapis.com/drive/v3/files",
        headers={"Authorization": f"Bearer {token}"},
        params={"q": f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
                "fields": "files(id,name)", "pageSize": 200})
    return {f["name"]: f["id"] for f in resp.json().get("files", [])}

@st.cache_data(ttl=300)
def read_bond_sheet(sheet_id):
    import time
    client = get_gs_client()
    for attempt in range(3):
        try:
            ws = client.open_by_key(sheet_id).get_worksheet(0)
            df = pd.DataFrame(ws.get_all_records())
            # 日期欄
            if "time" in df.columns:
                df["date"] = pd.to_datetime(df["time"], unit="s")
            elif "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            else:
                df["date"] = pd.to_datetime(df.iloc[:, 0])
            # 價格欄：優先找 close，找不到就用第一個數值欄
            if "close" not in df.columns:
                num_cols = [c for c in df.columns
                            if c not in ("date","time")
                            and pd.to_numeric(df[c], errors="coerce").notna().sum() > len(df)*0.5]
                if not num_cols:
                    raise ValueError(f"找不到價格欄位，現有欄位：{list(df.columns)}")
                df["close"] = pd.to_numeric(df[num_cols[0]], errors="coerce")
            else:
                df["close"] = pd.to_numeric(df["close"], errors="coerce")
            return df[["date","close"]].dropna().sort_values("date").reset_index(drop=True)
        except Exception as e:
            if "503" in str(e) and attempt < 2: time.sleep(3)
            else: raise e

@st.cache_data(ttl=300)
def read_fund_sheet(sheet_id):
    import time
    client = get_gs_client()
    for attempt in range(3):
        try:
            ws = client.open_by_key(sheet_id).get_worksheet(0)
            df = pd.DataFrame(ws.get_all_records())
            df["date"]  = pd.to_datetime(df.iloc[:,0], errors="coerce")
            df["close"] = pd.to_numeric(df.iloc[:,1], errors="coerce")
            return df[["date","close"]].dropna().sort_values("date").reset_index(drop=True)
        except Exception as e:
            if "503" in str(e) and attempt < 2: time.sleep(3)
            else: raise e

@st.cache_data(ttl=3600)
def load_master_db():
    try:
        client = get_gs_client()
        ws = client.open_by_key(MASTER_SHEET_ID).get_worksheet(0)
        rows = ws.get_all_records()
        db = dict(LOCAL_DB)
        for row in rows:
            code = str(row.get("ISIN/代碼","")).strip()
            name = str(row.get("債券名稱","")).strip()
            if not code or not name: continue
            ex = db.get(code, {})
            db[code] = {"issuer": name, "coupon": ex.get("coupon",0.0), "maturity": ex.get("maturity","")}
        return db
    except Exception:
        return LOCAL_DB

@st.cache_data(ttl=600)
def build_bond_catalog(master_id, bond_folder_id):
    try:
        import csv, io
        client = get_gs_client()
        master_rows = client.open_by_key(master_id).get_worksheet(0).get_all_records()
        file_opts   = list_folder(bond_folder_id)
        db          = load_master_db()
        catalog     = {}
        for row in master_rows:
            keys = list(row.keys())
            if len(keys) == 1 and ',' in keys[0]:
                col_names = [c.strip() for c in next(csv.reader([keys[0]]))]
                values    = [v.strip() for v in next(csv.reader([str(list(row.values())[0])]))]
                row = dict(zip(col_names, values))
            filename  = str(row.get("檔名","")).strip()
            isin      = str(row.get("ISIN/代碼","")).strip()
            bond_name = str(row.get("債券名稱","")).strip()
            if not filename or not bond_name: continue
            sheet_id = None
            cm = filename.replace(", 1D","").replace(",1D","").strip()
            for fname, fid in file_opts.items():
                cf = fname.replace(", 1D","").replace(",1D","").replace(".csv","").strip()
                if cm == cf or cm in cf or cf in cm:
                    sheet_id = fid; break
            if not sheet_id: continue
            info = db.get(isin, {})
            catalog[bond_name] = {
                "sheet_id": sheet_id, "isin": isin,
                "coupon": info.get("coupon",0.0), "maturity": info.get("maturity",""),
                "name": bond_name
            }
        return catalog
    except Exception as e:
        st.error(f"❌ 債券清單載入失敗：{e}")
        return {}

@st.cache_data(ttl=600)
def build_fund_catalog(fund_folder_id):
    try:
        fund_files = list_folder(fund_folder_id)
        return {name: {"sheet_id": fund_files[ticker], "ticker": ticker}
                for ticker, name in FUND_DB.items() if ticker in fund_files}
    except Exception as e:
        st.error(f"❌ 基金清單載入失敗：{e}")
        return {}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 計算函數
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def calc_ytm(price, coupon_rate, maturity_str):
    """Newton-Raphson YTM (semi-annual compounding, face=100)"""
    try:
        years = max(int(maturity_str) - dt_date.today().year, 0.5)
        n = max(round(years * 2), 1)
        c = coupon_rate / 2          # semi-annual coupon
        r = 0.025                    # initial guess: 5% annual → 2.5% semi
        for _ in range(200):
            periods = np.arange(1, n+1)
            pv   = float(np.sum(c / (1+r)**periods) + 100 / (1+r)**n)
            dpv  = float(-np.sum(periods*c / (1+r)**(periods+1)) - n*100 / (1+r)**(n+1))
            if abs(dpv) < 1e-12: break
            r_new = max(-0.99, min(r - (pv - price) / dpv, 5.0))
            if abs(r_new - r) < 1e-9: r = r_new; break
            r = r_new
        return r * 2   # annualize
    except Exception:
        return None

def calc_cy(price, coupon_rate):
    """Current Yield = annual coupon / price (face=100)"""
    return coupon_rate / price if price > 0 else None

def bond_daily_tri(df, coupon_rate):
    """Total return index for a single bond (starts at 100)"""
    prices = df["close"].values.astype(float)
    dc = (coupon_rate / 100) / 365
    tri = np.empty(len(prices))
    tri[0] = 100.0
    for i in range(1, len(prices)):
        tri[i] = tri[i-1] * (1 + (prices[i]-prices[i-1])/prices[i-1] + dc)
    return tri

def fund_tri(df):
    """Normalize fund NAV to 100"""
    p = df["close"].values.astype(float)
    return p / p[0] * 100

def build_portfolio_tri(bond_dfs_coupons, weights):
    """
    Blend bond TRIs into a single portfolio TRI.
    bond_dfs_coupons 和 weights 長度必須一致（只傳入成功載入的債券）。
    Returns (dates_array, tri_array) aligned to common dates.
    """
    if not bond_dfs_coupons or len(bond_dfs_coupons) != len(weights):
        return None, None

    # 每支債券建立日報酬 Series（欄名唯一：r_0, r_1, ...）
    ret_frames = []
    for i, (df, coupon) in enumerate(bond_dfs_coupons):
        tmp = df.copy()
        tmp["date"] = pd.to_datetime(tmp["date"])
        tmp = tmp.set_index("date").sort_index()
        dc = (coupon / 100) / 365
        col = f"r_{i}"
        tmp[col] = tmp["close"].pct_change() + dc
        ret_frames.append(tmp[[col]].dropna())

    # pd.concat 取交集日期（比 .join() 更穩定）
    merged = pd.concat(ret_frames, axis=1, join="inner")
    if merged.empty:
        return None, None

    # 確認欄數與權重數相符
    cols = merged.columns.tolist()
    if len(cols) != len(weights):
        return None, None

    # 加權日報酬（用欄名存取，不用 iloc 避免越界）
    w = np.array(weights, dtype=float) / sum(weights)
    port_ret = merged[cols[0]] * w[0]
    for i in range(1, len(cols)):
        port_ret = port_ret + merged[cols[i]] * w[i]

    tri = [100.0]
    for r in port_ret.values:
        tri.append(tri[-1] * (1 + r))

    first_date = merged.index[0] - pd.Timedelta(days=1)
    dates = np.concatenate([[first_date], merged.index.values])
    return dates, np.array(tri)

def calc_mdd(tri):
    arr = np.array(tri, dtype=float)
    return float(((arr - np.maximum.accumulate(arr)) / np.maximum.accumulate(arr)).min())

def calc_sharpe(tri, rf=0.04):
    rets = pd.Series(tri).pct_change().dropna()
    excess = rets - rf/252
    return float(excess.mean() / excess.std() * np.sqrt(252)) if excess.std() > 0 else 0.0

def calc_ann_ret(tri, dates):
    years = (pd.to_datetime(dates[-1]) - pd.to_datetime(dates[0])).days / 365
    return float((tri[-1]/tri[0])**(1/years) - 1) if years > 0.01 else 0.0

def period_ret(tri, dates, days):
    end = pd.to_datetime(dates[-1])
    mask = pd.to_datetime(dates) >= end - timedelta(days=days)
    sub = np.array(tri)[mask]
    return float((sub[-1]-sub[0])/sub[0]) if len(sub) >= 2 else None

def fmt_pct(v, bold=False):
    if v is None: return '<span class="neu">—</span>'
    cls = "pos" if v > 0.0005 else ("neg" if v < -0.0005 else "neu")
    s = f"{v:+.2%}"
    return f'<span class="{cls}"><b>{s}</b></span>' if bold else f'<span class="{cls}">{s}</span>'

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 主介面
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("""
<div style='padding:18px 0 6px 0'>
  <h1 style='font-size:1.75rem;color:#1a2744;margin:0'>⚔️ 自組債券投組 vs 基金對決</h1>
  <p style='color:#4a6080;margin:4px 0 0 0;font-size:0.9rem'>
    自組你的 CB 投組，正面挑戰各大債券基金｜含 YTM、當期收益率、MDD、Sharpe、現金流試算
  </p>
</div>
<hr style='border:none;border-top:2px solid #e0e4ef;margin:0 0 20px 0'>
""", unsafe_allow_html=True)

folder_id = st.secrets.get("FOLDER_ID", "")

with st.spinner("載入債券與基金清單..."):
    bond_catalog = build_bond_catalog(MASTER_SHEET_ID, folder_id)
    fund_catalog  = build_fund_catalog(FUND_FOLDER_ID)

if not bond_catalog:
    st.error("❌ 無法載入債券清單，請確認 FOLDER_ID 與 GOOGLE_CREDENTIALS")
    st.stop()

# ─── A：債券投組設定 ───
st.markdown('<div class="section-hd">🏦 部隊甲：自組債券投組</div>', unsafe_allow_html=True)

bond_options = sorted(bond_catalog.keys())
selected_bonds = st.multiselect(
    "選擇債券（可多選，最多 10 支）",
    options=bond_options, max_selections=10,
    help="從你的債券庫選擇要放入投組的債券，系統自動讀取最新價格並計算 YTM"
)

weights = {}
if selected_bonds:
    default_w = round(100 / len(selected_bonds), 1)
    st.markdown("**⚖️ 設定比重（%）**　*可手動調整，系統自動正規化至 100%*")
    for row_start in range(0, len(selected_bonds), 5):
        chunk = selected_bonds[row_start:row_start+5]
        cols = st.columns(len(chunk))
        for j, bname in enumerate(chunk):
            short = bond_catalog[bname]["name"][:12]
            with cols[j]:
                weights[bname] = st.number_input(
                    short, min_value=0.0, max_value=100.0,
                    value=default_w, step=5.0, key=f"w_{bname}"
                )
    total_w = sum(weights.values())
    if abs(total_w - 100) > 0.5:
        st.warning(f"⚠️ 比重合計：{total_w:.1f}%（計算時將自動正規化為 100%）")
    else:
        st.success(f"✅ 比重合計：{total_w:.1f}%")

# ─── B：對比基金選擇 ───
st.markdown('<div class="section-hd purple">🏦 部隊乙：對比基金</div>', unsafe_allow_html=True)
fund_options = sorted(fund_catalog.keys())
selected_funds = st.multiselect(
    "選擇對比基金（可多選，最多 6 支）",
    options=fund_options, max_selections=6,
    help="選擇你想比較的債券基金，不一定要是債券基金，任何基金都可以挑戰"
)

st.markdown("---")

# ─── 開始分析 ───
if not selected_bonds:
    st.info("👆 請先選擇至少 1 支債券，建立你的投組")
    st.stop()

run = st.button("🚀 開始分析", type="primary", use_container_width=False)
if not run and "last_result" not in st.session_state:
    st.stop()

# ─── 載入資料 ───
with st.spinner("載入債券與基金資料..."):
    norm_w = {k: v/sum(weights.values()) for k, v in weights.items()} if sum(weights.values()) > 0 \
             else {k: 1/len(selected_bonds) for k in selected_bonds}

    # Load bond data
    bond_rows = []
    bond_dfs_coupons = []
    load_ok = True
    for bname in selected_bonds:
        info = bond_catalog[bname]
        try:
            df = read_bond_sheet(info["sheet_id"])
            latest_price = float(df["close"].iloc[-1])
            coupon   = info["coupon"]
            maturity = info["maturity"]
            ytm = calc_ytm(latest_price, coupon, maturity) if coupon > 0 and maturity else None
            cy  = calc_cy(latest_price, coupon)
            bond_rows.append({
                "name": bname, "coupon": coupon, "maturity": maturity,
                "price": latest_price, "ytm": ytm, "cy": cy,
                "weight": norm_w[bname],
                "df": df,   # 保留原始資料供個別 TRI 使用
            })
            bond_dfs_coupons.append((df, coupon))
        except Exception as e:
            st.error(f"❌ {bname} 讀取失敗：{e}")
            load_ok = False

    # Load fund data
    fund_series = []
    for fname in selected_funds:
        info = fund_catalog[fname]
        try:
            df = read_fund_sheet(info["sheet_id"])
            fund_series.append({"name": fname, "df": df})
        except Exception as e:
            st.error(f"❌ {fname} 讀取失敗：{e}")

    # Build portfolio TRI（只用成功載入的債券及對應權重）
    if not load_ok:
        st.error("❌ 部分債券讀取失敗，請移除後重試")
        st.stop()

    loaded_bond_names = [r["name"] for r in bond_rows]
    loaded_weights = [norm_w[b] for b in loaded_bond_names]
    port_dates, port_tri = build_portfolio_tri(bond_dfs_coupons, loaded_weights)

if not load_ok or port_dates is None:
    st.error("❌ 投組資料合併失敗（可能是選取債券的資料期間無交集）")
    st.stop()

st.session_state["last_result"] = True

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 一、投組明細 + YTM/CY 摘要
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-hd">📋 債券投組明細</div>', unsafe_allow_html=True)

wtd_coupon = sum(r["coupon"] * r["weight"] for r in bond_rows)
ytm_valid  = [r for r in bond_rows if r["ytm"] is not None]
wtd_ytm    = sum(r["ytm"] * r["weight"] for r in ytm_valid) / sum(r["weight"] for r in ytm_valid) if ytm_valid else None
cy_valid   = [r for r in bond_rows if r["cy"] is not None]
wtd_cy     = sum(r["cy"] * r["weight"] for r in cy_valid) / sum(r["weight"] for r in cy_valid) if cy_valid else None

rows_html = ""
for r in bond_rows:
    ytm_s = f"{r['ytm']*100:.2f}%" if r["ytm"] else "—"
    cy_s  = f"{r['cy']*100:.2f}%"  if r["cy"]  else "—"
    rows_html += f"""<tr>
        <td class='left'>{r['name']}</td>
        <td>{r['coupon']:.2f}%</td>
        <td>{r['maturity']}</td>
        <td>{r['price']:.2f}</td>
        <td class='{'pos' if r['ytm'] and r['ytm']>0.04 else 'neu'}'>{ytm_s}</td>
        <td>{cy_s}</td>
        <td><b>{r['weight']*100:.1f}%</b></td>
    </tr>"""

ytm_avg_s = f"{wtd_ytm*100:.2f}%" if wtd_ytm else "—"
cy_avg_s  = f"{wtd_cy*100:.2f}%"  if wtd_cy  else "—"

st.markdown(f"""<table class='ptable'>
  <thead><tr>
    <th class='left'>債券名稱</th><th>票息率</th><th>到期年</th>
    <th>最新價格</th><th>YTM</th><th>當期收益率</th><th>比重</th>
  </tr></thead>
  <tbody>
    {rows_html}
    <tr>
      <td class='left'><b>⚖️ 加權平均</b></td>
      <td><b>{wtd_coupon:.2f}%</b></td><td>—</td><td>—</td>
      <td><b style='color:#1565c0'>{ytm_avg_s}</b></td>
      <td><b style='color:#1565c0'>{cy_avg_s}</b></td>
      <td><b>100%</b></td>
    </tr>
  </tbody>
</table>""", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# 投組摘要 Cards
inv = st.number_input("💵 試算投資金額（萬美元）", min_value=1, max_value=100000, value=100, step=10)
monthly_cf = inv * 10000 * (wtd_coupon/100) / 12
c1,c2,c3,c4 = st.columns(4)
def mcard(label, value, sub, color="#1a2744"):
    return f"""<div class='metric-box'>
        <div class='metric-label'>{label}</div>
        <div class='metric-value' style='color:{color}'>{value}</div>
        <div class='metric-sub'>{sub}</div>
    </div>"""
c1.markdown(mcard("⚖️ 加權平均 YTM", ytm_avg_s, "到期殖利率", "#1565c0"), unsafe_allow_html=True)
c2.markdown(mcard("💰 加權平均當期收益率", cy_avg_s, "Annual Coupon / Price", "#2e7d32"), unsafe_allow_html=True)
c3.markdown(mcard("🎯 加權平均票息率", f"{wtd_coupon:.2f}%", "Coupon Rate（面值計）", "#c8a84b"), unsafe_allow_html=True)
c4.markdown(mcard("📅 預估月配息",
    f"USD {monthly_cf:,.0f}",
    f"≈ TWD {monthly_cf*32:,.0f}　（{inv}萬美元）", "#7b1fa2"), unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 二、績效比較
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("---")
st.markdown('<div class="section-hd green">📈 績效比較</div>', unsafe_allow_html=True)

# 日期範圍
port_start = pd.Timestamp(port_dates[0]).date()
port_end   = pd.Timestamp(port_dates[-1]).date()

qcols = st.columns(6)
for label, days in [("1年",365),("2年",730),("3年",1095),("5年",1825),("全部",99999)]:
    if qcols[[1,2,3,4,5][["1年","2年","3年","5年","全部"].index(label)]].button(label):
        st.session_state["cmp_start"] = max(port_end - timedelta(days=days), port_start)
        st.rerun()

dc1, dc2 = st.columns(2)
default_start = st.session_state.get("cmp_start", max(port_end - timedelta(days=1095), port_start))
default_start = max(min(default_start, port_end), port_start)
cmp_start = dc1.date_input("起始日", value=default_start, min_value=port_start, max_value=port_end)
cmp_end   = dc2.date_input("結束日", value=port_end,      min_value=port_start, max_value=port_end)

# 建立比較系列
ts_start = pd.Timestamp(cmp_start)
ts_end   = pd.Timestamp(cmp_end)
port_mask = (pd.to_datetime(port_dates) >= ts_start) & (pd.to_datetime(port_dates) <= ts_end)
p_dates = port_dates[port_mask]
p_tri   = port_tri[port_mask]

if len(p_tri) < 2:
    st.warning("⚠️ 所選期間投組資料不足，請調整日期範圍")
    st.stop()

# 正規化投組 TRI 到選定起始點=100
p_tri = p_tri / p_tri[0] * 100

# ─── 走勢圖 ───
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=p_dates, y=p_tri,
    name="🏦 自組債券投組",
    line=dict(color="#1565c0", width=3),
))

for i, fs in enumerate(fund_series):
    fdf = fs["df"]
    mask = (fdf["date"] >= ts_start) & (fdf["date"] <= ts_end)
    sub  = fdf[mask].copy()
    if sub.empty: continue
    fnav = fund_tri(sub)
    fig.add_trace(go.Scatter(
        x=sub["date"], y=fnav,
        name=fs["name"],
        line=dict(color=FUND_COLORS[i % len(FUND_COLORS)], width=2, dash="dot"),
    ))

# 個別債券（細線，半透明感）
for i, br in enumerate(bond_rows):
    bdf = br["df"]
    mask = (bdf["date"] >= ts_start) & (bdf["date"] <= ts_end)
    sub  = bdf[mask].copy()
    if sub.empty: continue
    btri = bond_daily_tri(sub, br["coupon"])
    btri = btri / btri[0] * 100
    fig.add_trace(go.Scatter(
        x=sub["date"], y=btri,
        name=br["name"][:20],
        line=dict(color=BOND_IND_COLORS[i % len(BOND_IND_COLORS)], width=1.2, dash="dash"),
        opacity=0.75,
    ))

fig.add_hline(y=100, line_dash="dash", line_color="#aaa", line_width=1)
fig.update_layout(
    title="含息總報酬指數（起始=100）",
    yaxis_title="總報酬指數（含息，起始=100）",
    hovermode="x unified", height=460,
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    plot_bgcolor="#fff", paper_bgcolor="#f4f6fb",
    xaxis=dict(showgrid=True, gridcolor="#e8ecf2"),
    yaxis=dict(showgrid=True, gridcolor="#e8ecf2"),
)
st.plotly_chart(fig, use_container_width=True)

# ─── 績效摘要表 ───
st.markdown("**📊 各期間績效比較**")
periods = [("1個月",30),("3個月",90),("6個月",180),("1年",365),("2年",730),("3年",1095),("5年",1825)]

all_series = [{"name":"🏦 自組債券投組","dates":p_dates,"tri":p_tri,"color":"#1565c0"}]
for i, fs in enumerate(fund_series):
    fdf = fs["df"]
    mask = (fdf["date"] >= ts_start) & (fdf["date"] <= ts_end)
    sub  = fdf[mask].copy()
    if sub.empty: continue
    fnav = fund_tri(sub)
    all_series.append({"name":fs["name"],"dates":sub["date"].values,"tri":fnav,"color":FUND_COLORS[i%len(FUND_COLORS)]})

# 個別債券系列（用青綠色系區分）
for i, br in enumerate(bond_rows):
    bdf = br["df"]
    mask = (bdf["date"] >= ts_start) & (bdf["date"] <= ts_end)
    sub  = bdf[mask].copy()
    if sub.empty: continue
    btri = bond_daily_tri(sub, br["coupon"])
    btri = btri / btri[0] * 100   # 正規化至起始=100
    short = br["name"][:16]
    all_series.append({
        "name": f"│ {short}",
        "dates": sub["date"].values,
        "tri": btri,
        "color": BOND_IND_COLORS[i % len(BOND_IND_COLORS)],
        "is_bond_individual": True,
    })

# Period returns table
hdr = "<thead><tr><th>期間</th>"
for s in all_series:
    short = s["name"][:14]
    hdr += f'<th style="background:{s["color"]};color:#fff">{short}</th>'
hdr += "</tr></thead>"

body = "<tbody>"
for plabel, pdays in periods:
    body += f"<tr><td class='left' style='font-weight:600'>{plabel}</td>"
    for s in all_series:
        r = period_ret(s["tri"], s["dates"], pdays)
        body += f"<td>{fmt_pct(r, bold=True)}</td>"
    body += "</tr>"
body += "</tbody>"

st.markdown(f"<table class='ptable'>{hdr}{body}</table>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ─── 風險指標摘要 ───
st.markdown("**⚠️ 風險指標比較**")
risk_hdr = "<thead><tr><th class='left'>指標</th>"
for s in all_series:
    risk_hdr += f'<th style="background:{s["color"]};color:#fff">{s["name"][:14]}</th>'
risk_hdr += "</tr></thead>"

risk_body = "<tbody>"
metrics = [
    ("📈 區間總報酬",  lambda s: period_ret(s["tri"], s["dates"], 99999)),
    ("📉 最大回撤 MDD", lambda s: calc_mdd(s["tri"])),
    ("⚡ 年化報酬",    lambda s: calc_ann_ret(s["tri"], s["dates"])),
    ("🎯 Sharpe 比率", lambda s: None),  # placeholder
]

ann_vals = [calc_ann_ret(s["tri"], s["dates"]) for s in all_series]
mdd_vals = [calc_mdd(s["tri"]) for s in all_series]
shr_vals = [calc_sharpe(s["tri"]) for s in all_series]
total_r  = [(s["tri"][-1]/s["tri"][0] - 1) for s in all_series]

for label, vals in [
    ("📈 區間總報酬",    total_r),
    ("⚡ 年化報酬",      ann_vals),
    ("📉 最大回撤 MDD",  mdd_vals),
    ("🎯 Sharpe 比率",   shr_vals),
]:
    risk_body += f"<tr><td class='left' style='font-weight:600'>{label}</td>"
    for v in vals:
        if label == "🎯 Sharpe 比率":
            risk_body += f"<td><b>{v:.2f}</b></td>"
        else:
            risk_body += f"<td>{fmt_pct(v, bold=True)}</td>"
    risk_body += "</tr>"
risk_body += "</tbody>"

st.markdown(f"<table class='ptable'>{risk_hdr}{risk_body}</table>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ─── 逐年報酬 ───
st.markdown("**📅 逐年報酬比較**")

def calc_annual_rets(tri_arr, dates_arr):
    df = pd.DataFrame({"date": pd.to_datetime(dates_arr), "tri": tri_arr})
    df["year"] = df["date"].dt.year
    rows = {}
    for y, grp in df.groupby("year"):
        if len(grp) < 2: continue
        rows[str(y)] = (grp["tri"].iloc[-1] - grp["tri"].iloc[0]) / grp["tri"].iloc[0]
    return rows

all_ann = [calc_annual_rets(s["tri"], s["dates"]) for s in all_series]
all_years = sorted(set(y for ann in all_ann for y in ann.keys()), reverse=True)

ann_hdr = "<thead><tr><th class='left'>年度</th>"
for s in all_series:
    ann_hdr += f'<th style="background:{s["color"]};color:#fff">{s["name"][:14]}</th>'
ann_hdr += "</tr></thead><tbody>"

for yr in all_years:
    ann_hdr += f"<tr><td class='left' style='font-weight:700'>{yr}</td>"
    for ann in all_ann:
        r = ann.get(yr)
        ann_hdr += f"<td>{fmt_pct(r, bold=True)}</td>"
    ann_hdr += "</tr>"
ann_hdr += "</tbody>"
st.markdown(f"<table class='ptable'>{ann_hdr}</table>", unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 三、現金流試算
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("---")
st.markdown('<div class="section-hd">💰 現金流試算</div>', unsafe_allow_html=True)
st.caption(f"以上方設定的 **{inv} 萬美元** 投資金額計算")

cf_months = list(range(1, 13))
months_tc = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]

annual_coupon_usd = inv * 10000 * (wtd_coupon / 100)
monthly_usd = annual_coupon_usd / 12

cf_fig = go.Figure()
cf_fig.add_trace(go.Bar(
    x=months_tc, y=[monthly_usd]*12,
    name=f"自組債券投組 (票息 {wtd_coupon:.2f}%)",
    marker_color="#1565c0",
))
cf_fig.update_layout(
    title=f"預估每月票息配息（{inv} 萬美元）",
    yaxis_title="美元 USD",
    height=340, plot_bgcolor="#fff", paper_bgcolor="#f4f6fb",
    xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#e8ecf2"),
    legend=dict(orientation="h", y=1.05),
)
st.plotly_chart(cf_fig, use_container_width=True)

ca, cb, cc = st.columns(3)
ca.metric("💵 預估月配息",  f"USD {monthly_usd:,.0f}",   f"≈ TWD {monthly_usd*32:,.0f}")
cb.metric("📅 預估年配息",  f"USD {annual_coupon_usd:,.0f}", f"票息率 {wtd_coupon:.2f}%")
cc.metric("🎯 YTM 到期總報酬率", ytm_avg_s, "（含資本利得估算）")

st.markdown("""
<div style='margin-top:20px;padding:12px 16px;background:#fffbf0;border-left:4px solid #c8a84b;border-radius:0 8px 8px 0;font-size:0.8rem;color:#5a4a00;'>
⚠️ <b>免責聲明：</b>本工具僅供內部教育訓練使用。YTM 以到期年末估算，現金流以票息率（面值計）估算，
不代表實際投資報酬。債券價格與配息可能因市場利率、信用風險等因素變動。請勿作為投資建議。
</div>
""", unsafe_allow_html=True)
