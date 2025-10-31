import streamlit as st
import json, os
import pandas as pd
from datetime import date

# ===== Diretórios e arquivos =====
data_dir = 'data'
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

FILES = {
    'accounts': os.path.join(data_dir, 'accounts.json'),
    'cards': os.path.join(data_dir, 'cards.json'),
    'transactions': os.path.join(data_dir, 'transactions.json'),
    'recurrences': os.path.join(data_dir, 'recurrences.json'),
    'categories': os.path.join(data_dir, 'categories.json')
}

# ===== Funções =====
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

# ===== Dados =====
accounts = load_json(FILES['accounts'])
cards = load_json(FILES['cards'])
transactions = load_json(FILES['transactions'])
recurrences = load_json(FILES['recurrences'])
categories = load_json(FILES['categories'])

# ===== Categorias padrão =====
if not categories:
    categories = [
        {'id': 1, 'name': 'Alimentação', 'type': 'expense'},
        {'id': 2, 'name': 'Transporte', 'type': 'expense'},
        {'id': 3, 'name': 'Lazer', 'type': 'expense'},
        {'id': 4, 'name': 'Saúde', 'type': 'expense'},
        {'id': 5, 'name': 'Salário', 'type': 'income'},
        {'id': 6, 'name': 'Investimentos', 'type': 'income'}
    ]
    save_json(FILES['categories'], categories)

# ===== Config =====
st.set_page_config(page_title='Finance App', layout='wide')
st.title('💰 Finance App — Gestão Financeira Completa')
menu = st.sidebar.radio('Navegação', ['📈 Dashboard', '🏦 Contas', '💳 Cartões', '💸 Transações', '🔁 Recorrências', '🏷️ Categorias', '📤 Exportar / Importar'])

# ================= DASHBOARD =================
if menu == '📈 Dashboard':
    st.subheader('📅 Saldo Consolidado Mensal')
    df = pd.DataFrame(transactions)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.to_period('M').astype(str)
        monthly = df.groupby('month')['amount'].sum().reset_index()
        monthly['saldo_acumulado'] = monthly['amount'].cumsum()
        st.line_chart(monthly.set_index('month')['saldo_acumulado'])

        st.markdown('---')
        st.subheader('📊 Distribuição de Despesas por Categoria (%)')
        df_exp = df[df['amount'] < 0]
        if not df_exp.empty:
            cat_data = df_exp.groupby('category')['amount'].sum().abs().reset_index()
            cat_data['percent'] = cat_data['amount'] / cat_data['amount'].sum() * 100
            st.dataframe(cat_data)
            st.bar_chart(cat_data.set_index('category')['percent'])
        else:
            st.info('Nenhuma despesa cadastrada.')
    else:
        st.info('Nenhum dado ainda.')

# ================= CONTAS =================
elif menu == '🏦 Contas':
    st.subheader('Gerenciamento de Contas')
    with st.form('nova_conta'):
        nome = st.text_input('Nome da Conta')
        saldo = st.number_input('Saldo Inicial', step=0.01, value=0.0)
        criar = st.form_submit_button('Adicionar Conta')
        if criar and nome:
            accounts.append({'id': get_next_id(accounts), 'name': nome, 'balance': saldo})
            save_json(FILES['accounts'], accounts)
            st.success('Conta criada!')

    if accounts:
        df_acc = pd.DataFrame(accounts)
        st.dataframe(df_acc)
        editar_id = st.selectbox('Selecione conta para editar/excluir', df_acc['id'])
        conta = next(a for a in accounts if a['id'] == editar_id)
        novo_nome = st.text_input('Nome', conta['name'])
        novo_saldo = st.number_input('Saldo', value=float(conta['balance']))
        if st.button('Salvar Alterações'):
            conta['name'] = novo_nome
            conta['balance'] = novo_saldo
            save_json(FILES['accounts'], accounts)
            st.success('Atualizado!')
        if st.button('Excluir Conta'):
            accounts = [a for a in accounts if a['id'] != editar_id]
            save_json(FILES['accounts'], accounts)
            st.warning('Conta removida!')
    else:
        st.info('Nenhuma conta cadastrada.')

