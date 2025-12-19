# Importando bibliotecas
import numpy as np
import pandas as pd
import plotly.express as px
import glob

class ProcessosAnalisador:
    def __init__(self, arquivo_csv):
       
        self.df = self._carregar_dados(arquivo_csv)
    
    def _carregar_dados(self, arquivo_csv):
        # 1) Carregar e concatenar os dados dos processos judiciais da pasta uploads
        # Listar os arquivos CSV na pasta 'uploads'
        arquivo_csv = glob.glob('uploads/processos_*.csv')

        # Carregar os arquivos CSV e concatenar em um único DataFrame
        dfs = []
        for arquivo in arquivo_csv:  # lista/iterável com os caminhos tipo 'processos_1.csv', 'processos_2.csv', ...
            df_ano = pd.read_csv(arquivo, sep=',', encoding='utf-8')
            dfs.append(df_ano)

        df = pd.concat(dfs, ignore_index=True)

        # Verificar o nome correto das colunas (pode haver diferenças de acentuação ou espaços)
        colunas = df.columns.tolist()
        
        # Encontrar as colunas de data corretamente
        coluna_serventia = [col for col in colunas if 'serventia' in col.lower()][0]
        coluna_distribuicao = [col for col in colunas if 'data_distribuicao' in col.lower()][0]
        coluna_baixa = [col for col in colunas if 'data_baixa' in col.lower()][0]
        coluna_area_acao = [col for col in colunas if 'nome_area_acao' in col.lower()][0]
        coluna_processo_id = [col for col in colunas if 'numero' in col.lower()][0]
        coluna_comarca = [col for col in colunas if 'comarca' in col.lower()][0]
        
        # Renomear colunas para garantir consistência
        df = df.rename(columns={
            coluna_distribuicao: 'data_distribuicao',
            coluna_baixa: 'data_baixa',
            coluna_area_acao: 'nome_area_acao',
            coluna_processo_id: 'numero',
            coluna_comarca: 'comarca',
            coluna_serventia: 'serventia'
        })
        
        # Converter colunas de data para datetime com tratamento de erros
        df['data_distribuicao'] = pd.to_datetime(df['data_distribuicao'], errors='coerce')
        df['data_baixa'] = pd.to_datetime(df['data_baixa'], errors='coerce')
        
        return df
    
    def obter_comarcas_disponiveis(self):
        """
        Retorna as comarcas disponíveis
        """
        return sorted(self.df['comarca'].dropna().astype(str).unique())
    
    def obter_anos_disponiveis(self):
        """
        Retorna os anos disponíveis na coluna de data de distribuição
        """
        return sorted(self.df['data_baixa'].dt.year.unique())
    
    def calcular_estatisticas(self, comarca, ano_selecionado):
        """
        Calcula as estatísticas por área de ação para o ano selecionado
        """

        # Filtrar pela comarca
        df_comarca = self.df[self.df['comarca'] == comarca]
        
        # Filtrar processos distribuídos no ano selecionado
        df_ano = df_comarca[df_comarca['data_distribuicao'].dt.year == ano_selecionado]
        
        # Agrupar por nome_area_acao
        estatisticas = df_ano.groupby(['nome_area_acao', 'comarca','serventia']).agg(
            Distribuídos=('data_distribuicao', 'count') # Quantidade de datas distribuídas
        ).reset_index().astype({'Distribuídos': 'int'})
        
        # Calcular baixados no ano
        baixados_no_ano = df_comarca[
            (df_comarca['data_baixa'].dt.year == ano_selecionado) & 
            (df_comarca['data_baixa'].notna())
        ]
        
        # Agrupar baixados da mesma forma que os distribuídos
        baixados_por_area = baixados_no_ano.groupby(['nome_area_acao', 'comarca','serventia']).size()
        
        # Mesclar corretamente com estatisticas
        estatisticas = estatisticas.merge(
            baixados_por_area.rename('Baixados'), 
            on=['nome_area_acao', 'comarca','serventia'], 
            how='left'
        ).fillna(0).astype({'Baixados': 'int'})
        
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
        soma_pend_baix = estatisticas['Pendentes'] + estatisticas['Baixados']
        estatisticas['Taxa de Congestionamento (%)'] = np.where(
            soma_pend_baix > 0,
            (estatisticas['Pendentes'] / soma_pend_baix) * 100,
            0
        ).round(2)

        # Adicionar linha de totais
        totais = {
            'nome_area_acao': 'TOTAL',
            'comarca': '',
            'serventia':'',
            'Distribuídos': estatisticas['Distribuídos'].sum(),
            'Baixados': estatisticas['Baixados'].sum(),
            'Pendentes': estatisticas['Pendentes'].sum(),
        }

        # Evitar divisão por zero
        if (totais['Pendentes'] + totais['Baixados']) > 0:
            totais['Taxa de Congestionamento (%)'] = round(
                (totais['Pendentes'] / (totais['Pendentes'] + totais['Baixados'])) * 100, 2
            )
        else:
            totais['Taxa de Congestionamento (%)'] = 0.00

        # Adicionar a linha de totais ao DataFrame
        estatisticas = pd.concat([estatisticas, pd.DataFrame([totais])], ignore_index=True)
                
        return estatisticas
    
    # Gráfico de Barras Filtrados por Ano:
    def plotar_graficos_ano(self, ano_selecionado): 

        df_grafico = self.df
        df_grafico = df_grafico[['processo','nome_area_acao', 'comarca', 'data_distribuicao', 'data_baixa']]
        df_grafico['data_distribuicao'] = pd.to_datetime(df_grafico['data_distribuicao'], errors='coerce')
        df_grafico['data_baixa'] = pd.to_datetime(df_grafico['data_baixa'], errors='coerce')
        df_grafico['ano_baixa'] = df_grafico['data_baixa'].dt.year

        # Baixar dados do ano selecionado
        baixados_por_area = df_grafico[
                (df_grafico['data_baixa'].dt.year == ano_selecionado) & 
                (df_grafico['data_baixa'].notna())].groupby(
                ['nome_area_acao', 'comarca']).size()
        
        # Pendentes no ano selecionado
        pendentes_por_area = df_grafico[
                (df_grafico['data_distribuicao'].dt.year == ano_selecionado) & 
                (df_grafico['data_baixa'].isna())].groupby(
                ['nome_area_acao', 'comarca']).size()
        
        # Taxa de congestionamento
        taxa_cong = (pendentes_por_area / (pendentes_por_area + baixados_por_area)) * 100
        taxa_cong = taxa_cong.fillna(0).round(2)
        taxa_cong = taxa_cong.reset_index(name='Taxa de Congestionamento (%)')
        taxa_cong['Taxa de Congestionamento (%)'] = taxa_cong['Taxa de Congestionamento (%)'].astype(float)
        
        # Adiciona uma coluna com rótulo formatado
        taxa_cong['label_text'] = taxa_cong[
            'Taxa de Congestionamento (%)'].apply(lambda x: f'{x:.2f}%')

        # Gráfico de barras
        fig_barras = px.bar(
            taxa_cong,
            x='comarca',
            y=['Taxa de Congestionamento (%)'],
            color='nome_area_acao',
            barmode='group',
            title=f'Taxa de Congestionamento - {ano_selecionado}',
            labels={'Taxa de Congestionamento (%)': 'Taxa de Congestionamento (%)', 
                    'nome_area_acao': 'Área de Ação'}
            #color_discrete_map=color_map
        )
        
        # Força os rótulos a aparecerem dentro ou fora, conforme necessário
        fig_barras.update_traces(
            textposition='auto',  # Plotly decide o melhor lugar
            textfont=dict(size=12, color='black'),  # você pode ajustar
            insidetextanchor='start'
        )

        fig_barras.update_layout(
            yaxis_title='Taxa de Congestionamento (%)',
            uniformtext_minsize=8,
            uniformtext_mode='show',
            legend_title_text='Área de Ação por Comarca'
        )
        return fig_barras
    
    # Gráfico de Linhas Filtrados por Comarca e Área de Ação
    def plotar_graficos_comarca(self, comarca): 
        
        MAX_ANO = 2024
        
        # Base preparada
        df_grafico = self.df[['numero', 'nome_area_acao', 'comarca',
                            'data_distribuicao', 'data_baixa']].copy()

        df_grafico['data_distribuicao'] = pd.to_datetime(df_grafico['data_distribuicao'], errors='coerce')
        df_grafico['data_baixa'] = pd.to_datetime(df_grafico['data_baixa'], errors='coerce')

        # Filtro (case-insensitive, ignora espaços)
        alvo = (str(comarca) or '').strip().casefold()
        df = df_grafico[df_grafico['comarca'].astype(str).str.strip().str.casefold() == alvo]

        if df.empty:
            fig = px.line(title=f'Sem dados para a comarca: {comarca}')
            fig.update_layout(xaxis_title='Ano', yaxis_title='Taxa de Congestionamento (%)', yaxis_range=[0,100])
            return fig

        df['ano_distribuicao'] = df['data_distribuicao'].dt.year
        df['ano_baixa'] = df['data_baixa'].dt.year

        # Contagens por ano
        # Pendentes: distribuídos no ano e sem baixa
        pend = (df[(df['data_baixa'].isna()) & (df['ano_distribuicao'] <= MAX_ANO)]
            .groupby(['comarca','nome_area_acao','ano_distribuicao'])
            .size().reset_index(name='pendentes')
            .rename(columns={'ano_distribuicao':'ano'}))

        # Baixados: com baixa no ano
        baix = (df[(df['data_baixa'].notna()) & (df['ano_baixa'] <= MAX_ANO)] 
            .groupby(['comarca','nome_area_acao','ano_baixa'])
            .size().reset_index(name='baixados')
            .rename(columns={'ano_baixa':'ano'}))
        
        base = pend.merge(baix, on=['comarca','nome_area_acao','ano'], how='outer').fillna(0)

        # Taxa de Congestionamento
        soma = base['pendentes'] + base['baixados']
        base['Taxa de Congestionamento (%)'] = np.where(
            soma > 0,
            (base['pendentes'] / soma) * 100,
            np.nan
        ).round(2)

        # Limpeza final para o plot
        df_plot = (base[['comarca','nome_area_acao','ano','Taxa de Congestionamento (%)']]
           .dropna(subset=['ano'])
           .copy())
        
        # Garantir tipo inteiro para o eixo X
        df_plot['ano'] = df_plot['ano'].astype(int)
        df_plot = df_plot[df_plot['ano'] <= MAX_ANO]

        # Ordenação para um X crescente
        df_plot = df_plot.sort_values(['nome_area_acao', 'ano'])

        # Anos disponíveis para o eixo X (apenas desta comarca)
        anos_disponiveis = sorted(pd.unique(pd.concat([
            df.loc[df['ano_distribuicao'] <= MAX_ANO, 'ano_distribuicao'],
            df.loc[df['ano_baixa'] <= MAX_ANO, 'ano_baixa']
            ]).dropna().astype(int)))

        # Gráfico de Linhas
        fig_linha = px.line(
            df_plot,
            x='ano',
            y='Taxa de Congestionamento (%)',
            color='nome_area_acao',
            markers=True,
            title=f'Taxa de Congestionamento por Ano — {comarca}',
            labels={'ano': 'Ano', 'nome_area_acao': 'Área de Ação'}
        )
        fig_linha.update_traces(
            mode='lines+markers',
            hovertemplate='Ano: %{x}<br>Área de Ação: %{fullData.name}<br>Taxa: %{y:.2f}%<extra></extra>'
        )
        fig_linha.update_layout(
            xaxis_title='Ano',
            yaxis_title='Taxa de Congestionamento (%)',
            legend_title_text='Área de Ação',
            yaxis_range=[0, 100],
            margin=dict(l=40, r=20, t=60, b=40)
        )

        # Faz o eixo X mostrar exatamente os anos disponíveis
        fig_linha.update_xaxes(tickmode='array', tickvals=anos_disponiveis, ticktext=[str(a) for a in anos_disponiveis])
        
        return fig_linha
       
    # Gráfico de Linhas Filtrados por Comarca e Serventia
    def plotar_graficos_comarca_serventia(self, comarca): 
        
        MAX_ANO = 2024
        
        # Base preparada
        df_grafico = self.df[['numero', 'serventia', 'comarca',
                            'data_distribuicao', 'data_baixa']].copy()

        df_grafico['data_distribuicao'] = pd.to_datetime(df_grafico['data_distribuicao'], errors='coerce')
        df_grafico['data_baixa'] = pd.to_datetime(df_grafico['data_baixa'], errors='coerce')

        # Filtro (case-insensitive, ignora espaços)
        alvo = (str(comarca) or '').strip().casefold()
        df = df_grafico[df_grafico['comarca'].astype(str).str.strip().str.casefold() == alvo]

        if df.empty:
            fig = px.line(title=f'Sem dados para a comarca: {comarca}')
            fig.update_layout(xaxis_title='Ano', yaxis_title='Taxa de Congestionamento (%)', yaxis_range=[0,100])
            return fig

        df['ano_distribuicao'] = df['data_distribuicao'].dt.year
        df['ano_baixa'] = df['data_baixa'].dt.year

        # Contagens por ano
        # Pendentes: distribuídos no ano e sem baixa
        pend = (df[(df['data_baixa'].isna()) & (df['ano_distribuicao'] <= MAX_ANO)]
            .groupby(['comarca','serventia','ano_distribuicao'])
            .size().reset_index(name='pendentes')
            .rename(columns={'ano_distribuicao':'ano'}))

        # Baixados: com baixa no ano
        baix = (df[(df['data_baixa'].notna()) & (df['ano_baixa'] <= MAX_ANO)] 
            .groupby(['comarca','serventia','ano_baixa'])
            .size().reset_index(name='baixados')
            .rename(columns={'ano_baixa':'ano'}))
        
        base = pend.merge(baix, on=['comarca','serventia','ano'], how='outer').fillna(0)

        # Taxa de Congestionamento
        soma = base['pendentes'] + base['baixados']
        base['Taxa de Congestionamento (%)'] = np.where(
            soma > 0,
            (base['pendentes'] / soma) * 100,
            np.nan
        ).round(2)

        # Limpeza final para o plot
        df_plot = (base[['comarca','serventia','ano','Taxa de Congestionamento (%)']]
           .dropna(subset=['ano'])
           .copy())
        
        # Garantir tipo inteiro para o eixo X
        df_plot['ano'] = df_plot['ano'].astype(int)
        df_plot = df_plot[df_plot['ano'] <= MAX_ANO]

        # Ordenação para um X crescente
        df_plot = df_plot.sort_values(['serventia', 'ano'])

        # Anos disponíveis para o eixo X (apenas desta comarca)
        anos_disponiveis = sorted(pd.unique(pd.concat([
            df.loc[df['ano_distribuicao'] <= MAX_ANO, 'ano_distribuicao'],
            df.loc[df['ano_baixa'] <= MAX_ANO, 'ano_baixa']
            ]).dropna().astype(int)))

        # Gráfico de Linhas
        fig_linha = px.line(
            df_plot,
            x='ano',
            y='Taxa de Congestionamento (%)',
            color='serventia',
            markers=True,
            title=f'Taxa de Congestionamento por Ano — {comarca}',
            labels={'ano': 'Ano', 'serventia': 'Serventia'}
        )
        fig_linha.update_traces(
            mode='lines+markers',
            hovertemplate='Ano: %{x}<br>Serventia: %{fullData.name}<br>Taxa: %{y:.2f}%<extra></extra>'
        )
        fig_linha.update_layout(
            xaxis_title='Ano',
            yaxis_title='Taxa de Congestionamento (%)',
            legend_title_text='Serventia',
            yaxis_range=[0, 100],
            margin=dict(l=40, r=20, t=60, b=40)
        )

        # Faz o eixo X mostrar exatamente os anos disponíveis
        fig_linha.update_xaxes(tickmode='array', tickvals=anos_disponiveis, ticktext=[str(a) for a in anos_disponiveis])
        
        return fig_linha