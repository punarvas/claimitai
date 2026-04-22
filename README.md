# 📄 ClaimIt.ai

A Streamlit app that evaluates insurance claim eligibility using OCR + LLM reasoning over uploaded documents. 

---
## 🧠 Approach & Architecture

**Flow:**
1. Upload documents  
2. Extract text from PDFs and image files (requires OCR if PNG file)  
3. Normalize and combine all extracted information into JSON  
4. Use GPT 4o-mini to build a LLM context for insurance claim using pre-defined format.
5. Upload the LLM context to the webapp for the decision-making LLM to process the verdict (complete/incomplete/needs review)

**Architecture (bullet view):**
- Streamlit UI handles user interaction and file uploads  
- Document processing layer performs:
  - OCR (for scanned/image files), based on GPU-based PaddleOCR instance.
  - Text extraction and parsing (simple JSON)
- Data is normalized into structured JSON  
- LLM layer (OpenAI API):
  - Receives user query + document context  
  - Generates grounded response  
- Response is displayed in the chat UI  

**Separation:**
- `app.py`: UI + LLM interaction  
- `utils.py`: OCR, parsing, formatting
- **Python**: 3.10.11

---

## ⚖️ Key Decisions & Tradeoffs

1. I initially thought of using **RAG-based solution**, but felt that it is on overkill for a clearly-defined problem.
2. Many LLM-based open-source tools can process PDFs, but not PNGs. So, I incorporated a OCR-based solution that can process both, PDF and PNG, within single API.
3. Instead of letting the model to wander across the raw information, I decided to build a template (stored inside `prompts`) that LLM can complete using raw information. This will limit the context and output capabilities.
4. Streamlit is the most versatile and easy-to-create UIs. I took a starter template from ChatGPT and built on top of it to add document processing, context generation, and predefined-prompts layers.

---

## 🛠️ Tool Design

- `process_document`: Extracts + structures content  
- `build_master_information`: Combines multiple docs  
- `ai_formatter`: Converts raw data → structured output  
- `ask_model`: Queries LLM with attached files  

---

## 🚀 With More Time

- Standardize this "workflow" into a fundamental RAG-based solution that offers tool scalability and eliminates hardwired decision-making to a certain degree.
- Improve OCR runtime performance for tables and more complex, obsucred document scans (current performance: ~150 seconds for four PNG files)
- Show citations in responses to make it clear from where the LLM landed to the decision.
- Improve the prompts for the LLM in more structured way in order to use raw text input and not processed context.

---