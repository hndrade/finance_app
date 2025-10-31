import streamlit as st
import json, os
from datetime import date
import pandas as pd

data_dir = 'data'
accounts_file = os.path.join(data_dir, 'accounts.json')
transactions_file = os.path.join(data_dir, 'transactions.json')

# Funções utilitárias
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Carregar dados
accounts = load_json(accounts_file)
transactions = load_json(transactions_file)

st.title('💰 Controle Financeiro Pessoal')

contas_nomes = [a['name'] for a in accounts] if accounts else []
selected_account = st.sidebar.selectbox('Conta', contas_nomes)

st.header('Novo Lançamento')
with st.form('new_tx'):
    tipo = st.selectbox('Tipo', ['Despesa', 'Receita'])
    valor = st.number_input('Valor', min_value=0.01, step=0.01)
    categoria = st.text_input('Categoria')
    descricao = st.text_input('Descrição')
    data = st.date_input('Data', date.today())
    enviar = st.form_submit_button('Salvar')

if enviar and selected_account:
    conta = next(a for a in accounts if a['name'] == selected_account)
    novo_id = len(transactions) + 1
    amount = valor if tipo == 'Receita' else -valor
    nova_tx = {
        'id': novo_id,
        'account_id': conta['id'],
        'date': str(data),
        'type': tipo.lower(),
        'category': categoria,
        'description': descricao,
        'amount': amount
    }
    transactions.append(nova_tx)
    conta['balance'] += amount
    save_json(transactions_file, transactions)
    save_json(accounts_file, accounts)
    st.success('Lançamento salvo com sucesso!')

st.header('Transações Recentes')
df = pd.DataFrame(transactions)
if not df.empty:
    st.dataframe(df.sort_values('date', ascending=False))
else:
    st.info('Nenhum lançamento ainda.')

if accounts:
    st.header('Saldo por Conta')
    df_acc = pd.DataFrame(accounts)
    st.bar_chart(df_acc.set_index('name')['balance'])
