import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import requests
import json
import re


# =========================================================
# 🤖 True Universal Schema-to-SQL Engine (No Hardcoding)
# =========================================================
def generate_sql_universal(user_query, df):
    # 1. Dynamically extract schema and sample from ANY uploaded CSV
    schema_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        sample_vals = df[col].dropna().unique()[:3].tolist()
        schema_info.append(f"Column: '{col}' | Type: {dtype} | Sample values: {sample_vals}")

    schema_str = "\n".join(schema_info)

    # 2. System Prompt instructing LLM to strictly reason over DuckDB SQL
    system_prompt = f"""You are an expert DuckDB SQL analyst.
The table is already loaded in memory with the exact table name 'df'.

Schema & Sample Data:
{schema_str}

User Question: "{user_query}"

Rules:
1. Return ONLY the executable DuckDB SQL query.
2. Do NOT wrap the query in markdown (no ```sql or ```).
3. Do NOT add any conversational text, notes, or explanations.
4. Use case-insensitive matching where appropriate (e.g., LOWER(column) = 'value' or ILIKE).
5. Ensure column names with spaces or special characters are enclosed in double quotes if necessary.
"""

    # 3. Open Inference API (Mistral / Qwen / Llama engine)
    url = "https://text.pollinations.ai/"
    payload = {
        "messages": [
            {"role": "system",
             "content": "You are a specialized SQL generation model that only outputs raw DuckDB SQL queries without markdown or explanation."},
            {"role": "user", "content": system_prompt}
        ],
        "model": "mistral",
        "temperature": 0.1
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers, timeout=15)

    if response.status_code != 200:
        raise Exception(f"AI Service unavailable (Status {response.status_code}). Please try again.")

    raw_text = response.text.strip()

    # 4. Clean formatting / backticks
    cleaned_sql = re.sub(r"^```(?:sql)?|```$", "", raw_text, flags=re.MULTILINE).strip()

    # Extract only the SELECT statement
    match = re.search(r"(SELECT\s+.*)", cleaned_sql, re.IGNORECASE | re.DOTALL)
    if match:
        cleaned_sql = match.group(1).rstrip(";").strip()

    return cleaned_sql


# =========================================================
# 🎨 Streamlit Interface
# =========================================================
st.set_page_config(
    page_title="Universal Talk to Your Data | Text-to-SQL",
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

st.title("📊 Universal Text-to-SQL Analytics Engine")
st.write(
    "Upload **any** CSV dataset (Library, Sales, Students, Healthcare, etc.), ask any analytical question, and get automatic SQL execution with dynamic visual charts.")

# Sidebar File Ingestion
st.sidebar.header("📁 Data Ingestion")
uploaded_file = st.sidebar.file_uploader("Upload Any CSV Dataset", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.sidebar.success(f"Loaded {len(df)} rows & {len(df.columns)} columns!")

    with st.expander("👀 View Raw Dataset Preview", expanded=False):
        st.dataframe(df.head(10), use_container_width=True)

    st.divider()

    user_query = st.text_input("💬 Ask a question about this data:",
                               placeholder="e.g., Find top 5 most borrowed books by genre")

    if user_query:
        with st.spinner("🤖 Analyzing schema and generating SQL query..."):
            try:
                # Generate dynamic SQL
                sql_query = generate_sql_universal(user_query, df)

                col_left, col_right = st.columns([1, 1])

                with col_left:
                    st.subheader("🔍 Generated SQL Query")
                    st.code(sql_query, language="sql")

                    # Execute with DuckDB
                    result_df = duckdb.query(sql_query).df()
                    st.subheader("📋 Query Results")
                    st.dataframe(result_df, use_container_width=True)

                with col_right:
                    st.subheader("📈 Dynamic Visualization")
                    numeric_cols = [c for c in result_df.columns if pd.api.types.is_numeric_dtype(result_df[c])]
                    non_numeric_cols = [c for c in result_df.columns if not pd.api.types.is_numeric_dtype(result_df[c])]

                    if numeric_cols and non_numeric_cols:
                        fig = px.bar(
                            result_df,
                            x=non_numeric_cols[0],
                            y=numeric_cols[0],
                            title=f"{numeric_cols[0]} by {non_numeric_cols[0]}",
                            template="plotly_white",
                            color_discrete_sequence=['#2563EB']
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    elif len(numeric_cols) >= 2:
                        fig = px.bar(
                            result_df,
                            x=numeric_cols[0],
                            y=numeric_cols[1],
                            template="plotly_white",
                            color_discrete_sequence=['#2563EB']
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("ℹ️ Scalar output; tabular view rendered on the left.")

            except Exception as e:
                st.error(f"❌ Execution Error: {e}")
else:
    st.info("👈 Upload any CSV file in the sidebar to get started!")