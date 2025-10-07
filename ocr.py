# ======================================================
# STREAMLIT MULTI-SUPPLIER INVOICE OCR SYSTEM (FOLDER)
# ======================================================

import streamlit as st
import os
import pandas as pd
import pytesseract
import pdfplumber
from pdf2image import convert_from_path
import camelot
import re
import zipfile
from io import BytesIO

# --- PAGE CONFIG ---
st.set_page_config(page_title="Invoice OCR Folder Processor", layout="wide")
st.title("📁 Multi-Supplier Invoice OCR – Folder Upload Version")

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


# --- Extract Data from PDF ---
def extract_invoice_data(pdf_path, supplier="Unknown"):
    all_rows = []

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

    # Try pdfplumber
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

    # Try OCR fallback
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


# --- ZIP Folder Upload ---
uploaded_zip = st.file_uploader(
    "📦 Upload Folder (ZIP file) containing all Supplier Invoices (Subfolders allowed)",
    type=["zip"]
)

if uploaded_zip:
    st.info("Unzipping and scanning for PDF files...")

    # Create temp directory
    temp_dir = "uploaded_invoices"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # Save ZIP locally
    zip_path = os.path.join(temp_dir, "invoices.zip")
    with open(zip_path, "wb") as f:
        f.write(uploaded_zip.read())

    # Extract
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # Find all PDFs (including subfolders)
    pdf_files = []
    for root, _, files in os.walk(temp_dir):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))

    st.write(f"🔍 Found {len(pdf_files)} PDF(s) inside the uploaded folder.")

    # Process each PDF
    if pdf_files:
        all_data = []
        for path in pdf_files:
            supplier_guess = os.path.basename(path).split("_")[0]
            st.write(f"📄 Processing: {os.path.basename(path)}")
            df = extract_invoice_data(path, supplier_guess)
            if not df.empty:
                df["file_name"] = os.path.basename(path)
                all_data.append(df)
            else:
                st.warning(f"No data extracted from {os.path.basename(path)}")

        # Combine results
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            st.success("✅ All Invoices Processed Successfully!")
            st.dataframe(final_df, use_container_width=True)

            # Download as Excel
            output = BytesIO()
            final_df.to_excel(output, index=False)
            st.download_button(
                label="📥 Download Extracted Data (Excel)",
                data=output.getvalue(),
                file_name="Extracted_Invoices_Data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No extractable data found in the uploaded PDFs.")
    else:
        st.error("No PDF files detected in uploaded folder.")
else:
    st.info("Upload a ZIP folder containing all supplier invoices (PDFs).")
