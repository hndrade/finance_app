import streamlit as st
import json, os
import pandas as pd
from datetime import date, datetime

# -------------------- CONFIG & THEME (iOS-like) --------------------
st.set_page_config(page_title="Finance App", layout="wide")
IOS_CSS = """
<style>
:root { --bg:#f7f7f8; --card:#ffffff; --txt:#111; --muted:#6b7280; --primary:#007aff; --danger:#ff3b30; --success:#34c759; }
html,body .block-container{padding-top:0.6rem; padding-bottom:5.5rem; }
[data-testid="stSidebar"] { display:none; } /* sem sidebar */
button[kind="secondary"]{border-radius:14px;}
div[data-testid="stMetric"] { background:var(--card); border-radius:16px; padding:10px 12px; border:1px solid #e5e7eb; }
.css-1kyxreq, .st-emotion-cache-1kyxreq{font-family:-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial;}
/* bottom nav */
.navbar { position:fixed; bottom:0; left:0; right:0; background:var(--card); border-top:1px solid #e5e7eb; padding:8px 10px; }
.navbtn{width:100%; background:transparent; border:none; padding:6px 0; color:var(--muted); font-size:13px;}
.navbtn.active{color:var(--primary); font-weight:600;}
.fab { position:fixed; right:16px; bottom:76px; background:var(--primary); color:white; border:none; border-radius:24px; padding:12px 16px; font-weight:600; }
.card { background:var(--card); border:1px solid #e5e7eb; border-radius:16px; padding:12px; }
.small { font-size:12px; color:var(--muted); }
.table-compact td, .table-compact th{ padding:4px 6px !important; font-size:12px; }
</style>
"""
st.markdown(IOS_CSS, unsafe_allow_html=True)

# -------------------- FILES & STORAGE --------------------
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
FILES = {
    "accounts": os.path.join(DATA_DIR, "accounts.json"),
    "cards": os.path.join(DATA_DIR, "cards.json"),
    "transactions": os.path.join(DATA_DIR, "transactions.json"),
    "categories": os.path.join(DATA_DIR, "categories.json"),
    "recurrences": os.path.join(DATA_DIR, "recurrences.json"),
}

def load_json(path):
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)

def next_id(items): return (max([i.get("id", 0) for i in items], default=0) + 1)

# load
accounts = load_json(FILES["accounts"])
cards = load_json(FILES["cards"])
txs = load_json(FILES["transactions"])
cats = load_json(FILES["categories"])
recs = load_json(FILES["recurrences"])

# defaults
if not cats:
    cats = [
        {"id":1,"name":"Alimentação","type":"expense"},
        {"id":2,"name":"Transporte","type":"expense"},
        {"id":3,"name":"Saúde","type":"expense"},
        {"id":4,"name":"Lazer","type":"expense"},
        {"id":5,"name":"Moradia","type":"expense"},
        {"id":6,"name":"Salário","type":"income"},
        {"id":7,"name":"Investimentos","type":"income"},
    ]; save_json(FILES["categories"], cats)

# -------------------- NAV STATE --------------------
if "tab" not in st.session_state: st.session_state.tab = "home"
def set_tab(t): st.session_state.tab = t

# -------------------- HELPERS --------------------
def month_label(dt:date)->str: return datetime(dt.year, dt.month, 1).strftime("%Y-%m")

def compute_month_series(df:pd.DataFrame)->pd.DataFrame:
    if df.empty: return pd.DataFrame({"month":[],"amount":[],"saldo":[]})
    df["date"] = pd.to_datetime(df["date"])
    g = df.groupby(df["date"].dt.to_period("M").astype(str))["amount"].sum().reset_index(name="amount")
    g["saldo"] = g["amount"].cumsum()
    g.rename(columns={"date":"month"}, inplace=True)
    g["month"] = g["month"].astype(str)
    return g

def money(x): return f"R$ {x:,.2f}"

def card_invoice_options(card):
    today = date.today()
    closing = int(card["closing_day"]); due = int(card["due_day"])
    # se ainda não fechou no mês, fatura atual vence este mês; senão, mês seguinte
    if today.day <= closing:
        cur = date(today.year, today.month, due)
    else:
        ny, nm = (today.year + 1, 1) if today.month==12 else (today.year, today.month+1)
        cur = date(ny, nm, due)
    ny, nm = (cur.year + 1, 1) if cur.month==12 else (cur.year, cur.month+1)
    nxt = date(ny, nm, due)
    labels = {
        f"Fatura Atual ({cur.strftime('%b/%Y')})": cur.strftime("%Y-%m-%d"),
        f"Próxima Fatura ({nxt.strftime('%b/%Y')})": nxt.strftime("%Y-%m-%d"),
    }
    return labels

