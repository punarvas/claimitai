import io
from typing import List, Dict, Any
import streamlit as st
from openai import OpenAI
import random
import string
import os
from pathlib import Path
import uuid
from prompts.get_rule_prompt import get_rules
from utils import process_document, build_master_information, ai_formatter


def save_uploaded_files(files, session_id: str, base_dir: str = "uploads"):
    saved_paths = []
    # Create session-specific directory
    session_dir = Path(base_dir) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        # Prevent filename collisions
        unique_name = f"{uuid.uuid4()}_{f.name}"
        file_path = session_dir / unique_name
        # Save file to disk
        with open(file_path, "wb") as out_file:
            out_file.write(f.getvalue())
        saved_paths.append(file_path)
    return saved_paths


def upload_json_to_openai(json_path: str) -> str:
    with open(json_path, "rb") as f:
        uploaded_file = client.files.create(
            file=f,
            purpose="user_data",
        )
    return uploaded_file.id


def generate_session_id(length=10):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

# Example usage
session_id = generate_session_id()

st.set_page_config(page_title="Claim My Insurance", page_icon="💬", layout="wide")
st.title("ClaimIt.ai")

client = OpenAI()

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


STARTER_PROMPTS = [
    "Am I eligible for the insurance claim?"
]


def upload_files_to_openai(files) -> List[Dict[str, str]]:
    uploaded = []

    for f in files:
        file_bytes = f.getvalue()
        file_like = io.BytesIO(file_bytes)
        file_like.name = f.name

        result = client.files.create(
            file=file_like,
            purpose="user_data",
        )

        uploaded.append({
            "name": f.name,
            "id": result.id,
        })

    return uploaded


def build_input_items(user_query: str, uploaded_files: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    content = [
        {
            "type": "input_text",
            "text": (
                "Answer the user's question using the uploaded documents as context when relevant. "
                "Respond in plain text only. If the answer is not in the documents, say so clearly.\n\n"
                f"User question: {user_query}"
            ),
        }
    ]

    for item in uploaded_files:
        content.append({
            "type": "input_file",
            "file_id": item["id"],
        })

    return [{"role": "user", "content": content}]


def ask_model(user_query: str, uploaded_files: List[Dict[str, str]]) -> str:
    response = client.responses.create(
        model="gpt-5.4",
        input=build_input_items(user_query, uploaded_files),
        store=False,
    )
    return response.output_text


def run_query(user_query: str):
    st.session_state.chat_history.append({"role": "user", "content": user_query})

    with st.chat_message("user"):
        if user_query[:2] == "*$*":
            st.write(STARTER_PROMPTS[0])
        else:
            st.write(user_query)

    with st.chat_message("assistant"):
        try:
            if not st.session_state.uploaded_files:
                answer = "Please upload at least one document first."
            else:
                with st.spinner("Thinking..."):
                    answer = ask_model(user_query, st.session_state.uploaded_files)

            st.write(answer)
            st.session_state.chat_history.append({"role": "assistant", "content": answer})

        except Exception as e:
            error_text = f"Request failed: {e}"
            st.error(error_text)
            st.session_state.chat_history.append({"role": "assistant", "content": error_text})


# Sidebar upload UI
with st.sidebar:
    st.header("Documents")

    files = st.file_uploader(
        "Upload one or more files",
        accept_multiple_files=True,
        type=["pdf", "txt", "png", "jpeg"],
    )

    if st.button("Upload selected files"):
        if files:
            try:
                with st.spinner("Processing documents..."):
                    saved_paths = save_uploaded_files(files, session_id, base_dir="uploads")
                    save_dir = os.path.join("uploads", session_id)
                    new_saved_paths = process_document(saved_paths, save_dir)
                    json_path = build_master_information(new_saved_paths, save_dir, session_id)
                    json_path = ai_formatter(json_path)

                    hidden_state_file_id = upload_json_to_openai(json_path)
                    #st.write("Uploaded hidden_state.json file id:", hidden_state_file_id)

                st.session_state.uploaded_files = [{
                    "id": hidden_state_file_id,
                    "name": "hidden_state.json"
                }]
                st.success(f"Updated {len(new_saved_paths)} uploaded file(s).")
            except Exception as e:
                st.error(f"Upload failed: {e}")
        else:
            st.warning("Please choose at least one file.")

    if st.button("Clear uploaded files"):
        st.session_state.uploaded_files = []
        st.success("Cleared uploaded file list.")

# Show chat history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Starter prompts
st.subheader("Hey, how can I help you today?")

cols = st.columns(2)
for i, prompt in enumerate(STARTER_PROMPTS):
    with cols[i % 2]:
        if st.button(prompt, key=f"starter_{i}"):
            st.session_state.pending_prompt = get_rules()

# Free-form chat input
typed_prompt = st.chat_input("Ask a question about the uploaded documents...")

# Prefer clicked starter prompt, otherwise typed prompt
prompt_to_run = st.session_state.pending_prompt or typed_prompt

if prompt_to_run:
    run_query(prompt_to_run)
    st.session_state.pending_prompt = None
