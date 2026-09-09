from pathlib import Path
import unicodedata

import streamlit as st
import pandas as pd
try:
    import plotly.express as px
except ImportError:
    import plotly_express as px
import streamlit.components.v1 as components

st.set_page_config(layout="wide", page_title="IANNI Agropecuária - Análise Geral de Competências")

logo_path = Path(__file__).with_name("IANNIlogo_ianni_agropecuaria.png.png")

# 1. CSS Global de Impressão (aplicado apenas ao imprimir)
st.markdown("""
<style>
@media print {
    @page {
        size: A4 portrait;
        margin: 8mm;
    }

    html, body {
        margin: 0 !important;
        padding: 0 !important;
    }

    /* Ocultar barra lateral inteira */
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* Ocultar cabeçalho, rodapé e barra de ferramentas nativos do Streamlit */
    header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {
        display: none !important;
    }
    
    /* Ocultar botões, menus interativos (Selectbox) e caixas de seleção (Checkbox) do Streamlit */
    .stSelectbox, .stCheckbox, .stButton, .stDownloadButton, [data-testid="stForm"] {
        display: none !important;
    }
    
    /* Ocultar componentes de script do botão de impressão e iframes de terceiros */
    iframe, div[data-testid="stHtml"] {
        display: none !important;
    }
    
    /* Expandir o conteúdo principal para ocupar a largura máxima do papel */
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }

    [data-testid="stPlotlyChart"] {
        margin: 0 !important;
    }

    [data-testid="stImage"] img {
        max-height: 55px !important;
        width: auto !important;
    }

    h1 {
        font-size: 20pt !important;
        margin: 0 !important;
    }

    h3 {
        font-size: 12pt !important;
        margin: 0 !important;
    }

    h2 {
        font-size: 14pt !important;
        margin: 4px 0 !important;
    }
}
</style>
""", unsafe_allow_html=True)

# Leitura da base de dados geral
nome_csv = "Diretoria Geral.csv"
pasta_script = Path(__file__).resolve().parent
arquivo_csv = pasta_script / nome_csv

if not arquivo_csv.is_file():
    st.error(
        "Não foi possível localizar a base de dados CSV. "
        f"Coloque '{nome_csv}' na mesma pasta deste arquivo:\n{arquivo_csv}"
    )
    st.stop()

df = pd.read_csv(arquivo_csv, sep=",", encoding="utf-8-sig")

# Normaliza os nomes para aceitar os cabeçalhos acentuados do CSV.
def normalizar_coluna(nome):
    nome = unicodedata.normalize("NFKD", str(nome))
    return "".join(caractere for caractere in nome if not unicodedata.combining(caractere)).strip().upper()


df.columns = [normalizar_coluna(coluna) for coluna in df.columns]
df = df.rename(columns={
    "AVALIADO": "Nome",
    "COMPETENCIA": "Competencia",
    "AVALIADOR": "Avaliador",
    "NOTA GESTOR": "Média Gestor"
})

colunas_obrigatorias = {
    "Nome": "",
    "Competencia": "",
    "Avaliador": "",
    "Média Gestor": pd.NA
}
for coluna, valor_padrao in colunas_obrigatorias.items():
    if coluna not in df.columns:
        df[coluna] = valor_padrao

df = df.sort_values("Nome")

# Mapeamento e padronização das colunas
df["Colab"] = df["Nome"]
df["Compet"] = df["Competencia"]
df["Avaliar"] = df["Avaliador"]
df["Gestor"] = pd.to_numeric(df["Média Gestor"], errors="coerce")

# Inicializar estado de impressão se não existir
if "printing" not in st.session_state:
    st.session_state.printing = False

def desmarcar_checkboxes():
    st.session_state.mostrar_comentarios = False
    st.session_state.avaliacao_equipe = False
    st.session_state.media_avaliadores = False

def selecionar_avaliador():
    desmarcar_checkboxes()
    avaliador_selecionado = st.session_state.get("nome_avaliador")
    nomes_do_avaliador = sorted(
        df.loc[df["Avaliador"] == avaliador_selecionado, "Colab"].dropna().unique()
    )
    st.session_state["nome_avaliado"] = nomes_do_avaliador[0] if nomes_do_avaliador else None

# Cores padronizadas para os tipos de avaliação
color_discrete_map = {
    "Gestor": "#1565C0"
}

# -------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------
st.sidebar.write("""
## Painel Geral - IANNI Agropecuária
""")

avaliadores_unicos = sorted([str(a) for a in df["Avaliador"].dropna().unique() if str(a).strip() != ""])
nome_avaliador = st.sidebar.selectbox(
    "Avaliador",
    avaliadores_unicos,
    key="nome_avaliador",
    on_change=selecionar_avaliador
) if avaliadores_unicos else "Não informado"

