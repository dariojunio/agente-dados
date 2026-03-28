# ◈ Data Agent

A conversational data analysis agent built with Streamlit and Claude (Anthropic). Upload a CSV or Excel file, ask questions in natural language, and get instant analysis, live Python/pandas execution, and charts — no coding required.

---

## Features

- **Natural language chat** with a data expert agent (responses in Portuguese)
- **Exploratory data analysis** — statistical summary, null values, column types
- **Live pandas code execution** generated and run by the agent itself
- **Chart generation** — bar, line, histogram, pie, scatter, and box plots
- **Quick suggestion buttons** to get started without knowing what to ask
- Supports **CSV, XLSX, and XLS** files

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-username/agente-dados.git
cd agente-dados
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up your API key

Create a `.streamlit/secrets.toml` file:

```toml
ANTHROPIC_API_KEY = "your-key-here"
```

Or set it as an environment variable:

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### 4. Run the app

```bash
streamlit run app.py
```

---

## Project Structure

```
agente-dados/
├── app.py           # Streamlit interface
├── agente.py        # Agent logic and tool loop
├── ferramentas.py   # Analysis functions, pandas execution, and chart generation
└── requirements.txt
```

---

## Tech Stack

- [Streamlit](https://streamlit.io/) — web interface
- [Anthropic Claude](https://anthropic.com/) — language model (claude-haiku-4-5)
- [Pandas](https://pandas.pydata.org/) — data manipulation
- [Matplotlib](https://matplotlib.org/) — chart rendering

---

## Deployment

Ready to deploy on [Streamlit Cloud](https://streamlit.io/cloud). Just connect the repository and add `ANTHROPIC_API_KEY` to the app secrets.

---

## License

MIT
