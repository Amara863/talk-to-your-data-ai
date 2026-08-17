import os
import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
from groq import Groq
import re

# =========================================================
# 🚀 Universal AI Text-to-SQL Engine (Dynamic Live Groq Model)
# =========================================================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))


def generate_sql(user_query, df):
    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY missing! Please configure it in Streamlit Secrets.")

    client = Groq(api_key=GROQ_API_KEY)

    # 1. Fetch exact active models directly from your Groq account
    active_models = [
        m.id for m in client.models.list().data
        if not any(x in m.id.lower() for x in ["whisper", "guard", "embed", "vision", "decommissioned"])
    ]

    # Prioritize fastest lightweight text model (e.g. 8b / llama / mixtral)
    chosen_model = next((m for m in active_models if "8b" in m.lower()), active_models[0])

    # 2. Extract schema dynamically from ANY dataset
    schema_details = []
    for col in df.columns:
        samples = df[col].dropna().unique()[:3].tolist()
        schema_details.append(f"- Column: '{col}' (Type: {df[col].dtype}, Samples: {samples})")

    schema_text = "\n".join(schema_details)

    system_prompt = f"""You are an expert DuckDB SQL engineer.
The dataset is loaded in memory under table name 'df'.

Dataset Schema:
{schema_text}

Task:
Generate a strictly valid DuckDB SQL query to answer the user's question accurately.

Rules:
1. Return ONLY the raw SQL query.
2. NEVER use markdown code fences (no ```sql or ```).
3. NEVER write explanations or notes.
4. Use ILIKE or LOWER() for flexible text matching.
5. If column names have spaces, enclose them in double quotes.
"""

    response = client.chat.completions.create(
        model=chosen_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User question: {user_query}"}
        ],
        temperature=0.0
    )

    raw_sql = response.choices[0].message.content.strip()
    cleaned_sql = re.sub(r"^```(?:sql)?|```$", "", raw_sql, flags=re.MULTILINE).strip()
    return cleaned_sql


# =========================================================
# 🎨 Streamlit Web UI
# =========================================================
st.set_page_config(
    page_title="Universal Text-to-SQL Analytics",
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
st.write("Upload **any CSV file**, ask questions in plain English, and get instant SQL execution with dynamic charts.")

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
                               placeholder="e.g., attendance for rahul / highest marks / total sales by region")

    if user_query:
        with st.spinner("🤖 Executing query..."):
            try:
                sql_query = generate_sql(user_query, df)

                col_left, col_right = st.columns([1, 1])

                with col_left:
                    st.subheader("🔍 Generated SQL Query")
                    st.code(sql_query, language="sql")

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
                        st.info("ℹ️ Result is displayed in the table on the left.")

            except Exception as e:
                st.error(f"❌ Execution Error: {e}")
else:
    st.info("👈 Upload any CSV file in the sidebar to get started!")