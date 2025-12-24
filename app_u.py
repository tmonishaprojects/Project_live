import streamlit as st
import sqlite3
import json
import re

# =====================================================
# Database Connection
# =====================================================
DB_FILE = "empathy2.db"

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

# =====================================================
# Fetch Data Functions (USER)
# =====================================================
def get_passages():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, text FROM passages")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_questions(passage_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, text FROM questions WHERE passage_id=?", (passage_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_options(question_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, label, weight FROM options WHERE question_id=?",
        (question_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def save_response(passage_id, user_name, score, empathy_level, answers_json):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO responses (passage_id, user_name, score, empathy_level, answers_json)
        VALUES (?, ?, ?, ?, ?)
    """, (passage_id, user_name, score, empathy_level, answers_json))
    conn.commit()
    conn.close()

# =====================================================
# Admin Insert Functions
# =====================================================
def add_passage(title, text):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO passages (title, text) VALUES (?, ?)",
        (title, text)
    )
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid

def add_question(passage_id, text):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO questions (passage_id, text) VALUES (?, ?)",
        (passage_id, text)
    )
    conn.commit()
    qid = cur.lastrowid
    conn.close()
    return qid

def add_options(question_id, options):
    conn = get_connection()
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO options (question_id, label, weight) VALUES (?, ?, ?)",
        [(question_id, opt, weight) for opt, weight in options]
    )
    conn.commit()
    conn.close()

# =====================================================
# NLP: Question Generator (Rule-based, Explainable)
# =====================================================
def generate_questions_from_passage(passage_text):
    words = re.findall(r'\b[A-Za-z]{4,}\b', passage_text)
    focus = words[0] if words else "the person"

    return [
        f"How would you emotionally respond to {focus} in this situation?",
        "What would be your immediate action after understanding the situation?",
        "How would you communicate with the person involved empathetically?",
        "What kind of support would you offer considering the circumstances?",
        "How would you handle similar situations in the future?"
    ]

# =====================================================
# Empathy Level Logic
# =====================================================
def get_empathy_level(score):
    if score < 6:
        return "Low Empathy 😐"
    elif score <= 10:
        return "Moderate Empathy 🙂"
    else:
        return "High Empathy 💖"

# =====================================================
# Streamlit Config
# =====================================================
st.set_page_config(page_title="Empathy Analysis", layout="centered")

# =====================================================
# Sidebar Mode Selector
# =====================================================
st.sidebar.title("⚙️ Control Panel")
mode = st.sidebar.radio("Select Mode", ["User", "Company / Admin"])

# =====================================================
# COMPANY / ADMIN MODE
# =====================================================
if mode == "Company / Admin":
    st.title("🏢 Company Admin – Add Empathy Passage")

    passage_title = st.text_input("Passage Title")
    passage_text = st.text_area("Passage Description (Situation)")

    if st.button("🧠 Generate 5 Questions using NLP"):
        if not passage_text:
            st.warning("Please enter passage text first.")
        else:
            st.session_state.questions = generate_questions_from_passage(passage_text)

    questions = st.session_state.get("questions", [])

    question_blocks = []

    for i, q in enumerate(questions):
        st.subheader(f"Question {i+1}")
        q_text = st.text_input(f"Edit Question {i+1}", q)

        options = []
        for j in range(5):
            col1, col2 = st.columns([4, 1])
            with col1:
                opt_text = st.text_input(f"Option {j+1} (Q{i+1})")
            with col2:
                weight = st.selectbox(
                    "Weight",
                    [1, 2, 3, 4, 5],
                    key=f"w_{i}_{j}"
                )
            options.append((opt_text, weight))

        question_blocks.append((q_text, options))
        st.markdown("---")

    if st.button("💾 Save Passage & Questionnaire"):
        if not passage_title or not passage_text:
            st.error("Passage title and text are required.")
        else:
            pid = add_passage(passage_title, passage_text)

            for q_text, opts in question_blocks:
                qid = add_question(pid, q_text)
                add_options(qid, opts)

            st.success("✅ Passage, questions, and options saved successfully!")
            st.info("Switch to User mode to view the new passage.")

# =====================================================
# USER MODE (YOUR ORIGINAL LOGIC – UNCHANGED)
# =====================================================
if mode == "User":
    st.title("🧠 Empathy Analysis Application")

    user_name = st.text_input("Enter your name:")

    passages = get_passages()

    if not passages:
        st.error("⚠️ No passages found in the database.")
    else:
        passage_titles = [p[1] for p in passages]
        selected_title = st.selectbox("Choose a Passage:", passage_titles)

        selected_passage = next(p for p in passages if p[1] == selected_title)
        passage_id = selected_passage[0]

        st.subheader(f"📖 {selected_passage[1]}")
        st.write(selected_passage[2])

        questions = get_questions(passage_id)

        if not questions:
            st.warning("No questions found for this passage.")
        else:
            st.markdown("---")
            st.subheader("📝 Questionnaire")

            answers = {}
            score = 0

            for q_id, q_text in questions:
                st.write(f"**{q_text}**")
                options = get_options(q_id)

                labels = [o[1] for o in options]
                selected_option = st.radio("", labels, key=f"q_{q_id}")

                weight = next(o[2] for o in options if o[1] == selected_option)
                score += weight
                answers[q_text] = selected_option

                st.markdown("---")

            if st.button("Submit Responses"):
                if not user_name:
                    st.error("Please enter your name.")
                else:
                    empathy_level = get_empathy_level(score)
                    answers_json = json.dumps(answers)

                    save_response(
                        passage_id,
                        user_name,
                        score,
                        empathy_level,
                        answers_json
                    )

                    st.success("✅ Response saved successfully!")
                    st.metric("Your Empathy Score", score)
                    st.metric("Empathy Level", empathy_level)
