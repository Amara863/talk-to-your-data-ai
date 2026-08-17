import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import requests
import re

# =========================================================
# 🚀 Dynamic AI SQL Engine (Accurate Zero-Key Inference)
# =========================================================
def generate_sql_free(prompt_text, df):
    columns_info = ", ".join([f"{col} ({dtype})" for col, dtype in zip(df.columns, df.dtypes)])
    sample_data = df.head(3).to_string(index=False)

    system_prompt = f"""You are an expert DuckDB SQL engineer.
Table Name: strictly 'df'
Columns & Data Types: {columns_info}

Sample Rows:
{sample_data}

Instructions:
1. Translate the user query into a strictly valid DuckDB SQL query.
2. If the user asks for a specific filter (e.g., specific Category like 'Electronics', or Region like 'North'), use a WHERE clause (e.g. WHERE LOWER(Category) = 'electronics').
3. If grouping is requested or implied with aggregations, include appropriate GROUP BY.
4. Output ONLY the raw SQL query. Do not wrap in markdown (no ```sql or ```), do not add comments or explanations."""

    url = "https://text.pollinations.ai/"
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate DuckDB SQL for: {prompt_text}"}
        ],
        "model": "mistral",
        "seed": 42
    }

    try:
        res = requests.post(url, json=payload, timeout=12)
        if res.status_code == 200:
            cleaned = res.text.strip()
            cleaned = re.sub(r"^```(?:sql)?|```$", "", cleaned, flags=re.MULTILINE).strip()
            # Extract only SELECT statement if extra text returned
            select_match = re.search(r"(SELECT\s+.*)", cleaned, re.IGNORECASE | re.DOTALL)
            if select_match:
                return select_match.group(1).rstrip(";")
    except Exception:
        pass

    # Safe dynamic fallback if network drops
    return f"SELECT * FROM df WHERE LOWER(Category) LIKE '%{prompt_text.lower().split()[-1]}%' LIMIT 10"

# Page Setup & Styling
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

    st.divider()

    user_query = st.text_input("💬 Ask a question about this data:", placeholder="e.g., Show sales in Electronics category")

    if user_query:
        with st.spinner("🤖 Translating natural language to DuckDB SQL..."):
            try:
                sql_query = generate_sql_free(user_query, df)

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
                        st.info("ℹ️ Single metric/column output; table view shown above.")

            except Exception as e:
                st.error(f"❌ Execution Error: {e}")
else:
    st.info("👈 Upload `sales_data.csv` in the sidebar to get started!")