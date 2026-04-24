# 🤖 Agente Gemini — Pipeline Multi-Agente

Pipeline multi-agente usando **Google Gemini** com interface web em tempo real.  
✅ Compatível com **Python 3.10, 3.11, 3.12, 3.13 e 3.14**

---

## 🚀 Início Rápido

### 1. Obter chave Gemini (grátis)
Acesse **https://aistudio.google.com/apikey** e crie uma chave gratuita.

### 2. Instalar
```bash
cd agente_gemini
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### 3. Configurar
```bash
copy .env.example .env
# Edite o .env e coloque sua GEMINI_API_KEY
```

### 4. Rodar

**Interface Web (recomendado):**
```bash
python app.py
# Acesse: http://localhost:5000
```

**CLI:**
```bash
python main.py -t "SaaS para barbearias no Nordeste"
```

---

## 🏗️ Arquitetura

```
agente_gemini/
├── app.py               # Servidor Flask + SSE
├── main.py              # CLI
├── crew.py              # Orquestração do pipeline
├── config.py
├── requirements.txt
├── .env.example
├── agents/
│   ├── base_agent.py    # Motor Gemini Function Calling
│   └── agentes.py       # 4 agentes
├── tools/
│   └── custom_tools.py  # 4 ferramentas
├── templates/
│   └── index.html       # Interface web dark
└── output/              # Relatórios gerados
```

## 👥 Pipeline

```
🔍 Pesquisador  →  busca_web (3+ buscas DuckDuckGo)
      ↓
📊 Analista     →  analisar_texto (métricas + insights)
      ↓
✍️  Redator     →  salvar_arquivo (relatorio_final.md)
      ↓
🎯 Gerente      →  salvar_arquivo (relatorio_revisado.md)
```

## ⚙️ .env

```env
GEMINI_API_KEY=AIza...              # obrigatório — grátis em aistudio.google.com
GEMINI_MODEL=gemini-1.5-flash       # ou gemini-1.5-pro
PORT=5000
VERBOSE=true
```

## 💡 Exemplos

```bash
python main.py -t "mercado de SaaS para barbearias"
python main.py -t "agendamento online para clínicas"
python main.py -t "WhatsApp como canal de vendas"
```