def add_tx(origin_type, origin_name, kind, category, desc, d_ref, value, paid=False, invoice_date=None, parcels=1, card_due_day=None):
    """Registra 1..N transações. Para cartão, value é o total e será fatiado em parcelas."""
    global txs, accounts, cards
    if origin_type == "Conta":
        # para conta: não mexe no saldo agora se pendente; só ao marcar paga
        amount = value if kind=="income" else -value
        txs.append({
            "id": next_id(txs), "date": str(d_ref), "type": kind, "category": category, "description": desc,
            "amount": amount, "origin_type":"Conta", "origin": origin_name, "paid": paid, "invoice_date": None, "parcel": None
        })
        save_json(FILES["transactions"], txs)
    else:
        # cartão: cria N parcelas, sem mexer no saldo de conta; controla por invoice_date
        per = round(value/parcels, 2)
        # base invoice_date vem do seletor; se None, calcula fatura atual
        card = next(c for c in cards if c["name"] == origin_name)
        base_inv = invoice_date or list(card_invoice_options(card).values())[0]
        y = int(base_inv[:4]); m = int(base_inv[5:7])
        for i in range(parcels):
            mm = m + i
            yy = y + (mm-1)//12
            mm = ((mm-1)%12)+1
            inv_dt = date(yy, mm, int(card_due_day or card["due_day"]))
            txs.append({
                "id": next_id(txs), "date": str(d_ref), "type": "expense", "category": category,
                "description": f"{desc} (Parc {i+1}/{parcels})" if parcels>1 else desc,
                "amount": -per, "origin_type":"Cartão", "origin": origin_name, "paid": False,
                "invoice_date": inv_dt.strftime("%Y-%m-%d"), "parcel": f"{i+1}/{parcels}"
            })
        save_json(FILES["transactions"], txs)

def pay_transactions(ids, paying_account=None):
    """Marca como pagas e abate saldos:
       - Conta: aplica amount no saldo no momento do pagamento (uma vez).
       - Cartão: exige paying_account, debita conta pelo valor absoluto e marca tx paga.
    """
    global txs, accounts
    acc = None
    if paying_account:
        acc = next(a for a in accounts if a["name"]==paying_account)
    for tid in ids:
        tx = next(t for t in txs if t["id"]==tid)
        if tx["paid"]: continue
        if tx["origin_type"]=="Conta":
            acc = next(a for a in accounts if a["name"]==tx["origin"])
            acc["balance"] += tx["amount"]  # amount já é negativo p/ despesa
        else:
            if not acc: continue
            acc["balance"] += tx["amount"]  # despesa cartão: amount negativo -> reduz saldo da conta ao pagar
        tx["paid"] = True
    save_json(FILES["accounts"], accounts)
    save_json(FILES["transactions"], txs)

# -------------------- HEADER --------------------
st.markdown("<div class='small'>Finance App • Mobile</div>", unsafe_allow_html=True)

# -------------------- TABS --------------------
tab = st.session_state.tab