df_opcoes = df[df["Avaliador"] == nome_avaliador]

nomes_disponiveis = sorted(df_opcoes["Colab"].dropna().unique())
if nomes_disponiveis:
    Nome = st.sidebar.selectbox(
        "Avaliados",
        nomes_disponiveis,
        index=0,
        key="nome_avaliado",
        on_change=desmarcar_checkboxes
    )
else:
    Nome = "Nenhum avaliado encontrado"
    st.sidebar.info("Nenhum avaliado encontrado para este avaliador.")

# Filtros e agregações do colaborador selecionado
df_filtered = df[df["Colab"] == Nome]
cargos_disponiveis = (
    df_filtered["CARGO"].dropna().astype(str).str.strip().unique()
    if "CARGO" in df_filtered.columns else []
)
cargo = cargos_disponiveis[0] if len(cargos_disponiveis) > 0 else "Não informado"
df_Média = df_filtered.groupby("Compet")[["Gestor"]].mean().round(decimals=1).reset_index()
aval = ["Gestor"]

# -------------------------------------------------------------
# CASO 1: MODO DE IMPRESSÃO (Layout limpo apenas com o solicitado)
# -------------------------------------------------------------
if st.session_state.printing:
    
    if st.button("⬅️ Voltar ao Painel", key="back_to_dashboard", type="secondary"):
        st.session_state.printing = False
        st.rerun()
            
    # Título do Relatório com Nome do Avaliado
    col_logo, col_titulo = st.columns([1.4, 4])
    with col_logo:
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
    with col_titulo:
        st.markdown("# IANNI Agropecuária\n### Análise Geral de Competência")
    st.markdown(
        f'<h3 style="text-align: center;">Colaborador Avaliado: <strong>{Nome}</strong></h3>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div style="text-align: center;">({cargo})</div>',
        unsafe_allow_html=True
    )
    st.markdown("---")
    
    # 1. Gráfico: Competências
    st.write("## Competências")
    fig_comp = px.bar(
        df_Média, 
        y="Gestor", 
        x="Compet", 
        barmode='group', 
        text="Gestor",
        color_discrete_map=color_discrete_map
    )
    fig_comp.update_traces(
        texttemplate="%{y:.1f}",
        textposition="outside",
        cliponaxis=False
    )
    fig_comp.update_layout(
        xaxis_title="Competências",
        yaxis_title="Médias",
        height=270,
        margin=dict(l=45, r=15, t=15, b=45)
    )
    
    plotly_config_comp = {
        'displaylogo': False,
        'toImageButtonOptions': {
            'format': 'png',
            'filename': f'competencias_{Nome.replace(" ", "_")}',
            'height': 300,
            'width': 500,
            'scale': 2
        }
    }
    col_grafico_esquerda, col_grafico, col_grafico_direita = st.columns([0.8, 2.4, 0.8])
    with col_grafico:
        st.plotly_chart(fig_comp, use_container_width=True, config=plotly_config_comp)
    
    st.markdown("---")
    
    # 2. Linhas para Anotações / Plano de Ação
    st.write("### Anotações")
    for i in range(4):
        st.markdown('<div style="border-bottom: 1px dotted #888; height: 24px; margin-bottom: 1px; width: 100%;"></div>', unsafe_allow_html=True)
        
    # Linha para data e assinatura de ciente
    st.markdown("""
    <div style="margin-top: 24px; display: flex; justify-content: space-between; font-family: sans-serif; font-size: 12px; page-break-inside: avoid; break-inside: avoid;">
        <div style="width: 45%; text-align: center;">
            <div style="border-bottom: 1px solid #444; margin-bottom: 8px; height: 30px;"></div>
            <span style="color: #333; font-weight: 500;">Assinatura do Colaborador (Ciente)</span>
        </div>
        <div style="width: 45%; text-align: center;">
            <div style="border-bottom: 1px solid #444; margin-bottom: 8px; height: 30px;"></div>
            <span style="color: #333; font-weight: 500;">Data: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Acionar diálogo de impressão após 1 segundo
    components.html(
        """
        <script>
            setTimeout(function() {
                window.parent.print();
            }, 1000);
        </script>
        """,
        height=0
    )

# -------------------------------------------------------------
# CASO 2: MODO PAINEL NORMAL (Todos os elementos interativos)
# -------------------------------------------------------------
else:
    col_logo, col_titulo = st.columns([1.4, 4])
    with col_logo:
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)
    with col_titulo:
        st.markdown("# IANNI Agropecuária\n### Análise Geral de Competência")
    
    if st.button("🖨️ IMPRIMIR", key="btn_imprimir_top", type="primary"):
        st.session_state.printing = True
        st.rerun()

    # 1. Primeiro Gráfico: Competências
    st.markdown(
        f'<h3 style="text-align: center;">Competências - <strong>{Nome}</strong></h3>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div style="text-align: center;">({cargo})</div>',
        unsafe_allow_html=True
    )

    fig_comp = px.bar(
        df_Média, 
        y="Gestor", 
        x="Compet", 
        barmode='group', 
        text="Gestor",
        color_discrete_map=color_discrete_map
    )
    fig_comp.update_traces(
        texttemplate="%{y:.1f}",
        textposition="outside",
        cliponaxis=False
    )
    fig_comp.update_layout(xaxis_title="Competências", yaxis_title="Médias")

    plotly_config_comp = {
        'displaylogo': False,
        'toImageButtonOptions': {
            'format': 'png',
            'filename': f'competencias_{Nome.replace(" ", "_")}',
            'height': 600,
            'width': 1000,
            'scale': 2
        }
    }
    st.plotly_chart(fig_comp, use_container_width=True, config=plotly_config_comp)

    # -------------------------------------------------------------
    # 2. Segundo Gráfico: Análise dos Avaliados por Competência
    st.write("## Análise dos Avaliados por Competência")
    
    perguntas_preenchidas = df_filtered[
        df_filtered["PERGUNTA"].fillna("").astype(str).str.strip() != ""
    ]
    competencias_disponiveis = sorted(perguntas_preenchidas["Compet"].dropna().unique())
    if len(competencias_disponiveis) > 0:
        unica_Competencia = st.selectbox(
            "Escolha a Competência",
            competencias_disponiveis,
            index=0,
            key=f"competencia_{Nome}"
        )
        df_perguntas = perguntas_preenchidas[
            perguntas_preenchidas["Compet"] == unica_Competencia
        ].copy()

        if not df_perguntas.empty:
            df_perguntas = df_perguntas[["PERGUNTA", "Média Gestor"]].rename(columns={
                "PERGUNTA": "Pergunta",
                "Média Gestor": "Nota do Gestor"
            })
            st.dataframe(df_perguntas, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma pergunta encontrada para a competência selecionada.")
    else:
        st.info("Nenhuma competência encontrada para a seleção atual.")

    mostrar_comentarios = st.checkbox("Exibir Comentário", key="mostrar_comentarios")
    if mostrar_comentarios:
        df_comentarios = df_filtered.copy()
        for coluna in ["COMENT_AVAL", "COMENT_AUTO"]:
            df_comentarios[coluna] = df_comentarios[coluna].fillna("").astype(str).str.strip()
        df_comentarios = df_comentarios[
            (df_comentarios["COMENT_AVAL"] != "")
            | (df_comentarios["COMENT_AUTO"] != "")
        ]

        if not df_comentarios.empty:
            df_comentarios = df_comentarios[["COMENT_AVAL", "COMENT_AUTO"]].drop_duplicates().rename(columns={
                "COMENT_AVAL": "Comentário do Avaliador",
                "COMENT_AUTO": "Comentário do Avaliado"
            })
            st.dataframe(df_comentarios, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum comentário encontrado.")

    # ---------------------------------------------------------------------------------
    # 3. Terceira Seção: Desempenho Geral dos Avaliados
    st.write("### Desempenho Geral dos Avaliados")

    AvalEquipe = st.checkbox(
        "Exibir avaliação geral / da equipe",
        key="avaliacao_equipe"
    )

    if AvalEquipe:
        df_equipe = df_opcoes
        
        df_MédiaSetor = (
            df_equipe.groupby("Nome")["Gestor"]
            .mean()
            .round(1)
            .reset_index()
            .sort_values("Gestor", ascending=False)
        )
        
        altura_grafico = max(500, len(df_MédiaSetor) * 35)
        
        fig_Setor = px.bar(
            df_MédiaSetor, 
            x="Gestor", 
            y="Nome", 
            orientation="h", 
            height=altura_grafico, 
            barmode='group', 
            text="Gestor",
            color_discrete_map=color_discrete_map
        )
        fig_Setor.update_traces(
            texttemplate="%{x:.1f}",
            textposition="outside",
            cliponaxis=False
        )
        fig_Setor.update_layout(
            xaxis_title="Média", 
            yaxis_title="Colaborador", 
            bargap=0.15, 
            bargroupgap=0.05,
            yaxis={
                "categoryorder": "array",
                "categoryarray": df_MédiaSetor["Nome"].tolist()[::-1]
            }
        )
        
        plotly_config_setor = {
            'displaylogo': False,
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'desempenho_geral_equipe',
                'height': altura_grafico,
                'width': 1000,
                'scale': 2
            }
        }
        st.plotly_chart(fig_Setor, use_container_width=True, config=plotly_config_setor)

    st.write("## Média Geral dos Avaliados por Equipe")
    exibir_media_avaliadores = st.checkbox(
        "Exibir média geral por Equipe",
        key="media_avaliadores"
    )

    if exibir_media_avaliadores:
        # ---------------------------------------------
        # Média geral dos avaliados agrupada por avaliador
        df_avaliadores = df.dropna(subset=["Avaliador", "Nome", "Gestor"]).copy()
        medias_avaliados = (
            df_avaliadores.groupby(["Avaliador", "Nome"], as_index=False)["Gestor"]
            .mean()
        )
        medias_por_avaliador = (
            medias_avaliados.groupby("Avaliador", as_index=False)["Gestor"]
            .mean()
            .round(2)
            .sort_values("Gestor", ascending=False)
        )

        fig_avaliadores = px.bar(
            medias_por_avaliador,
            x="Gestor",
            y="Avaliador",
            orientation="h",
            text="Gestor",
            labels={"Gestor": "Média Geral", "Avaliador": "Avaliador"},
            color_discrete_sequence=["#1565C0"]
        )
        fig_avaliadores.update_traces(
            texttemplate="%{x:.2f}",
            textposition="outside",
            cliponaxis=False
        )
        fig_avaliadores.update_layout(
            xaxis_title="Média Geral",
            yaxis_title="Avaliador",
            xaxis_range=[0, 5],
            yaxis={
                "categoryorder": "array",
                "categoryarray": medias_por_avaliador["Avaliador"].tolist()[::-1]
            },
            height=max(400, len(medias_por_avaliador) * 35),
            margin=dict(l=20, r=20, t=20, b=40)
        )
        st.plotly_chart(
            fig_avaliadores,
            use_container_width=True,
            config={"displaylogo": False}
        )

    st.write("## Ranking Geral dos Avaliados")
    exibir_ranking_geral = st.checkbox(
        "Exibir ranking geral dos avaliados",
        key="ranking_geral"
    )

    if exibir_ranking_geral:
        medias_por_avaliado = (
            df.dropna(subset=["Nome", "Gestor"])
            .groupby("Nome", as_index=False)["Gestor"]
            .mean()
            .round(2)
        )

        if not medias_por_avaliado.empty:
            melhores = medias_por_avaliado.nlargest(5, "Gestor").sort_values("Gestor")
            piores = medias_por_avaliado.nsmallest(5, "Gestor").sort_values("Gestor", ascending=False)

            col_melhores, col_piores = st.columns(2)
            with col_melhores:
                st.markdown('<h3 style="text-align: center;">5 maiores médias</h3>', unsafe_allow_html=True)
                fig_melhores = px.bar(
                    melhores,
                    x="Gestor",
                    y="Nome",
                    orientation="h",
                    text="Gestor",
                    color_discrete_sequence=["#2E7D32"]
                )
                fig_melhores.update_traces(
                    texttemplate="%{x:.2f}",
                    textposition="outside",
                    cliponaxis=False
                )
                fig_melhores.update_layout(
                    xaxis_title="Média geral",
                    yaxis_title="Avaliado",
                    xaxis_range=[0, 5],
                    height=320,
                    margin=dict(l=20, r=20, t=20, b=40)
                )
                st.plotly_chart(fig_melhores, use_container_width=True, config={"displaylogo": False})

            with col_piores:
                st.markdown('<h3 style="text-align: center;">5 menores médias</h3>', unsafe_allow_html=True)
                fig_piores = px.bar(
                    piores,
                    x="Gestor",
                    y="Nome",
                    orientation="h",
                    text="Gestor",
                    color_discrete_sequence=["#C62828"]
                )
                fig_piores.update_traces(
                    texttemplate="%{x:.2f}",
                    textposition="outside",
                    cliponaxis=False
                )
                fig_piores.update_layout(
                    xaxis_title="Média geral",
                    yaxis_title="Avaliado",
                    xaxis_range=[0, 5],
                    yaxis={
                        "categoryorder": "array",
                        "categoryarray": piores["Nome"].tolist()[::-1]
                    },
                    height=320,
                    margin=dict(l=20, r=20, t=20, b=40)
                )
                st.plotly_chart(fig_piores, use_container_width=True, config={"displaylogo": False})
        else:
            st.info("Não há médias válidas para montar o ranking.")

