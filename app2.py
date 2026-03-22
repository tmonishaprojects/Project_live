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
# FETCH FUNCTIONS
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
    cur.execute("SELECT id, label, weight FROM options WHERE question_id=?", (question_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

# =====================================================
# CREATE FUNCTIONS
# =====================================================
def add_passage(title, text):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO passages (title, text) VALUES (?, ?)", (title, text))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid

def add_question(passage_id, text):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO questions (passage_id, text) VALUES (?, ?)", (passage_id, text))
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
# UPDATE FUNCTIONS
# =====================================================
def update_passage(passage_id, title, text):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE passages SET title=?, text=? WHERE id=?", (title, text, passage_id))
    conn.commit()
    conn.close()

def update_question(question_id, text):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE questions SET text=? WHERE id=?", (text, question_id))
    conn.commit()
    conn.close()

def update_option(option_id, label, weight):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE options SET label=?, weight=? WHERE id=?", (label, weight, option_id))
    conn.commit()
    conn.close()

# =====================================================
# DELETE FUNCTIONS
# =====================================================
def delete_passage(passage_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM options WHERE question_id IN (SELECT id FROM questions WHERE passage_id=?)", (passage_id,))
    cur.execute("DELETE FROM questions WHERE passage_id=?", (passage_id,))
    cur.execute("DELETE FROM responses WHERE passage_id=?", (passage_id,))
    cur.execute("DELETE FROM passages WHERE id=?", (passage_id,))
    conn.commit()
    conn.close()

def delete_question(question_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM options WHERE question_id=?", (question_id,))
    cur.execute("DELETE FROM questions WHERE id=?", (question_id,))
    conn.commit()
    conn.close()

def delete_option(option_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM options WHERE id=?", (option_id,))
    conn.commit()
    conn.close()

# =====================================================
# NLP Question Generator
# =====================================================
def generate_questions_from_passage(passage_text):
    words = re.findall(r'\b[A-Za-z]{4,}\b', passage_text)
    focus = words[0] if words else "the person"

    return [
        f"How would you emotionally respond to {focus}?",
        "What would be your immediate action?",
        "How would you communicate empathetically?",
        "What support would you offer?",
        "How would you handle similar situations?"
    ]

# =====================================================
# Empathy Logic
# =====================================================
def get_empathy_level(score):
    if score < 6:
        return "Low Empathy 😐"
    elif score <= 10:
        return "Moderate Empathy 🙂"
    else:
        return "High Empathy 💖"

# =====================================================
# STREAMLIT UI
# =====================================================
st.set_page_config(page_title="Empathy Analysis", layout="centered")

st.sidebar.title("⚙️ Control Panel")
mode = st.sidebar.radio("Select Mode", ["User", "Admin"])

# =====================================================
# ADMIN MODE
# =====================================================
if mode == "Admin":
    st.title("🏢 Admin Panel")

    # -------------------------------
    # EDIT / DELETE PASSAGE
    # -------------------------------
    st.subheader("✏️ Edit / Delete Passage")

    passages = get_passages()

    if passages:
        passage_dict = {p[1]: p for p in passages}
        selected_title = st.selectbox("Select Passage", list(passage_dict.keys()))

        pid, title, text = passage_dict[selected_title]

        new_title = st.text_input("Edit Title", title)
        new_text = st.text_area("Edit Text", text)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Update Passage"):
                update_passage(pid, new_title, new_text)
                st.success("Updated!")

        with col2:
            if st.button("Delete Passage"):
                delete_passage(pid)
                st.warning("Deleted!")
                st.experimental_rerun()

        # -------------------------------
        # QUESTIONS
        # -------------------------------
        st.subheader("📝 Manage Questions")

        questions = get_questions(pid)

        for q_id, q_text in questions:
            st.write(f"QID: {q_id}")
            new_q = st.text_input(f"Edit Q{q_id}", q_text)

            col1, col2 = st.columns(2)

            with col1:
                if st.button(f"Update Q{q_id}"):
                    update_question(q_id, new_q)

            with col2:
                if st.button(f"Delete Q{q_id}"):
                    delete_question(q_id)
                    st.experimental_rerun()

            options = get_options(q_id)

            for opt_id, label, weight in options:
                col1, col2, col3 = st.columns([4, 2, 1])

                with col1:
                    new_label = st.text_input(f"Opt {opt_id}", label)

                with col2:
                    new_weight = st.selectbox(
                        "Weight",
                        [1,2,3,4,5],
                        index=weight-1,
                        key=f"w_{opt_id}"
                    )

                with col3:
                    if st.button("❌", key=f"d_{opt_id}"):
                        delete_option(opt_id)
                        st.experimental_rerun()

                if st.button(f"Update Opt {opt_id}"):
                    update_option(opt_id, new_label, new_weight)

            st.markdown("---")

    # -------------------------------
    # CREATE NEW PASSAGE
    # -------------------------------
    st.subheader("➕ Add New Passage")

    title = st.text_input("Title")
    text = st.text_area("Passage")

    if st.button("Generate Questions"):
        st.session_state.questions = generate_questions_from_passage(text)

    questions = st.session_state.get("questions", [])

    blocks = []

    for i, q in enumerate(questions):
        q_text = st.text_input(f"Q{i+1}", q)
        opts = []

        for j in range(5):
            opt = st.text_input(f"Option {j+1} Q{i+1}")
            weight = st.selectbox("Weight", [1,2,3,4,5], key=f"{i}{j}")
            opts.append((opt, weight))

        blocks.append((q_text, opts))

    if st.button("Save New Passage"):
        pid = add_passage(title, text)

        for q, opts in blocks:
            qid = add_question(pid, q)
            add_options(qid, opts)

        st.success("Saved!")

# =====================================================
# USER MODE
# =====================================================
if mode == "User":
    st.title("🧠 Empathy Analysis")

    name = st.text_input("Your Name")

    passages = get_passages()

    if passages:
        titles = [p[1] for p in passages]
        selected = st.selectbox("Choose Passage", titles)

        p = next(x for x in passages if x[1] == selected)
        pid = p[0]

        st.subheader(p[1])
        st.write(p[2])

        questions = get_questions(pid)

        score = 0
        answers = {}

        for q_id, q_text in questions:
            st.write(q_text)
            options = get_options(q_id)

            labels = [o[1] for o in options]
            choice = st.radio("", labels, key=q_id)

            weight = next(o[2] for o in options if o[1] == choice)
            score += weight
            answers[q_text] = choice

        if st.button("Submit"):
            level = get_empathy_level(score)
            save_response(pid, name, score, level, json.dumps(answers))

            st.success("Saved!")
            st.metric("Score", score)
            st.metric("Level", level)