<div align="center">

# 🤖 AI Agents

**Building Intelligent Agents for Modern Platforms**

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-success.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)]()

</div>

---

### 📌 Overview

This repository contains practical AI Agents that you can run and use.

Currently available:

### ✅ Personal Assistant Agent (`مُعين`)

A smart personal assistant that:
- Speaks **Arabic** and **English**
- Helps with daily tasks, organizing thoughts, and summarization
- Supports interactive **chat** interface
- Prepared for future **voice messages** support

---

### 🚀 How to Run the Personal Assistant

```bash
# 1. Clone the repository
git clone https://github.com/milou311/ai-agents.git
cd ai-agents

# 2. Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file and add your OpenAI API key
echo OPENAI_API_KEY=sk-your-key-here > .env

# 5. Run the assistant
python main.py
```

---

### 💬 How to use

After running `python main.py`:

- Write your message in Arabic or English
- Type `/reset` to clear conversation history
- Type `/exit` to quit

---

### 🗂️ Current Project Structure

```text
ai-agents/
├── agents/
│   ├── personal_assistant.py   # Main assistant logic
│   ├── voice_interface.py      # Voice support (coming soon)
│   └── __init__.py
├── main.py                     # Entry point
├── requirements.txt
├── .gitignore
└── README.md
```

---

### 🛠️ Roadmap

| Feature                        | Status          |
|--------------------------------|-----------------|
| Text Chat Interface            | ✅ Ready        |
| Arabic + English support       | ✅ Ready        |
| Conversation memory            | ✅ Ready        |
| Voice messages (STT + TTS)     | 🚧 In progress  |
| Tool calling (search, etc.)    | ⏳ Planned      |
| Multi-agent collaboration      | ⏳ Planned      |

---

### 📄 License

MIT License

---

<div align="center">
  Built with ❤️ by <a href="https://github.com/milou311">Mohamed Miloud</a>
</div>