# ================= CARTÕES =================
elif menu == '💳 Cartões':
    st.subheader('Gerenciamento de Cartões de Crédito')
    with st.form('novo_cartao'):
        nome = st.text_input('Nome do Cartão')
        limite = st.number_input('Limite (R$)', value=1000.0)
        fechamento = st.number_input('Dia de Fechamento', min_value=1, max_value=28, value=10)
        vencimento = st.number_input('Dia de Vencimento', min_value=1, max_value=28, value=20)
        criar = st.form_submit_button('Adicionar')
        if criar and nome:
            cards.append({
                'id': get_next_id(cards),
                'name': nome,
                'limit': limite,
                'closing_day': fechamento,
                'due_day': vencimento,
                'invoice': 0
            })
            save_json(FILES['cards'], cards)
            st.success('Cartão adicionado!')

    if cards:
        df_cards = pd.DataFrame(cards)
        st.dataframe(df_cards)
        editar_id = st.selectbox('Selecione cartão', df_cards['id'])
        card = next(c for c in cards if c['id'] == editar_id)
        novo_nome = st.text_input('Nome', card['name'])
        novo_limite = st.number_input('Limite', value=float(card['limit']))
        novo_fech = st.number_input('Fechamento', min_value=1, max_value=28, value=int(card['closing_day']))
        novo_venc = st.number_input('Vencimento', min_value=1, max_value=28, value=int(card['due_day']))
        if st.button('Salvar Cartão'):
            card.update({'name': novo_nome, 'limit': novo_limite, 'closing_day': novo_fech, 'due_day': novo_venc})
            save_json(FILES['cards'], cards)
            st.success('Cartão atualizado!')
        if st.button('Excluir Cartão'):
            cards = [c for c in cards if c['id'] != editar_id]
            save_json(FILES['cards'], cards)
            st.warning('Cartão removido!')
    else:
        st.info('Nenhum cartão cadastrado.')

# ================= TRANSAÇÕES =================
elif menu == '💸 Transações':
    st.subheader('Lançamentos Financeiros')
    contas_nomes = [a['name'] for a in accounts]
    cartoes_nomes = [c['name'] for c in cards]
    categorias_nomes = [c['name'] for c in categories]

    with st.form('nova_tx'):
        tipo = st.selectbox('Tipo', ['Despesa', 'Receita'])
        origem = st.radio('Origem', ['Conta', 'Cartão de Crédito'])
        valor = st.number_input('Valor', min_value=0.01, step=0.01)
        categoria = st.selectbox('Categoria', categorias_nomes)
        descricao = st.text_input('Descrição')
        data_lcto = st.date_input('Data', date.today())

        origem_nome = None
        fatura_escolhida = None

        if origem == 'Conta':
            if contas_nomes:
                origem_nome = st.selectbox('Selecionar Conta', contas_nomes)
            else:
                st.warning('Nenhuma conta cadastrada!')
        else:
            if cartoes_nomes:
                origem_nome = st.selectbox('Selecionar Cartão', cartoes_nomes)
                cartao = next((c for c in cards if c['name'] == origem_nome), None)
                if cartao:
                    hoje = date.today()
                    mes_atual = hoje.month
                    ano_atual = hoje.year
                    fechamento = cartao['closing_day']
                    vencimento = cartao['due_day']

                    # Determina fatura atual e próxima
                    if hoje.day <= fechamento:
                        fatura_atual = date(ano_atual, mes_atual, vencimento)
                        fatura_prox = date(ano_atual if mes_atual < 12 else ano_atual + 1, mes_atual + 1 if mes_atual < 12 else 1, vencimento)
                    else:
                        fatura_atual = date(ano_atual if mes_atual < 12 else ano_atual + 1, mes_atual + 1 if mes_atual < 12 else 1, vencimento)
                        fatura_prox = date(ano_atual if mes_atual < 11 else ano_atual + 1, mes_atual + 2 if mes_atual < 11 else (mes_atual + 2) % 12, vencimento)

                    faturas = {
                        f"Fatura Atual ({fatura_atual.strftime('%b/%Y')})": fatura_atual.strftime('%Y-%m-%d'),
                        f"Próxima Fatura ({fatura_prox.strftime('%b/%Y')})": fatura_prox.strftime('%Y-%m-%d')
                    }
                    fatura_escolhida = st.selectbox('Selecione a Fatura', list(faturas.keys()))
            else:
                st.warning('Nenhum cartão cadastrado!')

        enviar = st.form_submit_button('Salvar')

    if enviar and origem_nome:
        amount = valor if tipo == 'Receita' else -valor
        invoice_date = faturas[fatura_escolhida] if fatura_escolhida else None
        nova_tx = {
            'id': get_next_id(transactions),
            'date': str(data_lcto),
            'type': tipo.lower(),
            'category': categoria,
            'description': descricao,
            'amount': amount,
            'origin': origem_nome,
            'invoice_date': invoice_date
        }
        transactions.append(nova_tx)

        if origem == 'Conta':
            conta = next(a for a in accounts if a['name'] == origem_nome)
            conta['balance'] += amount
            save_json(FILES['accounts'], accounts)
        else:
            cartao = next(c for c in cards if c['name'] == origem_nome)
            cartao['invoice'] += abs(amount)
            save_json(FILES['cards'], cards)

        save_json(FILES['transactions'], transactions)
        st.success('Transação salva com sucesso!')

    if transactions:
        df = pd.DataFrame(transactions)
        st.dataframe(df.sort_values('date', ascending=False))
    else:
        st.info('Nenhuma transação ainda.')