# -------------------- DASHBOARD --------------------
if tab == "home":
    # KPIs
    df = pd.DataFrame(txs)
    total_accounts = sum(a["balance"] for a in accounts) if accounts else 0.0
    # faturas abertas (somente cartão, pendentes por invoice do mês atual)
    today = date.today()
    this_month = f"{today.year}-{today.month:02d}"
    open_invoices = 0.0
    if not df.empty:
        if "invoice_date" in df.columns:
            open_invoices = df[(df["origin_type"]=="Cartão") & (~df["paid"]) & (df["invoice_date"].str[:7]==this_month)]["amount"].abs().sum()
    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo Contas", money(total_accounts))
    col2.metric("Faturas do mês", money(open_invoices))
    proj = total_accounts - open_invoices
    col3.metric("Saldo Projetado", money(proj))

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Evolução do Saldo Mensal")
    if not df.empty:
        s = compute_month_series(df.copy())
        if not s.empty:
            st.line_chart(s.set_index("month")["saldo"])
        else:
            st.info("Sem dados para gráfico.")
    else:
        st.info("Sem lançamentos ainda.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Gastos por Categoria (%)")
    if not df.empty:
        exp = df[df["amount"]<0].copy()
        if not exp.empty:
            cat = exp.groupby("category")["amount"].sum().abs().reset_index()
            cat["percent"] = (cat["amount"]/cat["amount"].sum()*100).round(1)
            st.dataframe(cat[["category","percent"]].sort_values("percent", ascending=False), use_container_width=True)
            st.bar_chart(cat.set_index("category")["percent"])
        else:
            st.info("Sem despesas até o momento.")
    else:
        st.info("Sem lançamentos ainda.")
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------- TRANSAÇÕES --------------------
elif tab == "tx":
    st.subheader("Novo Lançamento")
    colA, colB = st.columns(2)
    with st.form("quick_tx"):
        tipo = st.selectbox("Tipo", ["Despesa","Receita"], index=0)
        origem_tipo = st.radio("Origem", ["Conta","Cartão"], horizontal=True)
        valor = st.number_input("Valor", min_value=0.01, step=0.01)
        categoria = st.selectbox("Categoria", [c["name"] for c in cats])
        desc = st.text_input("Descrição")
        data_ref = st.date_input("Data", date.today())
        parcelas = 1
        invoice_map = None
        sel_origin = None
        if origem_tipo=="Conta":
            sel_origin = st.selectbox("Conta", [a["name"] for a in accounts] or ["(Cadastre uma conta)"])
        else:
            sel_origin = st.selectbox("Cartão", [c["name"] for c in cards] or ["(Cadastre um cartão)"])
            if tipo=="Despesa" and cards:
                card = next((c for c in cards if c["name"]==sel_origin), None)
                parcelas = st.number_input("Parcelas", min_value=1, max_value=48, value=1, step=1)
                invoice_map = card_invoice_options(card) if card else None
                inv_label = st.selectbox("Fatura", list(invoice_map.keys()) if invoice_map else [])
        submit = st.form_submit_button("Salvar")

    if submit:
        if origem_tipo=="Conta":
            add_tx("Conta", sel_origin, "income" if tipo=="Receita" else "expense",
                   categoria, desc, data_ref, valor, paid=False)
            st.success("Lançamento criado (pendente). Marque como pago quando efetivar.")
        else:
            if not cards:
                st.error("Cadastre um cartão.")
            else:
                inv_date = invoice_map[inv_label] if invoice_map else None
                add_tx("Cartão", sel_origin, "expense", categoria, desc, data_ref, valor,
                       paid=False, invoice_date=inv_date, parcels=int(parcelas))
                st.success(f"Despesa no cartão registrada ({parcelas} parcela(s)).")

    st.markdown("---")
    st.subheader("Pendentes")
    if txs:
        df = pd.DataFrame(txs)
        df_pend = df[~df["paid"]].copy()
        if not df_pend.empty:
            # compact view
            show = df_pend[["id","date","origin_type","origin","type","category","description","amount","invoice_date","parcel"]].sort_values("date", ascending=False)
            st.dataframe(show, use_container_width=True, height=260)
            ids_to_pay = st.multiselect("Selecionar IDs para pagar", show["id"].tolist())
            pay_col1, pay_col2 = st.columns(2)
            with pay_col1:
                conta_pagto = st.selectbox("Conta para pagar", [a["name"] for a in accounts])
            with pay_col2:
                if st.button("Pagar selecionados ✅"):
                    pay_transactions(ids_to_pay, paying_account=conta_pagto)
                    st.rerun()
        else:
            st.info("Nenhuma pendência.")
    else:
        st.info("Sem lançamentos.")

    st.markdown("---")
    st.subheader("Pagas (recentes)")
    if txs:
        df = pd.DataFrame(txs)
        df_paid = df[df["paid"]].copy().sort_values("date", ascending=False).head(20)
        if not df_paid.empty:
            st.dataframe(df_paid[["id","date","origin_type","origin","type","category","description","amount","invoice_date","parcel"]],
                         use_container_width=True, height=260)
        else:
            st.info("Nada pago ainda.")

# -------------------- CONTAS / CARTÕES --------------------
elif tab == "wallet":
    st.subheader("Contas")
    with st.form("new_acc"):
        n = st.text_input("Nome")
        bal = st.number_input("Saldo Inicial", value=0.0, step=0.01)
        if st.form_submit_button("Adicionar Conta"):
            accounts.append({"id":next_id(accounts),"name":n,"balance":bal})
            save_json(FILES["accounts"], accounts); st.success("Conta criada."); st.rerun()
    if accounts:
        df = pd.DataFrame(accounts)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhuma conta.")

    st.markdown("---")
    st.subheader("Cartões")
    with st.form("new_card"):
        n = st.text_input("Nome do Cartão")
        limitv = st.number_input("Limite (R$)", value=1000.0, step=100.0)
        closing = st.number_input("Fechamento (1-28)", min_value=1, max_value=28, value=10)
        due = st.number_input("Vencimento (1-28)", min_value=1, max_value=28, value=20)
        if st.form_submit_button("Adicionar Cartão"):
            cards.append({"id":next_id(cards),"name":n,"limit":limitv,"closing_day":int(closing),"due_day":int(due)})
            save_json(FILES["cards"], cards); st.success("Cartão criado."); st.rerun()
    if cards:
        dfc = pd.DataFrame(cards)
        st.dataframe(dfc, use_container_width=True)
    else:
        st.info("Nenhum cartão.")

