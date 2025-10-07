#!/bin/bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils ghostscript
pip install -r requirements.txt
echo "✅ System ready for OCR extraction!"
