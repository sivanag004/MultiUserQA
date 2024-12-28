from flask import Flask, render_template, request, session, redirect, url_for
import os
import json
from utils import search
import secrets
secret_key = secrets.token_hex(16)
print(secret_key)

app = Flask(__name__)
app.secret_key = secret_key

# Paths
DOCUMENTS_DIR = "documents"
METADATA_PATH = "embeddings/metadata.json"
INDEX_PATH = "embeddings/faiss_index"
USER_DATA_PATH = "user_data.json"

# Load user data
with open(USER_DATA_PATH, "r") as f:
    USER_DATA = json.load(f)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        if email in USER_DATA:
            session["email"] = email
            return redirect(url_for("query"))
        return "Unauthorized email address.", 401
    return render_template("login.html")

@app.route("/query", methods=["GET", "POST"])
def query():
    if "email" not in session:
        return redirect(url_for("login"))

    email = session["email"]
    user_files = USER_DATA[email]
    context = session.get("context", "")
    # print(f"Authorized Files for {email} : {user_files}")
    if request.method == "POST":
        query_text = request.form["query"]
        full_query = context + " " + query_text if context else query_text
        results = search(full_query, INDEX_PATH, METADATA_PATH, user_files)
        # context = " ".join([res["content"][:200] for res in results])  # Limited excerpt
        context += " " + query_text + " " + " ".join([res["content"][:200] for res in results])
        session["context"] = context
        unique_results = []
        seen = set()
        for res in results:
            if res["content"] not in seen:
                unique_results.append(res)
                seen.add(res["content"])
        return render_template("query.html", results=unique_results, context=context,username=email)

    return render_template("query.html", results=[], context=context,username=email)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
