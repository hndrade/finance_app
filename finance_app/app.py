import streamlit as st
import json, os
import pandas as pd
from datetime import date, datetime

# ===================== CONFIG GERAL =====================
st.set_page_config(page_title="Finance App", layout="wide")

IOS_CSS = """
<style>
:root { --bg:#f7f7f8; --card:#ffffff; --txt:#111; --muted:#6b7280; --primary:#007aff; --danger:#ff3b30; --success:#34c759; }
html,body .block-container{padding-top:0.6rem; padding-bottom:5.5rem;}
/* Estilo iOS-like */
[data-testid="stSidebarNav"] { display:none; }
div[data-testid="stMetric"] { background:var(--card); border-radius:16px; padding:10px 12px; border:1px solid #e5e7eb; }
.card { background:var(--card); border:1px solid #e5e7eb; border-radius:16px; padding:12px; }
.small { font-size:12px; color:var(--muted); }
.table-compact td, .table-compact th{ padding:4px 6px !important; font-size:12px; }
/* Barra inferior (mobile) */
.navbar { position:fixed; bottom:0; left:0; right:0; background:var(--card); border-top:1px solid #e5e7eb; padding:8px 10px; }
.navbtn{width:100%; background:transparent; border:none; padding:6px 0; color:var(--muted); font-size:13px;}
.navbtn.active{color:var(--primary); font-weight:600;}
.fab { position:fixed; right:16px; bottom:76px; background:var(--primary); color:white; border:none; border-radius:24px; padding:12px 16px; font-weight:600; }
/* Desktop refinado */
@media (min-width: 992px){
  html,body .block-container{padding-bottom:2rem;}
  .navbar, .fab { display:none; }
}
</style>
"""
st.markdown(IOS_CSS, unsafe_allow_html=True)

# ===================== ARMAZENAMENTO =====================
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

accounts = load_json(FILES["accounts"])
cards = load_json(FILES["cards"])
txs = load_json(FILES["transactions"])
cats = load_json(FILES["categories"])
recs = load_json(FILES["recurrences"])

# categorias padrão
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

# ===================== STATE & HELPERS =====================
if "tab" not in st.session_state: st.session_state.tab = "home"  # home | tx | wallet | settings
if "compact" not in st.session_state: st.session_state.compact = True  # mobile compacto por padrão
if "force_desktop" not in st.session_state: st.session_state.force_desktop = False

def set_tab(tab_name:str):
    st.session_state.tab = tab_name

def money(x): return f"R$ {x:,.2f}"

def compute_month_series(df:pd.DataFrame)->pd.DataFrame:
    if df.empty: return pd.DataFrame({"month":[],"amount":[],"saldo":[]})
    df["date"] = pd.to_datetime(df["date"])
    g = df.groupby(df["date"].dt.to_period("M").astype(str))["amount"].sum().reset_index(name="amount")
    g["saldo"] = g["amount"].cumsum()
    g.rename(columns={"date":"month"}, inplace=True)
    g["month"] = g["month"].astype(str)
    return g

def card_invoice_options(card):
    today = date.today()
    closing = int(card["closing_day"]); due = int(card["due_day"])
    # Se ainda não fechou, fatura do mês corrente; senão, próximo mês
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

