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
                for idx, row in df_new.iterrows():
                    row_dict = row.to_dict()
                    row_dict['id'] = next_id
                    next_id += 1
                    current_data.append(row_dict)
                save_json(FILES[tabela_tipo], current_data)
                st.success(f'{len(df_new)} registros adicionados a {tabela_tipo}.')
            else:
                df_new['id'] = range(1, len(df_new)+1)
                save_json(FILES[tabela_tipo], df_new.to_dict(orient='records'))
                st.warning(f'{tabela_tipo} substituído por novo conjunto ({len(df_new)} registros).')

# ================= OUTROS MENUS (resumidos) =================
elif menu == '🏦 Contas':
    st.write('⚙️ Gerenciamento de contas — igual versão anterior')
elif menu == '💳 Cartões':
    st.write('⚙️ Gerenciamento de cartões — igual versão anterior')
elif menu == '💸 Transações':
    st.write('⚙️ Lançamentos — igual versão anterior')
elif menu == '🔁 Recorrências':
    st.write('⚙️ Recorrências — igual versão anterior')
elif menu == '🏷️ Categorias':
    st.write('⚙️ Categorias — igual versão anterior')
