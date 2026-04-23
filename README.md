# 💳 Payment Analytics Dashboard

A multi-PSP payment analytics dashboard built with **Streamlit** and **Plotly** for FundedNext.

## Features

- **Total payment attempt analysis** — PSP-wise, country-wise, method-wise
- **Approval rate analytics** — by country, MID, PSP
- **Interactive filters** — filter by PSP source, PSP name, MID, country, payment method
- **Automated insights** — strategic recommendations and anomaly detection
- **Global choropleth map** — country-level approval rate heatmap
- **MID × Country heatmap** — deep-dive BridgerPay cross-analysis

## PSP Data Logic

| PSP | Filter Applied |
|-----|---------------|
| **BridgerPay** | Unique `merchantOrderId` (deduped retries). `approved` = success |
| **Coinsbuy** | `Confirmed` = success |
| **Confirmo** | `PAID` = success |
| **PayProcc** | USD amount: `Amount` if Currency=USD, else `Applied Amount`. Unique `Merchant Order ID` |
| **Zen Pay** | Apple Pay + Google Pay only (no Card). `ACCEPTED` = success |

## Setup & Run Locally

### 1. Clone / download

```bash
git clone https://github.com/YOUR_USERNAME/payment-dashboard.git
cd payment-dashboard
```

### 2. Add your data files

Place your CSV/XLSX files in the `data/` folder:

```
data/
  BridgerPay.csv
  Coinsbuy.xlsx
  Confirmo.csv
  PayProcc.csv
  Zen_Pay.csv
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the dashboard

```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`

---

## Deploy on Streamlit Cloud (GitHub)

1. **Push to GitHub** — make sure `data/` folder and all files are committed
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **"New app"**
4. Select your repo, branch (`main`), and set **Main file path** to `app.py`
5. Click **Deploy**

> **Note on data privacy**: If your data contains sensitive customer information, do NOT push raw CSVs to a public GitHub repo. Use a private repo, or use Streamlit secrets + cloud storage (S3/GCS) to load data securely.

### Option B: Streamlit Cloud with Private Data

If you don't want to commit raw data files:

1. Upload your files to an S3 bucket or similar
2. Use `st.secrets` in Streamlit Cloud to store credentials
3. Load data via `boto3` or `pandas.read_csv(s3_url)`

---

## Folder Structure

```
payment-dashboard/
├── app.py                 # Main dashboard
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── .gitignore             # Ignore data files if needed
└── data/
    ├── BridgerPay.csv
    ├── Coinsbuy.xlsx
    ├── Confirmo.csv
    ├── PayProcc.csv
    └── Zen_Pay.csv
```

## .gitignore (optional — if keeping data private)

```
data/*.csv
data/*.xlsx
```