def add_tx(origin_type, origin_name, kind, category, desc, d_ref, value,
           paid=False, invoice_date=None, parcels=1, card_due_day=None):
    """Cria 1..N transações. Para cartão, fatia em parcelas por fatura."""
    global txs, accounts, cards
    if origin_type == "Conta":
        amount = value if kind=="income" else -value
        txs.append({
            "id": next_id(txs), "date": str(d_ref), "type": kind, "category": category, "description": desc,
            "amount": amount, "origin_type":"Conta", "origin": origin_name, "paid": paid, "invoice_date": None, "parcel": None
        })
        save_json(FILES["transactions"], txs)
    else:
        per = round(value/parcels, 2)
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
       - Conta: aplica amount no saldo ao pagar.
       - Cartão: exige paying_account; debita a conta pelo valor (amount negativo).
    """
    global txs, accounts
    acc = None
    if paying_account:
        acc = next(a for a in accounts if a["name"]==paying_account)
    for tid in ids:
        tx = next(t for t in txs if t["id"]==tid)
        if tx["paid"]: continue
        if tx["origin_type"]=="Conta":
            accc = next(a for a in accounts if a["name"]==tx["origin"])
            accc["balance"] += tx["amount"]  # aplica (negativo para despesa)
        else:
            if not acc: continue
            acc["balance"] += tx["amount"]  # despesa cartão: amount negativo -> reduz saldo
        tx["paid"] = True
    save_json(FILES["accounts"], accounts)
    save_json(FILES["transactions"], txs)

# ===================== LAYOUT: SIDEBAR (DESKTOP) =====================
# Toggle para modo compacto x desktop
with st.sidebar:
    st.markdown("### ⚙️ Exibição")
    st.session_state.compact = st.toggle("Modo compacto (mobile)", value=st.session_state.compact)
    st.session_state.force_desktop = st.toggle("Forçar layout desktop", value=st.session_state.force_desktop)
    st.markdown("---")
    # Navegação desktop
    if st.session_state.force_desktop:
        tab_map = {"🏠 Dashboard":"home","💸 Transações":"tx","💳 Carteira":"wallet","⚙️ Configurações":"settings"}
        pick = st.radio("Navegação", list(tab_map.keys()), index=list(tab_map.values()).index(st.session_state.tab))
        set_tab(tab_map[pick])

# ===================== HEADER =====================
st.markdown("<div class='small'>Finance App • Híbrido</div>", unsafe_allow_html=True)

# ===================== HOME =====================
if st.session_state.tab == "home":
    df = pd.DataFrame(txs)
    total_accounts = sum(a["balance"] for a in accounts) if accounts else 0.0
    # fatura do mês atual (pendentes de cartão)
    today = date.today()
    this_month = f"{today.year}-{today.month:02d}"
    open_invoices = 0.0
    if not df.empty and "invoice_date" in df.columns:
        mask = (df.get("origin_type","")=="Cartão") & (~df["paid"]) & (df["invoice_date"].str[:7]==this_month)
        open_invoices = df[mask]["amount"].abs().sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Saldo Contas", money(total_accounts))
    col2.metric("Faturas do mês", money(open_invoices))
    col3.metric("Saldo Projetado", money(total_accounts - open_invoices))

    # Evolução do saldo
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

    # % por categoria
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Gastos por Categoria (%)")
    if not df.empty:
        exp = df[df["amount"]<0].copy()
        if not exp.empty:
            cat = exp.groupby("category")["amount"].sum().abs().reset_index()
            cat["percent"] = (cat["amount"]/cat["amount"].sum()*100).round(1)
            st.dataframe(cat[["category","percent"]].sort_values("percent", ascending=False),
                         use_container_width=True, height=(220 if st.session_state.compact else 300))
            st.bar_chart(cat.set_index("category")["percent"])
        else:
            st.info("Sem despesas até o momento.")
    else:
        st.info("Sem lançamentos ainda.")
    st.markdown("</div>", unsafe_allow_html=True)

# ===================== TRANSAÇÕES =====================
elif st.session_state.tab == "tx":
    st.subheader("Novo Lançamento")
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
            if tipo=="Despesa" and cards and sel_origin in [c["name"] for c in cards]:
                card = next((c for c in cards if c["name"]==sel_origin), None)
                parcelas = st.number_input("Parcelas", min_value=1, max_value=48, value=1, step=1)
                invoice_map = card_invoice_options(card) if card else None
                if invoice_map:
                    inv_label = st.selectbox("Fatura", list(invoice_map.keys()))
                else:
                    inv_label = None
            else:
                inv_label = None

        submit = st.form_submit_button("Salvar")

    if submit:
        if origem_tipo=="Conta":
            add_tx("Conta", sel_origin, "income" if tipo=="Receita" else "expense",
                   categoria, desc, data_ref, valor, paid=False)
            st.success("Lançamento criado (pendente).")
        else:
            if not cards or sel_origin not in [c["name"] for c in cards]:
                st.error("Cadastre um cartão válido.")
            else:
                inv_date = invoice_map[inv_label] if invoice_map and inv_label else None
                add_tx("Cartão", sel_origin, "expense", categoria, desc, data_ref, valor,
                       paid=False, invoice_date=inv_date, parcels=int(parcelas))
                st.success(f"Despesa no cartão registrada ({parcelas} parcela(s)).")

    st.markdown("---")
    st.subheader("Pendentes")
    if txs:
        df = pd.DataFrame(txs)
        df_pend = df[~df["paid"]].copy()
        if not df_pend.empty:
            show = df_pend[["id","date","origin_type","origin","type","category","description","amount","invoice_date","parcel"]]\
                .sort_values("date", ascending=False)
            st.dataframe(show, use_container_width=True, height=(260 if st.session_state.compact else 380))
            ids_to_pay = st.multiselect("Selecionar IDs para pagar", show["id"].tolist())
            colp1, colp2 = st.columns(2)
            with colp1:
                conta_pagto = st.selectbox("Conta para pagar", [a["name"] for a in accounts] or ["(Cadastre uma conta)"])
            with colp2:
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
                         use_container_width=True, height=(260 if st.session_state.compact else 380))
        else:
            st.info("Nada pago ainda.")

# ===================== CARTEIRA (CONTAS/CARTÕES) =====================
elif st.session_state.tab == "wallet":
    st.subheader("Contas")
    with st.form("new_acc"):
        n = st.text_input("Nome")
        bal = st.number_input("Saldo Inicial", value=0.0, step=0.01)
        if st.form_submit_button("Adicionar Conta"):
            accounts.append({"id":next_id(accounts),"name":n,"balance":bal})
            save_json(FILES["accounts"], accounts); st.success("Conta criada."); st.rerun()
    if accounts:
        st.dataframe(pd.DataFrame(accounts), use_container_width=True)
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
        st.dataframe(pd.DataFrame(cards), use_container_width=True)
    else:
        st.info("Nenhum cartão.")

# ===================== CONFIG (CATEGORIAS / IMPORT-EXPORT) =====================
elif st.session_state.tab == "settings":
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

# ===================== NAV MOBILE (SEM JS) =====================
# Só desenha barra inferior se NÃO estiver em modo desktop forçado
if not st.session_state.force_desktop:
    home_cls = "navbtn active" if st.session_state.tab=="home" else "navbtn"
    tx_cls   = "navbtn active" if st.session_state.tab=="tx" else "navbtn"
    wal_cls  = "navbtn active" if st.session_state.tab=="wallet" else "navbtn"
    set_cls  = "navbtn active" if st.session_state.tab=="settings" else "navbtn"

    # Desenha botões genuínos que mudam session_state; sem JS
    c = st.container()
    with c:
        st.markdown("<div class='navbar'>", unsafe_allow_html=True)
        colA, colB, colC, colD = st.columns(4)
        with colA:
            if st.button("🏠\nHome", use_container_width=True):
                set_tab("home"); st.rerun()
        with colB:
            if st.button("💸\nTransações", use_container_width=True):
                set_tab("tx"); st.rerun()
        with colC:
            if st.button("💳\nCarteira", use_container_width=True):
                set_tab("wallet"); st.rerun()
        with colD:
            if st.button("⚙️\nConfig", use_container_width=True):
                set_tab("settings"); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Botão flutuante -> Transações
    st.markdown(
        "<form action='#' method='get'><button class='fab' name='go_tx' value='1'>+ Lançar</button></form>",
        unsafe_allow_html=True
    )
    if st.session_state.get("go_tx"):
        set_tab("tx"); st.rerun()
