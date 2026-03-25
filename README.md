💰 AI-Powered Expense Tracker
An intelligent expense tracking web application built with Django, enhanced with an AI chatbot for financial insights, analytics, and smart interactions.


🚀 Features

📊 Expense Management
- Add, edit, and delete expenses
- Categorize expenses with categories & subcategories
- Track tax amount and total spending
- Real-time data updates

📅 Budget Tracking
- Monthly budget creation with validation (no duplicate months)
- Budget usage tracking with alerts
- Remaining balance calculation

🧾 Receipt Management
- Upload and store receipts
- Extract and track receipt details
- View recent receipts and spending

🤖 AI Chatbot (Gemini Powered)
- Ask natural language questions:
  - “What is my total spending this month?”
  - “Which category did I spend the most on?”
  - “Show items in Food category”
- Secure design:
  - No direct database exposure
  - Django handles queries → Only results sent to AI
- Supports:
  - Expense queries
  - Budget insights
  - Receipt queries
- Chat history maintained using session

📈 Dashboard Analytics
- Donut chart for expense distribution
- Bar chart for monthly spending trends
- Summary cards (total expenses, categories, etc.)

🎨 UI Features
- Clean dashboard layout
- Sidebar navigation
- Chat widget integrated across pages
- Responsive design


🧠 Tech Stack

- **Backend:** Django (Python)
- **Frontend:** HTML, CSS, JavaScript
- **Database:** SQLite
- **AI Integration:** Google Gemini API
- **Visualization:** Chart.js
- **Version Control:** Git & GitHub


🔒 Security Approach

- No raw database sent to AI
- Queries processed in Django ORM
- Only filtered/safe results passed to Gemini
- Prevents sensitive data exposure

