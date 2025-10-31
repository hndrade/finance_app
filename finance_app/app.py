import streamlit as st
import json, os
import pandas as pd
from datetime import date, timedelta

# Diretório de dados
data_dir = 'data'
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# Arquivos JSON
FILES = {
    'accounts': os.path.join(data_dir, 'accounts.json'),
    'cards': os.path.join(data_dir, 'cards.json'),
    'transactions': os.path.join(data_dir, 'transactions.json'),
    'recurrences': os.path.join(data_dir, 'recurrences.json')
}

# Funções auxiliares
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_next_id(items):
    return max([i.get('id', 0) for i in items], default=0) + 1

# Carrega os dados
accounts = load_json(FILES['accounts'])
cards = load_json(FILES['cards'])
transactions = load_json(FILES['transactions'])
recurrences = load_json(FILES['recurrences'])

# Configuração do app
st.set_page_config(page_title='Finance App', layout='wide')
st.title('💰 Finance App — Dashboard Financeiro Completo')

# Menu lateral
menu = st.sidebar.radio('Navegação', ['🏠 Dashboard', '🏦 Contas', '💳 Cartões', '💸 Transações', '🔁 Recorrências'])

# ===================== DASHBOARD =====================
if menu == '🏠 Dashboard':
    col1, col2, col3 = st.columns(3)
    total_contas = sum(a['balance'] for a in accounts) if accounts else 0
    total_cartoes = sum(c.get('invoice', 0) for c in cards) if cards else 0
    saldo_proj = total_contas - total_cartoes

    col1.metric('Saldo em Contas', f"R$ {total_contas:,.2f}")
    col2.metric('Faturas a Pagar', f"R$ {total_cartoes:,.2f}")
    col3.metric('Saldo Projetado', f"R$ {saldo_proj:,.2f}")

    st.markdown('---')
    st.subheader('📊 Distribuição por Categoria')
    df = pd.DataFrame(transactions)
    if not df.empty:
        df_exp = df[df['amount'] < 0]
        df_exp['abs_amount'] = df_exp['amount'].abs()
        cat_data = df_exp.groupby('category')['abs_amount'].sum().reset_index()
        st.bar_chart(cat_data.set_index('category'))
    else:
        st.info('Nenhuma transação cadastrada ainda.')

# ===================== CONTAS =====================
elif menu == '🏦 Contas':
    st.subheader('Gerenciamento de Contas')

    with st.form('nova_conta'):
        nome = st.text_input('Nome da Conta')
        saldo = st.number_input('Saldo Inicial', step=0.01, value=0.0)
        criar = st.form_submit_button('Adicionar Conta')
        if criar and nome:
            nova = {'id': get_next_id(accounts), 'name': nome, 'balance': saldo}
            accounts.append(nova)
            save_json(FILES['accounts'], accounts)
            st.success('Conta criada com sucesso!')

    if accounts:
        df_acc = pd.DataFrame(accounts)
        st.dataframe(df_acc)
        st.bar_chart(df_acc.set_index('name')['balance'])
    else:
        st.info('Nenhuma conta cadastrada.')

# ===================== CARTÕES =====================
elif menu == '💳 Cartões':
    st.subheader('Gerenciamento de Cartões de Crédito')

    with st.form('novo_cartao'):
        nome = st.text_input('Nome do Cartão')
        limite = st.number_input('Limite (R$)', step=100.0, value=1000.0)
        fechamento = st.number_input('Dia do Fechamento', min_value=1, max_value=28, value=10)
        vencimento = st.number_input('Dia do Vencimento', min_value=1, max_value=28, value=20)
        criar = st.form_submit_button('Adicionar Cartão')
        if criar and nome:
            novo = {
                'id': get_next_id(cards), 'name': nome, 'limit': limite,
                'closing_day': fechamento, 'due_day': vencimento, 'invoice': 0
            }
            cards.append(novo)
            save_json(FILES['cards'], cards)
            st.success('Cartão adicionado com sucesso!')

    if cards:
        df_cards = pd.DataFrame(cards)
        st.dataframe(df_cards[['name', 'limit', 'closing_day', 'due_day', 'invoice']])
    else:
        st.info('Nenhum cartão cadastrado.')

# ===================== TRANSAÇÕES =====================
elif menu == '💸 Transações':
    st.subheader('Lançamentos Financeiros')

    contas_nomes = [a['name'] for a in accounts] if accounts else []
    with st.form('nova_tx'):
        tipo = st.selectbox('Tipo', ['Despesa', 'Receita'])
        valor = st.number_input('Valor', min_value=0.01, step=0.01)
        categoria = st.text_input('Categoria')
        descricao = st.text_input('Descrição')
        data_lcto = st.date_input('Data', date.today())
        conta_sel = st.selectbox('Conta', contas_nomes)
        enviar = st.form_submit_button('Registrar')

    if enviar and conta_sel:
        conta = next(a for a in accounts if a['name'] == conta_sel)
        novo_id = get_next_id(transactions)
        amount = valor if tipo == 'Receita' else -valor
        nova_tx = {
            'id': novo_id,
            'account_id': conta['id'],
            'date': str(data_lcto),
            'type': tipo.lower(),
            'category': categoria,
            'description': descricao,
            'amount': amount
        }
        transactions.append(nova_tx)
        conta['balance'] += amount
        save_json(FILES['transactions'], transactions)
        save_json(FILES['accounts'], accounts)
        st.success('Lançamento salvo com sucesso!')

    if transactions:
        df = pd.DataFrame(transactions)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date', ascending=False)
        st.dataframe(df)
    else:
        st.info('Nenhuma transação ainda.')

# ===================== RECORRÊNCIAS =====================
elif menu == '🔁 Recorrências':
    st.subheader('Despesas e Receitas Recorrentes')

    with st.form('nova_rec'):
        nome = st.text_input('Nome da Recorrência')
        tipo = st.selectbox('Tipo', ['Despesa', 'Receita'])
        valor = st.number_input('Valor', step=0.01)
        categoria = st.text_input('Categoria')
        intervalo = st.selectbox('Frequência', ['Mensal', 'Semanal', 'Anual'])
        inicio = st.date_input('Início', date.today())
        salvar = st.form_submit_button('Salvar Recorrência')
        if salvar and nome:
            nova = {
                'id': get_next_id(recurrences),
                'name': nome,
                'type': tipo.lower(),
                'amount': valor,
                'category': categoria,
                'frequency': intervalo.lower(),
                'start_date': str(inicio)
            }
            recurrences.append(nova)
            save_json(FILES['recurrences'], recurrences)
            st.success('Recorrência adicionada com sucesso!')

    if recurrences:
        st.dataframe(pd.DataFrame(recurrences))
    else:
        st.info('Nenhuma recorrência cadastrada.')
