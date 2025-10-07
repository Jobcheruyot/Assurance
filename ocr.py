import streamlit as st
import os
import tempfile
import pytesseract
from pdf2image import convert_from_path
import pdfplumber
import pandas as pd
from PIL import Image

# ============ STREAMLIT UI ============ #
st.set_page_config(page_title="Invoice OCR Extractor", layout="wide")
st.title("🧾 Multi-PDF Invoice OCR Extractor")
st.markdown("Upload a **folder (or multiple PDFs)**. The app will scan all subfolders for PDFs, extract text and items, and export results to Excel.")

# ============ FILE UPLOAD ============ #
uploaded_files = st.file_uploader(
    "📂 Upload all your PDF files (drag & drop from a folder)",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    # Create a temporary folder to store uploaded PDFs
    temp_dir = tempfile.mkdtemp()
    pdf_paths = []

    # Save all uploaded PDFs to temp directory
    for uploaded_file in uploaded_files:
        file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
        pdf_paths.append(file_path)

    st.success(f"✅ {len(pdf_paths)} PDF file(s) uploaded successfully!")

    # ============ PROCESSING ============ #
    progress = st.progress(0)
    extracted_data = []

    for idx, pdf_file in enumerate(pdf_paths):
        st.write(f"🔍 Processing: {os.path.basename(pdf_file)}")
        try:
            # Extract text using pdfplumber first (structured text)
            with pdfplumber.open(pdf_file) as pdf:
                all_text = ""
                for page in pdf.pages:
                    all_text += page.extract_text() or ""

            # If pdfplumber fails or text is empty, fallback to OCR
            if not all_text.strip():
                st.warning(f"No extractable text in {os.path.basename(pdf_file)} — switching to OCR...")
                images = convert_from_path(pdf_file)
                for image in images:
                    text = pytesseract.image_to_string(image)
                    all_text += text

            # Simple line splitting logic
            lines = [line.strip() for line in all_text.split("\n") if line.strip()]

            # Try to extract item-like lines
            for line in lines:
                if any(char.isdigit() for char in line):  # crude way to find item lines
                    extracted_data.append({
                        "File": os.path.basename(pdf_file),
                        "Line": line
                    })

        except Exception as e:
            st.error(f"Error processing {os.path.basename(pdf_file)}: {e}")

        progress.progress((idx + 1) / len(pdf_paths))

    # ============ EXPORT RESULTS ============ #
    if extracted_data:
        df = pd.DataFrame(extracted_data)
        st.subheader("📊 Extracted Invoice Data")
        st.dataframe(df.head(50))

        # Export to Excel
        output_path = os.path.join(temp_dir, "Extracted_Invoices.xlsx")
        df.to_excel(output_path, index=False)

        with open(output_path, "rb") as f:
            st.download_button(
                label="⬇️ Download Extracted Excel File",
                data=f,
                file_name="Extracted_Invoices.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        st.success("✅ Extraction Complete! Download your Excel file above.")
    else:
        st.warning("⚠️ No valid data found in uploaded PDFs.")
else:
    st.info("👆 Upload PDF files from your folders to begin.")
