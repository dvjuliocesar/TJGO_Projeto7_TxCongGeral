# Bibliotecas
import pandas as pd
import numpy as np
import glob


# Carregar e concatenar os dados dos processos judiciais da pasta uploads
# Listar os arquivos CSV na pasta 'uploads'
arquivo_csv = glob.glob('uploads/processos_*.csv')

# Carregar os arquivos CSV e concatenar em um único DataFrame
dfs = []
for arquivo in arquivo_csv:
    # Extrair o ano do nome do arquivo
    ano = int(arquivo.split('_')[-1].split('.')[0])
    df_ano = pd.read_csv(arquivo, sep=',', encoding='utf-8')
    df_ano['ano_arquivo'] = ano  # Adicionar coluna com o ano do arquivo
    dfs.append(df_ano)

df = pd.concat(dfs, ignore_index=True)

# Verificar o nome correto das colunas (pode haver diferenças de acentuação ou espaços)
colunas = df.columns.tolist()

# Encontrar as colunas de data corretamente
coluna_serventia = [col for col in colunas if 'serventia' in col.lower()][0]
coluna_distribuicao = [col for col in colunas if 'data_distribuicao' in col.lower()][0]
coluna_baixa = [col for col in colunas if 'data_baixa' in col.lower()][0]
coluna_area_acao = [col for col in colunas if 'nome_area_acao' in col.lower()][0]
coluna_processo_id = [col for col in colunas if 'processo' in col.lower()][0]
coluna_comarca = [col for col in colunas if 'comarca' in col.lower()][0]

# Renomear colunas para garantir consistência
df = df.rename(columns={
coluna_distribuicao: 'data_distribuicao',
coluna_baixa: 'data_baixa',
coluna_area_acao: 'nome_area_acao',
coluna_processo_id: 'processo',
coluna_comarca: 'comarca',
coluna_serventia: 'serventia'
})

# Converter colunas de data para datetime com tratamento de erros
df['data_distribuicao'] = pd.to_datetime(df['data_distribuicao'], errors='coerce')
df['data_baixa'] = pd.to_datetime(df['data_baixa'], errors='coerce')

# Comarcas disponíveis
comarcas_disponiveis = sorted(df['comarca'].unique())

# Anos disponíveis
anos_disponiveis = sorted(df['data_distribuicao'].dt.year.unique())

 # Filtrar pela comarca
df_comarca = df[df['comarca']]

# Filtrar processos distribuídos no ano selecionado
df_ano = df_comarca[df_comarca['data_distribuicao'].dt.year]

# Agrupar por nome_area_acao
estatisticas = df_ano.groupby(['nome_area_acao', 'comarca','serventia']).agg(
    Distribuídos=('data_distribuicao', 'count') # Quantidade de datas distribuídas
).reset_index()

# Calcular baixados no ano
baixados_no_ano = df_comarca[
    (df_comarca['data_baixa'].dt.year) & 
    (df_comarca['data_baixa'].notna())
]

# Agrupar baixados da mesma forma que os distribuídos
baixados_por_area = baixados_no_ano.groupby(['nome_area_acao', 'comarca','serventia']).size()

# Mesclar corretamente com estatisticas
estatisticas = estatisticas.merge(
    baixados_por_area.rename('Baixados'), 
    on=['nome_area_acao', 'comarca','serventia'], 
    how='left'
).fillna(0)

# Calcular pendentes
pendentes_por_area = df_ano[df_ano['data_baixa'].isna()].groupby(
    ['nome_area_acao', 'comarca','serventia']
).size()

estatisticas = estatisticas.merge(
    pendentes_por_area.rename('Pendentes'), 
    on=['nome_area_acao', 'comarca', 'serventia'], 
    how='left'
).fillna(0).astype({'Pendentes': 'int'})

# Calcular taxa de congestionamento no ano
estatisticas['Taxa de Congestionamento (%)'] = (
    (estatisticas['Pendentes'] / (estatisticas['Pendentes'] + estatisticas['Baixados'])) * 100
).fillna(0).round(2)

print(estatisticas.head(10))


