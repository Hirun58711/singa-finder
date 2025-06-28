import streamlit as st
import pandas as pd
import json
import re
from io import BytesIO
from serpapi import GoogleSearch

API_KEY = "edb0879a4af20e74c00d45785f64ed3226bb0ddd12483b1b27b1ddd8e8c8ca8a"  # ใส่ API KEY ของคุณ

@st.cache_data
def load_location_data():
    with open("api_province_with_amphure_tambon.json", "r", encoding="utf-8") as f:
        return json.load(f)

def build_hierarchy(data):
    provinces = {}
    for p in data:
        pname = p["name_th"]
        amphures = {}
        for a in p.get("amphure", []):
            aname = a["name_th"]
            tambons = [t["name_th"] for t in a.get("tambon", [])]
            amphures[aname] = tambons
        provinces[pname] = amphures
    return provinces

# โหลดข้อมูล
location_data = load_location_data()
hierarchy = build_hierarchy(location_data)

st.set_page_config(page_title="BOSS REAL NUMBER", layout="centered")
st.title("🔍 หาเบอร์ร้านไหนดีจ๊าา")

search_query = st.text_input("คำค้นหา (เช่น ร้านอาหาร, คลินิก, โรงเรียน)", "ร้านอาหาร")
province = st.selectbox("จังหวัด", list(hierarchy.keys()))
district = st.selectbox("อำเภอ/เขต (ไม่เลือก = ทั้งจังหวัด)", [""] + list(hierarchy[province].keys()))

if district:
    tambons = hierarchy[province][district]
    selected_tambons = st.multiselect("ตำบล (ไม่เลือก = ทั้งอำเภอ)", tambons)
else:
    selected_tambons = []

if st.button("ค้นหา"):
    all_results = []

    if district:
        targets = selected_tambons if selected_tambons else [district]
    else:
        targets = [province]

    for target in targets:
        query = f"{search_query} {target} {district if district else ''} {province}"
        st.write(f"📍 ค้นหา: {query}")

        params = {
            "engine": "google_maps",
            "q": query,
            "api_key": API_KEY,
            "hl": "th",
            "type": "search",
            "limit": 20
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict().get("local_results", [])
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาด: {e}")
            continue

        for place in results:
            raw_phone = place.get("phone", "")
            cleaned = re.sub(r"[^\d]", "", raw_phone)
            if cleaned.startswith("66") and len(cleaned) == 11:
                cleaned = "0" + cleaned[2:]
            if not re.fullmatch(r"0[689]\d{8}", cleaned):
                continue

            all_results.append({
                "จังหวัด": province,
                "อำเภอ": district if district else "-",
                "ตำบล": target,
                "ชื่อ": place.get("title", ""),
                "เบอร์โทร": cleaned,
                "ที่อยู่": place.get("address", ""),
                "เว็บไซต์": place.get("website", ""),
                "เรตติ้ง": place.get("rating", "")
            })

    df = pd.DataFrame(all_results)
    if not df.empty:
        st.success(f"✅ พบ {len(df)} รายการ")
        st.dataframe(df)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Results")
        output.seek(0)

        st.download_button("⬇️ ดาวน์โหลด Excel", output, "ผลลัพธ์.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.warning("ไม่พบข้อมูลที่ตรงกับเงื่อนไข")