# ================= RECORRÊNCIAS =================
elif menu == '🔁 Recorrências':
    st.subheader('Gerenciar Despesas e Receitas Recorrentes')
    with st.form('nova_rec'):
        nome = st.text_input('Nome da Recorrência')
        tipo = st.selectbox('Tipo', ['Despesa', 'Receita'])
        valor = st.number_input('Valor', step=0.01)
        categoria = st.selectbox('Categoria', [c['name'] for c in categories])
        frequencia = st.selectbox('Frequência', ['Mensal', 'Semanal', 'Anual'])
        inicio = st.date_input('Data de Início', date.today())
        criar = st.form_submit_button('Adicionar')
        if criar and nome:
            recurrences.append({
                'id': get_next_id(recurrences),
                'name': nome,
                'type': tipo.lower(),
                'amount': valor,
                'category': categoria,
                'frequency': frequencia.lower(),
                'start_date': str(inicio)
            })
            save_json(FILES['recurrences'], recurrences)
            st.success('Recorrência adicionada!')

    if recurrences:
        df_rec = pd.DataFrame(recurrences)
        st.dataframe(df_rec)
        del_id = st.selectbox('Excluir recorrência ID', df_rec['id'])
        if st.button('Excluir recorrência'):
            recurrences = [r for r in recurrences if r['id'] != del_id]
            save_json(FILES['recurrences'], recurrences)
            st.warning('Recorrência removida!')
    else:
        st.info('Nenhuma recorrência cadastrada.')

# ================= CATEGORIAS =================
elif menu == '🏷️ Categorias':
    st.subheader('Gerenciar Categorias')
    with st.form('nova_cat'):
        nome_cat = st.text_input('Nome da Categoria')
        tipo_cat = st.selectbox('Tipo', ['Despesa', 'Receita'])
        add = st.form_submit_button('Adicionar')
        if add and nome_cat:
            categories.append({'id': get_next_id(categories), 'name': nome_cat, 'type': tipo_cat.lower()})
            save_json(FILES['categories'], categories)
            st.success('Categoria adicionada!')
    st.dataframe(pd.DataFrame(categories))

# ================= EXPORTAÇÃO / IMPORTAÇÃO =================
elif menu == '📤 Exportar / Importar':
    st.subheader('Download e Upload de Registros')

    # ---- Download ----
    st.write('### 📥 Baixar todos os dados')
    export_data = {
        'accounts': accounts,
        'cards': cards,
        'transactions': transactions,
        'recurrences': recurrences,
        'categories': categories
    }
    for key, data in export_data.items():
        if data:
            df_export = pd.DataFrame(data)
            csv = df_export.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label=f'Baixar {key}.csv', data=csv, file_name=f'{key}.csv', mime='text/csv')

    st.markdown('---')

    # ---- Upload ----
    st.write('### 📤 Enviar planilhas para atualização')
    uploaded_file = st.file_uploader('Selecione um arquivo CSV para adicionar/substituir dados', type=['csv'])
    tabela_tipo = st.selectbox('Tipo de tabela', list(FILES.keys()))
    acao = st.radio('Ação', ['Adicionar aos existentes', 'Substituir completamente'])

    if uploaded_file is not None:
        df_new = pd.read_csv(uploaded_file)
        st.write('Prévia dos dados:')
        st.dataframe(df_new.head())
        if st.button('Aplicar upload'):
            current_data = load_json(FILES[tabela_tipo])
            if acao == 'Adicionar aos existentes':
                next_id = get_next_id(current_data)
                for _, row in df_new.iterrows():
                    r = row.to_dict()
                    r['id'] = next_id
                    next_id += 1
                    current_data.append(r)
                save_json(FILES[tabela_tipo], current_data)
                st.success(f'{len(df_new)} registros adicionados a {tabela_tipo}.')
            else:
                df_new['id'] = range(1, len(df_new) + 1)
                save_json(FILES[tabela_tipo], df_new.to_dict(orient='records'))
                st.warning(f'{tabela_tipo} substituído ({len(df_new)} registros).')



