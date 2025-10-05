import streamlit as st
import sqlite3
import json

# ---------------------------
# Database Connection
# ---------------------------
DB_FILE = "empathy2.db"  # update if path differs

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

# ---------------------------
# Fetch Data Functions
# ---------------------------
def get_passages():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, text FROM passages")
    passages = cur.fetchall()
    conn.close()
    return passages

def get_questions(passage_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, text FROM questions WHERE passage_id = ?", (passage_id,))
    questions = cur.fetchall()
    conn.close()
    return questions

def get_options(question_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, label, weight FROM options WHERE question_id = ?", (question_id,))
    options = cur.fetchall()
    conn.close()
    return options

def save_response(passage_id, user_name, score, empathy_level, answers_json):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO responses (passage_id, user_name, score, empathy_level, answers_json)
        VALUES (?, ?, ?, ?, ?)
    """, (passage_id, user_name, score, empathy_level, answers_json))
    conn.commit()
    conn.close()

# ---------------------------
# Empathy Level Logic
# ---------------------------
def get_empathy_level(score):
    if score < 6:
        return "Low Empathy 😐"
    elif score <= 10:
        return "Moderate Empathy 🙂"
    else:
        return "High Empathy 💖"

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="Empathy Analysis", layout="centered")
st.title("🧠 Empathy Analysis Application")

user_name = st.text_input("Enter your name:")

passages = get_passages()

if not passages:
    st.error("⚠️ No passages found in the database.")
else:
    passage_titles = [p[1] for p in passages]
    selected_title = st.selectbox("Choose a Passage:", passage_titles)

    # Get passage details
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

            if not options:
                st.warning("No options found for this question.")
                continue

            option_labels = [o[1] for o in options]
            selected_option = st.radio("", option_labels, key=f"q_{q_id}")

            # Get weight of selected option
            selected_weight = next(o[2] for o in options if o[1] == selected_option)
            score += selected_weight
            answers[q_text] = selected_option

            st.markdown("---")

        if st.button("Submit Responses"):
            empathy_level = get_empathy_level(score)
            answers_json = json.dumps(answers)

            save_response(passage_id, user_name, score, empathy_level, answers_json)

            st.success("✅ Response saved successfully!")
            st.metric("Your Empathy Score", score)
            st.metric("Empathy Level", empathy_level)
