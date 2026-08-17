import os
import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import google.generativeai as genai
import re

# ==========================================
# 🔑 Fetch API Key from Streamlit Secrets
# ==========================================
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def generate_sql_with_gemini(prompt_text):
    try:
        live_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    except Exception:
        live_models = []

    flash_models = [m for m in live_models if 'flash' in m.lower()]
    other_models = [m for m in live_models if m not in flash_models]
    candidates = flash_models + other_models

    if not candidates:
        candidates = ['models/gemini-2.5-flash', 'gemini-2.5-flash', 'gemini-flash-latest']

    last_error = None
    for model_name in candidates:
        try:
            m = genai.GenerativeModel(model_name)
            res = m.generate_content(prompt_text)
            if res and res.text:
                return res.text
        except Exception as e:
            last_error = e
            continue

    raise last_error if last_error else Exception("Unable to generate response from model.")


# Page Setup & Theme Styling
st.set_page_config(
    page_title="Talk to Your Data | Text-to-SQL Engine",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
    <style>
    .main { background-color: #F8FAFC; }
    h1, h2, h3 { color: #0F172A; font-family: 'Space Grotesk', sans-serif; }
    .stButton>button { background-color: #2563EB; color: white; border-radius: 6px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Talk to Your Data — AI Analytics Engine")
st.write("Upload any CSV file, ask questions in plain English, and get instant SQL execution with dynamic charts.")

# Sidebar - File Ingestion
st.sidebar.header("📁 Data Ingestion")
uploaded_file = st.sidebar.file_uploader("Upload CSV Dataset", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.sidebar.success(f"Loaded {len(df)} rows successfully!")

    with st.expander("👀 View Raw Dataset Preview", expanded=False):
        st.dataframe(df.head(10), use_container_width=True)

    columns_info = ", ".join([f"{col} ({dtype})" for col, dtype in zip(df.columns, df.dtypes)])
    sample_rows = df.head(2).to_string()

    st.divider()

    user_query = st.text_input("💬 Ask a question about this data:",
                               placeholder="e.g., Show total Sales by Region as a bar chart")

    if user_query:
        if not GEMINI_API_KEY:
            st.error("⚠️ Gemini API Key not found. Please set GEMINI_API_KEY in Streamlit Secrets.")
        else:
            with st.spinner("🤖 Translating natural language to DuckDB SQL..."):
                prompt = f"""
                You are an expert DuckDB SQL analyst.
                The table name is strictly 'df'.

                Columns and types: {columns_info}
                Sample rows:
                {sample_rows}

                User Question: "{user_query}"

                Rules:
                1. Return ONLY the valid executable SQL query. Do not include markdown tags like ```sql or ```.
                2. Do not write explanations.
                3. Query must be compatible with DuckDB and table name 'df'.
                """

                try:
                    raw_sql = generate_sql_with_gemini(prompt)

                    sql_query = raw_sql.strip()
                    sql_query = re.sub(r"```sql|```", "", sql_query).strip()

                    col_left, col_right = st.columns([1, 1])

                    with col_left:
                        st.subheader("🔍 Generated SQL Query")
                        st.code(sql_query, language="sql")

                        result_df = duckdb.query(sql_query).df()
                        st.subheader("📋 Query Results")
                        st.dataframe(result_df, use_container_width=True)

                    with col_right:
                        st.subheader("📈 Dynamic Visualization")
                        if len(result_df.columns) >= 2:
                            x_col = result_df.columns[0]
                            y_col = result_df.columns[1]

                            if pd.api.types.is_numeric_dtype(result_df[y_col]):
                                fig = px.bar(
                                    result_df,
                                    x=x_col,
                                    y=y_col,
                                    title=f"{y_col} grouped by {x_col}",
                                    template="plotly_white",
                                    color_discrete_sequence=['#2563EB']
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("ℹ️ Result columns are non-numeric; table view shown.")
                        else:
                            st.info("ℹ️ Single column output; chart not required.")

                except Exception as e:
                    st.error(f"❌ Execution Error: {e}")

else:
    st.info("👈 Upload `sales_data.csv` in the sidebar to get started!")