# -------------------- CONFIG / CATEGORIAS / IMPORT-EXPORT --------------------
elif tab == "settings":
    st.subheader("Categorias")
    with st.form("new_cat"):
        name = st.text_input("Nome da categoria")
        typ = st.selectbox("Tipo", ["Despesa","Receita"])
        if st.form_submit_button("Adicionar Categoria"):
            cats.append({"id":next_id(cats),"name":name,"type":"expense" if typ=="Despesa" else "income"})
            save_json(FILES["categories"], cats); st.success("Categoria criada."); st.rerun()
    if cats:
        st.dataframe(pd.DataFrame(cats), use_container_width=True)

    st.markdown("---")
    st.subheader("Exportar / Importar CSV")
    export_blocks = {
        "accounts": accounts, "cards": cards, "transactions": txs, "categories": cats, "recurrences": recs
    }
    c1,c2 = st.columns(2)
    with c1:
        for key, data in export_blocks.items():
            if data:
                csv = pd.DataFrame(data).to_csv(index=False).encode("utf-8-sig")
                st.download_button(f"Baixar {key}.csv", data=csv, file_name=f"{key}.csv", mime="text/csv")
    with c2:
        up = st.file_uploader("Enviar CSV para adicionar/substituir", type=["csv"])
        target = st.selectbox("Tabela", list(export_blocks.keys()))
        action = st.radio("Ação", ["Adicionar", "Substituir"], horizontal=True)
        if up is not None and st.button("Aplicar upload"):
            df_new = pd.read_csv(up)
            cur = load_json(FILES[target])
            if action=="Adicionar":
                nid = next_id(cur)
                rows=[]
                for _,r in df_new.iterrows():
                    d=r.to_dict(); d["id"]=nid; nid+=1; rows.append(d)
                cur += rows; save_json(FILES[target], cur)
            else:
                df_new["id"] = range(1, len(df_new)+1)
                save_json(FILES[target], df_new.to_dict(orient="records"))
            st.success("Importação concluída."); st.rerun()

# -------------------- FLOAT ACTION BUTTON --------------------
st.markdown("<button class='fab' onclick='window.parent.postMessage({type:\"streamlit:setComponentValue\",value:\"tx\"},\"*\")'>+ Lançar</button>", unsafe_allow_html=True)
# pequeno hack: botão leva para aba de transações
st.session_state.tab = st.session_state.tab  # no-op

# -------------------- BOTTOM NAV --------------------
home_cls = "navbtn active" if tab=="home" else "navbtn"
tx_cls   = "navbtn active" if tab=="tx" else "navbtn"
wal_cls  = "navbtn active" if tab=="wallet" else "navbtn"
set_cls  = "navbtn active" if tab=="settings" else "navbtn"
nav_html = f"""
<div class='navbar'>
  <div class='row' style='display:flex; gap:6px;'>
    <div style='flex:1;text-align:center;'><button class='{home_cls}' onclick="window.parent.postMessage({{tab:'home'}},'*')">🏠<br/>Home</button></div>
    <div style='flex:1;text-align:center;'><button class='{tx_cls}' onclick="window.parent.postMessage({{tab:'tx'}},'*')">💸<br/>Transações</button></div>
    <div style='flex:1;text-align:center;'><button class='{wal_cls}' onclick="window.parent.postMessage({{tab:'wallet'}},'*')">💳<br/>Carteira</button></div>
    <div style='flex:1;text-align:center;'><button class='{set_cls}' onclick="window.parent.postMessage({{tab:'settings'}},'*')">⚙️<br/>Config</button></div>
  </div>
</div>
<script>
window.addEventListener('message', (e)=>{
  if(e.data && e.data.tab){ fetch(window.location.href, {{method:'POST', headers:{{'X-Requested-With':'XMLHttpRequest'}}}}).then(()=>{ window.parent.postMessage({{type:'streamlit:setAppState', state:{{tab:e.data.tab}}}}, '*'); } ) }
});
</script>
"""
st.markdown(nav_html, unsafe_allow_html=True)
