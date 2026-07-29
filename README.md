<div align="center">

# 🤖 AI Agents — مُعين

**وكيل ذكاء اصطناعي متقدم عبر بوت تليجرام**

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)]()
[![Status](https://img.shields.io/badge/Status-Active-success.svg)]()

</div>

---

### 📌 نظرة عامة

**مُعين** هو مساعد شخصي ذكي يعمل عبر تليجرام ويدعم:

| الميزة | الحالة |
|--------|--------|
| الدردشة النصية (عربي + إنجليزي) | ✅ |
| ذاكرة محادثة دائمة (SQLite) | ✅ |
| البحث على الإنترنت | ✅ |
| قراءة وكتابة الملفات | ✅ |
| المهام والتذكيرات | ✅ |
| ملاحظات دائمة | ✅ |
| استدعاء APIs خارجية | ✅ |
| تنفيذ مهام متعددة تلقائياً (Tool loop) | ✅ |
| الرسائل الصوتية (STT + TTS) | ✅ |
| الصور والمستندات | ✅ |

---

### 🚀 التثبيت والتشغيل

```bash
git clone https://github.com/milou311/ai-agents.git
cd ai-agents

python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt

# أنشئ ملف .env
cp .env.example .env
# ثم عدّل القيم:
# TELEGRAM_BOT_TOKEN=...
# GROQ_API_KEY=...
```

**تشغيل البوت:**

```bash
python -m agents.telegram_bot
```

**الواجهة النصية المحلية (اختيارية):**

```bash
python main.py
```

---

### 🔑 الحصول على المفاتيح

1. **Telegram Bot Token**  
   تحدث مع [@BotFather](https://t.me/BotFather) → `/newbot`

2. **Groq API Key** (مجاني)  
   https://console.groq.com → API Keys

---

### 💬 أمثلة على الاستخدام

- «ابحث عن آخر أخبار الذكاء الاصطناعي»
- «أضف مهمة: مراجعة التقرير يوم الجمعة»
- «ذكّرني بعد 45 دقيقة بالاتصال بأحمد»
- «احفظ ملاحظة: أفضل القهوة بدون سكر»
- «اكتب ملخصاً واحفظه في ملف summary.md»
- أرسل رسالة صوتية → يرد نصاً + صوتاً
- أرسل صورة → يصفها ويساعدك

---

### 🗂️ هيكل المشروع

```text
ai-agents/
├── agents/
│   ├── telegram_bot.py      # بوت تليجرام الرئيسي
│   ├── agent_core.py        # نواة الوكيل + tool calling
│   ├── memory.py            # SQLite (محادثات، مهام، تذكيرات)
│   ├── personal_assistant.py
│   ├── voice_interface.py
│   └── tools/
│       ├── web_search.py
│       ├── file_ops.py
│       ├── tasks_tool.py
│       └── http_api.py
├── data/                    # يُنشأ تلقائياً (ذاكرة + ملفات المستخدمين)
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

---

### 🛠️ ملاحظات تقنية

- **النموذج:** `llama-3.3-70b-versatile` عبر Groq (يدعم Tool Calling)
- **التعرف على الصوت:** Groq Whisper `whisper-large-v3`
- **تحويل النص لصوت:** `edge-tts` (صوت عربي `ar-SA-HamedNeural`)
- **البحث:** DuckDuckGo (بدون مفتاح)
- **الذاكرة:** SQLite محلي في `data/memory.db`
- **الملفات:** معزولة لكل مستخدم في `data/files/<user_id>/`

---

### 📄 الرخصة

MIT License

---

<div align="center">
  Built with ❤️ by <a href="https://github.com/milou311">Mohamed Miloud</a>
</div>
