import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

st.set_page_config(page_title="Amazon 配送 自動割当ツール", layout="wide")
st.title("🚚 Amazon 配送 自動割当ツール")

# --- 関数定義 ---
def extract_tracking_ids(sheet_df):
    return sheet_df.iloc[3:, 1].dropna().astype(str).tolist()

def get_course_from_sheet_name(sheet_name):
    return sheet_name.split("_")[-1] if "_" in sheet_name else sheet_name

# --- ファイルアップロード ---
uploaded_file = st.file_uploader("📄 Excelファイル（B列にTracking ID、シート名にコース番号）", type=["xlsx"])
driver_master_file = st.file_uploader("📄 ドライバーマスター（drivers_master.csv）", type=["csv"])

# --- ドライバーマスター読み込み ---
if driver_master_file:
    driver_df = pd.read_csv(driver_master_file)
    driver_df.columns = driver_df.columns.str.strip().str.lower()
    driver_df = driver_df.rename(columns={
        "driver name": "driver_name",
        "transporter id": "transporter_id"
    })
    driver_df = driver_df.dropna(subset=["driver_name", "transporter_id"])
    transport_map = dict(zip(driver_df["driver_name"], driver_df["transporter_id"]))
    available_drivers = driver_df["driver_name"].unique().tolist()
else:
    available_drivers = []
    transport_map = {}

# --- セッション状態の初期化 ---
if "selected_drivers" not in st.session_state:
    st.session_state["selected_drivers"] = {}
if "results_by_course" not in st.session_state:
    st.session_state["results_by_course"] = {}

# --- 接頭辞セレクタ ---
st.markdown("### 🏷️ コース接頭辞（全体共通）")
prefix = st.selectbox("接頭辞を選択してください", options=["", "CX", "MX"], index=1)

# --- 入力フォーム ---
st.markdown("### 🔢 コース名（数字）とドライバー名（最大20名）")
driver_selections = {}
assignments = []

for i in range(1, 21):
    cols = st.columns([1, 3, 3, 3])

    with cols[0]:
        st.markdown(f"#### {i}")

    with cols[1]:
        course_number = st.text_input(f"コース番号{i}", key=f"course_{i}")

    with cols[2]:
        others_selected = {name for j, name in driver_selections.items() if j != i and name}
        current_value = st.session_state.get(f"driver_{i}", "")
        selectable_drivers = [""] + sorted([
            d for d in available_drivers
            if d == current_value or d not in others_selected
        ])
        driver = st.selectbox(f"ドライバー名{i}", options=selectable_drivers, key=f"driver_{i}")

    driver_selections[i] = driver

    if course_number.strip() and driver.strip():
        full_course = f"{prefix}{course_number.strip()}"
        assignments.append({
            "course": full_course,
            "driver": driver.strip(),
            "transport_id": transport_map.get(driver.strip(), "")
        })

        result_info = st.session_state["results_by_course"].get(full_course)

        with cols[3]:
            if result_info:
                tracking_ids = result_info["tracking_ids"]
                transport_id = result_info["transport_id"]
                tracking_copy_text = "\n".join(tracking_ids).replace("\n", "\\n")
                components.html(f"""
                    <div style='display: flex; align-items: center; gap: 5px;'>
                        <button onclick=\"navigator.clipboard.writeText('{tracking_copy_text}')\">📋 Tracking</button>
                        <button onclick=\"navigator.clipboard.writeText('{transport_id}')\">📋 Transporter</button>
                    </div>
                """, height=40)

# --- 実行ボタン ---
st.markdown("---")
if st.button("🚀 実行開始"):
    if not uploaded_file:
        st.error("⚠️ Excelファイルをアップロードしてください。")
    elif not assignments:
        st.error("⚠️ コース名とドライバー名を1件以上入力してください。")
    else:
        xls = pd.ExcelFile(uploaded_file)
        execution_pairs = []
        results_by_course = {}

        for sheet_name in xls.sheet_names:
            course_code = get_course_from_sheet_name(sheet_name)
            df = xls.parse(sheet_name, header=None)
            tracking_ids = extract_tracking_ids(df)

            for a in assignments:
                if a["course"] == course_code:
                    entry = {
                        "course": course_code,
                        "driver": a["driver"],
                        "transport_id": a["transport_id"],
                        "tracking_ids": tracking_ids
                    }
                    results_by_course[course_code] = entry
                    for tid in tracking_ids:
                        execution_pairs.append({
                            "tracking_id": tid,
                            "driver_name": a["driver"],
                            "transport_id": a["transport_id"]
                        })

        if not execution_pairs:
            st.warning("⚠️ 一致するコース名が見つかりませんでした。")
        else:
            st.success("✅ データ準備完了！")
            st.subheader("📋 コピー用データ（Tracking ID / Transporter ID）")

            tracking_copy_text = "\n".join([item['tracking_id'] for item in execution_pairs]).replace("\n", "\\n")
            unique_transport_ids = list({item['transport_id'] for item in execution_pairs})
            transport_copy_text = "\n".join(unique_transport_ids).replace("\n", "\\n")

            components.html(f"""
                <div style='display: flex; gap: 20px;'>
                    <div>
                        <button onclick=\"navigator.clipboard.writeText('{tracking_copy_text}')\">📋 全Tracking IDをコピー</button>
                    </div>
                    <div>
                        <button onclick=\"navigator.clipboard.writeText('{transport_copy_text}')\">📋 Transporter IDをコピー</button>
                    </div>
                </div>
            """, height=80)

            st.session_state["results_by_course"] = results_by_course
