# Elevate Charter AI (Django + Streamlit)

A modern, object-oriented private aviation charter quoting system with two modes:
- **Manual** form-based quote generation
- **Chat** agent with natural language processing

## 🏗️ **Architecture**

### **Backend (Django)**
- **Models** (`core/models.py`): Clean data structures using dataclasses
- **Repository** (`core/repository.py`): Data access layer for airports and aircraft
- **Services** (`core/services.py`): Business logic for pricing and trip processing
- **Views** (`core/views.py`): API endpoints with clean separation of concerns

### **Frontend (Streamlit)**
- **Components** (`frontend/components.py`): Reusable UI components
- **Main App** (`frontend/streamlit_app.py`): Clean, minimal main application

## ✨ **Features**

### **Manual Mode**
- Traditional form-based quote generation
- Real-time pricing with distance calculations
- Multiple aircraft options with detailed comparisons
- Comprehensive pricing breakdowns

### **Chat Mode**
- Natural language understanding
- Context-aware conversations
- Fallback to regex parsing for reliability
- Structured quote responses

## 🚀 **Setup**

### **1. Backend Setup**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set up OpenAI (optional)
cp .env.template .env
# Edit .env and add your OpenAI API key
export OPENAI_API_KEY="your_api_key_here"

python manage.py runserver 8000
```

### **2. Frontend Setup**
```bash
cd ../frontend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export BACKEND_URL=http://127.0.0.1:8000
streamlit run streamlit_app.py
```

## 🔧 **OpenAI Integration**

The chat mode can use OpenAI's API for enhanced natural language understanding:

- **Better Intent Recognition**: Understands complex travel requests
- **Conversation Memory**: Maintains context across multiple messages
- **Natural Responses**: Generates human-like, aviation-focused responses

### **Environment Variables**
```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4  # Optional, defaults to gpt-4
OPENAI_SYSTEM_PROMPT="Custom prompt..."  # Optional
```

## 📡 **API Endpoints**

* `POST /api/quote` → Generate manual quotes with multiple aircraft options
* `POST /api/chat`  → Process natural language requests
* `GET /api/status` → System status and OpenAI availability

## 💬 **Chat Examples**

Try these natural language inputs:
- "I need a jet for 4 people from LA to Vegas next weekend"
- "Book a charter from New York to Miami on Friday, return Monday"
- "Private jet for 8 passengers from Boston to Seattle departing next week"

### **Conversation Flow Features**

The chat system maintains **conversation context** and provides **intelligent follow-up handling**:

#### **Memory & Context**
- **Short-term memory**: Remembers the last 3 messages for immediate context
- **Conversation state**: Maintains trip details across multiple messages
- **Context-aware responses**: Understands follow-up questions without repetition

#### **Smart Follow-up Handling**
- **Partial information**: Asks clarifying questions for missing details
- **Progressive completion**: Builds trip requests step-by-step
- **Intelligent updates**: Handles changes to existing trip details

#### **Conversation Examples**
```
User: "i need a jet"
Bot: "I have some details: passengers: 1. I still need: origin, destination, departure_date. Can you provide these?"

User: "from bos to lax"
Bot: "Great! When would you like to depart from BOS to LAX?"

User: "on friday"
Bot: "Charter: 1 pax on Very Light Jet from BOS to LAX. Total: $29,802 USD."

User: "i want a bigger aircraft"
Bot: "Charter: 6 pax on Light Jet from BOS to LAX. Total: $XX,XXX USD."
```

#### **Follow-up Patterns**
- **"bigger aircraft"** → Upgrades to larger aircraft with 4-6 passengers
- **"for X people"** → Updates passenger count while maintaining route/date
- **"return flight"** → Adds return date to existing one-way trip
- **"change to X passengers"** → Updates passenger count and aircraft accordingly

#### **Memory Limitations**
- **Context window**: Currently limited to last 3 messages
- **Long conversations**: May lose earlier context in extended chats
- **Future improvements**: Planning to increase memory and add conversation summaries

## 🎯 **Code Quality Features**

- **Type Hints**: Full Python type annotations for better IDE support
- **Clean Architecture**: Separation of concerns with models, services, and views
- **Error Handling**: Comprehensive error handling and user feedback
- **Documentation**: Detailed docstrings and inline comments
- **Modular Design**: Reusable components and services

## 📝 **Notes**

* **Clean Code**: Object-oriented design with clear separation of concerns
* **Maintainable**: Easy to extend and modify for future requirements
* **Scalable**: Architecture supports easy addition of new features
* **Professional**: Production-ready code structure and patterns

## 🔄 **Development Workflow**

1. **Models**: Define data structures in `models.py`
2. **Repository**: Implement data access in `repository.py`
3. **Services**: Add business logic in `services.py`
4. **Views**: Create API endpoints in `views.py`
5. **Components**: Build UI components in `components.py`
6. **Integration**: Wire everything together in the main app

This architecture makes the codebase easy to understand, maintain, and extend! 🚁✈️
