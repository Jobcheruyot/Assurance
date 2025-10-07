# ============================================
# STREAMLIT MULTI-SUPPLIER INVOICE OCR SYSTEM
# ============================================

import streamlit as st
import os
import pandas as pd
import pytesseract
import pdfplumber
from pdf2image import convert_from_path
import camelot
import re
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Invoice OCR System", layout="wide")
st.title("📄 Multi-Supplier Invoice OCR & Data Extractor")

# --- Column Name Library ---
column_library = {
    "invoice_no": ["invoice no", "inv no", "invoice number", "inv#", "bill no"],
    "date": ["date", "invoice date", "bill date"],
    "supplier": ["supplier", "vendor", "company"],
    "item": ["item", "description", "product", "goods"],
    "qty": ["qty", "quantity", "pcs", "no.", "units"],
    "price": ["price", "unit price", "unit cost", "rate", "cost"],
    "total": ["total", "amount", "value", "line total"],
    "vat": ["vat", "tax", "vat amount"]
}

def normalize_columns(df, column_library):
    rename_map = {}
    for std_col, variants in column_library.items():
        for col in df.columns:
            col_clean = col.lower().strip()
            if any(col_clean.startswith(v.lower()) for v in variants):
                rename_map[col] = std_col
    df = df.rename(columns=rename_map)
    return df

# --- Extraction Logic ---
def extract_invoice_data(pdf_file, supplier="Unknown"):
    all_rows = []

    # Save temporarily
    with open("temp_invoice.pdf", "wb") as f:
        f.write(pdf_file.read())

    pdf_path = "temp_invoice.pdf"

    # Try Camelot
    try:
        tables = camelot.read_pdf(pdf_path, pages='all')
        if tables:
            for t in tables:
                df = t.df
                df.columns = df.iloc[0]
                df = df.drop(0)
                df = normalize_columns(df, column_library)
                df["supplier"] = supplier
                all_rows.append(df)
    except Exception as e:
        print("Camelot error:", e)

    # pdfplumber fallback
    if not all_rows:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        df = pd.DataFrame(table[1:], columns=table[0])
                        df = normalize_columns(df, column_library)
                        df["supplier"] = supplier
                        all_rows.append(df)
        except Exception as e:
            print("pdfplumber error:", e)

    # OCR fallback
    if not all_rows:
        try:
            images = convert_from_path(pdf_path)
            text = ""
            for img in images:
                text += pytesseract.image_to_string(img)
            items = re.findall(r"([A-Za-z].+?)\s+(\d+)\s+([\d.,]+)\s+([\d.,]+)", text)
            if items:
                df = pd.DataFrame(items, columns=["item", "qty", "price", "total"])
                df["supplier"] = supplier
                all_rows.append(df)
        except Exception as e:
            print("OCR error:", e)

    if all_rows:
        return pd.concat(all_rows, ignore_index=True)
    else:
        return pd.DataFrame()

# --- Streamlit UI ---
uploaded_files = st.file_uploader(
    "📂 Upload All PDF Invoices (Multiple Selection Allowed)",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    st.info(f"Processing {len(uploaded_files)} PDF(s)... This may take a moment.")
    all_data = []

    for pdf_file in uploaded_files:
        supplier_guess = pdf_file.name.split("_")[0] if "_" in pdf_file.name else "Unknown"
        st.write(f"🔹 Processing: {pdf_file.name}")
        df = extract_invoice_data(pdf_file, supplier_guess)
        if not df.empty:
            df["file_name"] = pdf_file.name
            all_data.append(df)
        else:
            st.warning(f"No data extracted from {pdf_file.name}")

    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        st.success("✅ Extraction Completed!")
        st.dataframe(full_df, use_container_width=True)

        # Download as Excel
        output = BytesIO()
        full_df.to_excel(output, index=False)
        st.download_button(
            label="📥 Download Extracted Data (Excel)",
            data=output.getvalue(),
            file_name="Invoice_Extracted_Data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("No valid invoice data found in the uploaded PDFs.")
else:
    st.info("Upload one or more PDF invoices to begin processing.")
