import streamlit as st
import sqlite3
import pandas as pd
import csv
import io
import os
import base64

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

# 1. FUNÇÃO PARA CARREGAR IMAGEM DE FUNDO DO LOGIN
def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

bg_b64 = get_image_base64("Gemini_Generated_Image_yde6bfyde6bfyde6.jpg")

# 2. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gato na Grade - Victor Lacôrte", layout="wide", page_icon="🏫")

st.markdown("""
    <style>
    div.stButton > button {
        background-color: #A31515 !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
        border: 1px solid #800F0F !important;
        font-weight: bold !important;
        padding: 8px 20px !important;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #800F0F !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .btn-selecionado > button {
        background-color: #FFD700 !important;
        color: #000000 !important;
        border: 3px dashed #000000 !important;
        transform: scale(1.05);
        box-shadow: 0 0 15px rgba(255, 215, 0, 0.6) !important;
    }
    h1, h2, h3 { color: #A31515 !important; }
    .horario-texto {
        display: flex;
        align-items: center;
        height: 100%;
        min-height: 40px;
        font-weight: bold;
        font-style: italic;
        padding-top: 10px;
    }
    .btn-cancelar > button {
        background-color: #6c757d !important;
        border: 1px solid #5a6268 !important;
    }
    .btn-cancelar > button:hover {
        background-color: #5a6268 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 3. INICIALIZAÇÃO DE ESTADOS GLOBAIS
if "autenticado" not in st.session_state: st.session_state["autenticado"] = False
if "grade_gerada" not in st.session_state: st.session_state["grade_gerada"] = None
if "celula_selecionada" not in st.session_state: st.session_state["celula_selecionada"] = None
if "modo_edicao" not in st.session_state: st.session_state["modo_edicao"] = False

# 4. BANCO DE DADOS
@st.cache_resource
def obter_conexao():
    return sqlite3.connect("banco_escola_web.db", check_same_thread=False)

def inicializar_banco():
    conn = obter_conexao()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS locais (id INTEGER PRIMARY KEY, nome TEXT UNIQUE)''')
    for local in ["Escola Sede", "Penitenciária", "CR Masculino", "CR Feminino"]:
        cursor.execute("INSERT OR IGNORE INTO locais (nome) VALUES (?)", (local,))
    cursor.execute('''CREATE TABLE IF NOT EXISTS turmas (id INTEGER PRIMARY KEY, local_id INTEGER, nome TEXT, turno TEXT, aulas_por_dia INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS disciplinas (id INTEGER PRIMARY KEY, nome TEXT, carga_semanal INTEGER, nivel TEXT, turma_id INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS professores (id INTEGER PRIMARY KEY, nome TEXT UNIQUE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS prof_disciplina (prof_id INTEGER, disc_id INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS restricoes (prof_id INTEGER, dia_semana TEXT, aula_bloqueada INTEGER)''')
    conn.commit()

inicializar_banco()

# 5. TELA DE LOGIN ABSOLUTA
def tela_login():
    if bg_b64:
        st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{bg_b64}");
            background-size: 100vw 100vh;
            background-position: left top;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        
        .block-container {{
            padding: 0 !important;
            max-width: 100% !important;
        }}
        
        [data-testid="stForm"] {{
            position: fixed;
            top: 32.5vh;        
            left: 44.5vw;       
            width: 46vw;        
            height: 50vh;       
            background-color: transparent !important; 
            border: none !important;
            box-shadow: none !important;
            z-index: 999;
            padding-top: 3vh !important;
            padding-left: 4vw !important;
            padding-right: 4vw !important;
        }}
        
        header[data-testid="stHeader"] {{
            background-color: transparent !important;
        }}
        </style>
        """, unsafe_allow_html=True)
    
    with st.form("form_login"):
        st.markdown("<h2 style='text-align: center; color: white !important; margin-bottom: 15px;'>Acesso Restrito</h2>", unsafe_allow_html=True)
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar no Sistema"):
            if usuario == "Admin" and senha == "Victor0004":
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Credenciais inválidas.")

def gerar_csv_grade(grade, turmas_nomes, dias_semana, max_aulas):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Dia", "Horário"] + turmas_nomes)
    for dia in dias_semana:
        for h in range(1, max_aulas + 1):
            linha = [dia, f"{h}ª Aula"]
            for t in turmas_nomes:
                aula = grade.get((t, dia, h))
                linha.append(f"{aula['disc_nome']} (Prof. {aula['prof_nome']})" if aula else "Livre")
            writer.writerow(linha)
    return output.getvalue().encode('utf-8-sig')

def renderizar_pagina_pdf(pdf, grade, turmas, dias_semana, max_aulas, titulo, paleta, cor_map, cor_idx):
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, titulo.encode('latin-1', 'replace').decode('latin-1'), 0, 1, 'C')
    pdf.ln(3)
    
    largura_util = 277
    col_dia = 22
    col_hora = 18
    col_turma = (largura_util - col_dia - col_hora) / len(turmas)
    
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(col_dia, 8, "Dia", 1, 0, 'C')
    pdf.cell(col_hora, 8, "Aula", 1, 0, 'C')
    for t in turmas:
        pdf.cell(col_turma, 8, t.encode('latin-1', 'replace').decode('latin-1'), 1, 0, 'C')
    pdf.ln()
    
    for dia in dias_semana:
        for h in range(1, max_aulas + 1):
            pdf.set_font("Arial", 'B', 9)
            pdf.set_text_color(0, 0, 0)
            
            texto_dia = dia if h == 1 else ""
            pdf.cell(col_dia, 7, texto_dia.encode('latin-1', 'replace').decode('latin-1'), 'L R', 0, 'C')
            pdf.cell(col_hora, 7, f"{h}a", 1, 0, 'C')
            
            for t in turmas:
                aula = grade.get((t, dia, h))
                if aula:
                    chave_cor = f"{aula['disc_nome']}{aula['prof_nome']}"
                    if chave_cor not in cor_map:
                        cor_map[chave_cor] = paleta[cor_idx % len(paleta)]
                        cor_idx += 1
                    r, g, b = cor_map[chave_cor]
                    pdf.set_text_color(r, g, b)
                    texto = f"{aula['disc_nome']} - {aula['prof_nome']}"
                    if len(texto) > 20: texto = texto[:18] + ".."
                else:
                    pdf.set_text_color(150, 150, 150)
                    texto = "Livre"
                pdf.cell(col_turma, 7, texto.encode('latin-1', 'replace').decode('latin-1'), 1, 0, 'C')
            
            pdf.set_text_color(0, 0, 0)
            pdf.ln()
        pdf.cell(largura_util, 0, "", 'T', 1)

def gerar_pdf_grade(grade, turmas_nomes, dias_semana, max_aulas, unidade_nome, conn):
    if FPDF is None: return None
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    
    paleta = [(0, 0, 205), (220, 20, 60), (34, 139, 34), (255, 140, 0), (138, 43, 226), (139, 69, 19), (0, 139, 139), (210, 105, 30)]
    cor_map = {}
    
    if unidade_nome == "Escola Sede":
        cursor = conn.cursor()
        turmas_fund = []
        turmas_medio = []
        for t in turmas_nomes:
            cursor.execute("SELECT d.nivel FROM disciplinas d JOIN turmas tu ON d.turma_id = tu.id WHERE tu.nome = ? LIMIT 1", (t,))
            res = cursor.fetchone()
            if res and "Fundamental" in res[0]: turmas_fund.append(t)
            else: turmas_medio.append(t)
            
        if turmas_fund: renderizar_pagina_pdf(pdf, grade, turmas_fund, dias_semana, max_aulas, "Grade Oficial - Sede (Ensino Fundamental)", paleta, cor_map, 0)
        if turmas_medio: renderizar_pagina_pdf(pdf, grade, turmas_medio, dias_semana, max_aulas, "Grade Oficial - Sede (Ensino Médio)", paleta, cor_map, len(cor_map))
    else:
        renderizar_pagina_pdf(pdf, grade, turmas_nomes, dias_semana, max_aulas, f"Grade Oficial - {unidade_nome}", paleta, cor_map, 0)
    
    resultado = pdf.output(dest='S')
    if isinstance(resultado, str): return resultado.encode('latin-1')
    return resultado

# --- FUNÇÕES DO MOTOR ---
def processar_motor_ortools(unidade_alvo):
    try: from ortools.sat.python import cp_model
    except ImportError: return False

    conn = obter_conexao()
    cursor = conn.cursor()
    model = cp_model.CpModel()
    dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]

    todas_turmas = cursor.execute("SELECT t.id, t.nome, t.aulas_por_dia, l.nome FROM turmas t JOIN locais l ON t.local_id = l.id ORDER BY t.nome ASC").fetchall()
    turmas = {t[0]: {'nome': t[1], 'aulas': t[2], 'local': t[3]} for t in todas_turmas}
    turmas_alvo = {k: v for k, v in turmas.items() if v['local'] == unidade_alvo}
    if not turmas_alvo: return False

    disciplinas = {d[0]: {'nome': d[1], 'carga': d[2], 'turma_id': d[3]} for d in cursor.execute("SELECT id, nome, carga_semanal, turma_id FROM disciplinas").fetchall()}
    vinculos = cursor.execute("SELECT pd.prof_id, pd.disc_id, p.nome FROM prof_disciplina pd JOIN professores p ON pd.prof_id = p.id").fetchall()
    prof_nomes = {v[0]: v[2] for v in vinculos}
    restricoes = cursor.execute("SELECT prof_id, dia_semana, aula_bloqueada FROM restricoes").fetchall()

    aulas_vars = {}
    for prof_id, disc_id, _ in vinculos:
        if disc_id not in disciplinas: continue
        turma_id = disciplinas[disc_id]['turma_id']
        if turma_id not in turmas: continue 
        for d in dias:
            for h in range(1, turmas[turma_id]['aulas'] + 1):
                aulas_vars[(prof_id, disc_id, turma_id, d, h)] = model.NewBoolVar(f'a_{prof_id}_{disc_id}_{turma_id}_{d}_{h}')

    for prof_id, disc_id, _ in vinculos:
        if disc_id not in disciplinas: continue
        turma_id = disciplinas[disc_id]['turma_id']
        if turma_id not in turmas: continue
        vars_disciplina = [aulas_vars[(prof_id, disc_id, turma_id, d, h)] for d in dias for h in range(1, turmas[turma_id]['aulas'] + 1)]
        model.Add(sum(vars_disciplina) == disciplinas[disc_id]['carga'])
        if turmas[turma_id]['local'] == "Escola Sede":
            for d in dias:
                for h in range(1, turmas[turma_id]['aulas'] - 1):
                    if (prof_id, disc_id, turma_id, d, h) in aulas_vars:
                        model.Add(aulas_vars[(prof_id, disc_id, turma_id, d, h)] + aulas_vars[(prof_id, disc_id, turma_id, d, h+1)] + aulas_vars[(prof_id, disc_id, turma_id, d, h+2)] <= 2)

    for p_id in prof_nomes.keys():
        for d in dias:
            for h in range(1, 7):
                vars_prof_horario = [var for key, var in aulas_vars.items() if key[0] == p_id and key[3] == d and key[4] == h]
                if vars_prof_horario: model.AddAtMostOne(vars_prof_horario)

    for t_id, t_info in turmas.items():
        for d in dias:
            for h in range(1, t_info['aulas'] + 1):
                vars_turma = [var for key, var in aulas_vars.items() if key[2] == t_id and key[3] == d and key[4] == h]
                if vars_turma: model.AddAtMostOne(vars_turma)

    for prof_id, dia, aula in restricoes:
        for key, var in aulas_vars.items():
            if key[0] == prof_id and key[3] == dia and key[4] == aula: model.Add(var == 0)

    for p_id in prof_nomes.keys():
        for d in dias:
            vars_crm = [v for k, v in aulas_vars.items() if k[0]==p_id and k[3]==d and turmas[k[2]]['local'] == "CR Masculino"]
            vars_crf = [v for k, v in aulas_vars.items() if k[0]==p_id and k[3]==d and turmas[k[2]]['local'] == "CR Feminino"]
            if vars_crm and vars_crf:
                b_crm = model.NewBoolVar(f'bool_crm_{p_id}_{d}')
                b_crf = model.NewBoolVar(f'bool_crf_{p_id}_{d}')
                for v in vars_crm: model.AddImplication(v, b_crm)
                for v in vars_crf: model.AddImplication(v, b_crf)
                model.Add(b_crm + b_crf <= 1)

    dias_trabalhados = []
    starts_turma = []
    penalidade_horario = []
    dias_cheios = []

    for p_id in prof_nomes.keys():
        for d in dias:
            vars_prof_dia = [var for key, var in aulas_vars.items() if key[0] == p_id and key[3] == d]
            if vars_prof_dia:
                trabalha_neste_dia = model.NewBoolVar(f'trab_{p_id}_{d}')
                for var in vars_prof_dia: model.AddImplication(var, trabalha_neste_dia)
                dias_trabalhados.append(trabalha_neste_dia)
                
                if unidade_alvo != "Escola Sede":
                    is_full = model.NewBoolVar(f'full_{p_id}_{d}')
                    max_aulas_dia = max([t['aulas'] for t in turmas_alvo.values()])
                    model.Add(sum(vars_prof_dia) == max_aulas_dia).OnlyEnforceIf(is_full)
                    model.Add(sum(vars_prof_dia) < max_aulas_dia).OnlyEnforceIf(is_full.Not())
                    dias_cheios.append(is_full)
            
            for t_id in turmas.keys():
                for h in range(1, turmas[t_id]['aulas'] + 1):
                    vars_pth = [var for key, var in aulas_vars.items() if key[0] == p_id and key[2] == t_id and key[3] == d and key[4] == h]
                    if not vars_pth: continue
                    is_teaching_now = model.NewBoolVar(f'teach_{p_id}_{t_id}_{d}_{h}')
                    model.Add(is_teaching_now == sum(vars_pth))
                    start_var = model.NewBoolVar(f'start_{p_id}_{t_id}_{d}_{h}')
                    if h == 1: model.Add(start_var == is_teaching_now)
                    else:
                        vars_pth_prev = [var for key, var in aulas_vars.items() if key[0] == p_id and key[2] == t_id and key[3] == d and key[4] == h-1]
                        is_teaching_prev = model.NewBoolVar(f'teach_prev_{p_id}_{t_id}_{d}_{h}')
                        model.Add(is_teaching_prev == sum(vars_pth_prev)) if vars_pth_prev else model.Add(is_teaching_prev == 0)
                        model.Add(start_var >= is_teaching_now - is_teaching_prev)
                    starts_turma.append(start_var)
                    penalidade_horario.append(is_teaching_now * h)

    peso_base = sum(dias_trabalhados) * 10000 + sum(starts_turma) * 100 + sum(penalidade_horario)
    if unidade_alvo != "Escola Sede": model.Minimize(peso_base - sum(dias_cheios) * 5000)
    else: model.Minimize(peso_base)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15.0 
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        grade_resultado = {}
        for t_id, t_info in turmas_alvo.items():
            for d in dias:
                for h in range(1, t_info['aulas'] + 1):
                    chave = (t_info['nome'], d, h)
                    grade_resultado[chave] = None
                    for key, var in aulas_vars.items():
                        if key[2] == t_id and key[3] == d and key[4] == h and solver.Value(var) == 1:
                            grade_resultado[chave] = {'prof_id': key[0], 'prof_nome': prof_nomes[key[0]], 'disc_nome': disciplinas[key[1]]['nome']}
        st.session_state["grade_gerada"] = grade_resultado
        st.session_state["turmas_alvo"] = turmas_alvo
        st.session_state["dias_semana"] = dias
        return True
    return False

def acionar_troca(chave):
    if not st.session_state["modo_edicao"]: return
    if st.session_state["celula_selecionada"] is None:
        st.session_state["celula_selecionada"] = chave
    else:
        c1 = st.session_state["celula_selecionada"]
        c2 = chave
        temp = st.session_state["grade_gerada"][c1]
        st.session_state["grade_gerada"][c1] = st.session_state["grade_gerada"][c2]
        st.session_state["grade_gerada"][c2] = temp
        st.session_state["celula_selecionada"] = None

def renderizar_relatorio_auditoria(unidade_alvo):
    conn = obter_conexao()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, p.nome, d.nome, d.carga_semanal, t.nome 
        FROM professores p JOIN prof_disciplina pd ON p.id = pd.prof_id
        JOIN disciplinas d ON pd.disc_id = d.id JOIN turmas t ON d.turma_id = t.id
        JOIN locais l ON t.local_id = l.id WHERE l.nome = ? ORDER BY p.nome, t.nome
    ''', (unidade_alvo,))
    prof_disc_alvo = cursor.fetchall()
    dados_relatorio = []
    for p_id, p_nome, d_nome, carga_req, t_nome in prof_disc_alvo:
        carga_alocada = 0
        for (turma_key, dia, h), dados_aula in st.session_state["grade_gerada"].items():
            if dados_aula and dados_aula['prof_id'] == p_id and dados_aula['disc_nome'] == d_nome and turma_key == t_nome:
                carga_alocada += 1
        restricoes = cursor.execute("SELECT dia_semana, aula_bloqueada FROM restricoes WHERE prof_id = ?", (p_id,)).fetchall()
        str_restricoes = ", ".join([f"{r[0][:3]} ({r[1]}ª)" for r in restricoes]) if restricoes else "Livre"
        status = "✅ OK" if carga_alocada == carga_req else "❌ Erro"
        dados_relatorio.append({"Status": status, "Professor": p_nome, "Turma": t_nome, "Disciplina": d_nome, "Exigido": carga_req, "Na Grade": carga_alocada, "Indisponibilidade": str_restricoes})
    if dados_relatorio: st.dataframe(pd.DataFrame(dados_relatorio), use_container_width=True, hide_index=True)

# 6. APLICATIVO PRINCIPAL
def aplicativo_principal():
    conn = obter_conexao()
    cursor = conn.cursor()
    
    with st.sidebar:
        # Busca inteligente da imagem do mascote
        mascote_path = None
        for arquivo in os.listdir('.'):
            if arquivo.lower().startswith('mascote.') and arquivo.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                mascote_path = arquivo
                break
        
        if mascote_path:
            st.image(mascote_path, use_container_width=True)
        else:
            st.warning("⚠️ Imagem do mascote não encontrada. Salve-a como 'mascote.png' ou 'mascote.jpg' na mesma pasta.")
            
        st.markdown("### Painel de Controle")
        if st.button("Sair (Logout)"):
            st.session_state["autenticado"] = False
            st.rerun()

    st.title("Painel de Alocação Lógica")
    aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs(["1. Turmas", "2. Disciplinas", "3. Professores", "4. Indisponibilidade", "5. Gerar Grade", "6. Gerenciar Dados"])
    locais = [row[0] for row in cursor.execute("SELECT nome FROM locais ORDER BY id").fetchall()]

    with aba1:
        st.header("Cadastro de Turmas")
        with st.form("form_turmas", clear_on_submit=True):
            local_selecionado = st.selectbox("Unidade Prisional / Sede", locais)
            nome_turma = st.text_input("Nome da Turma (Ex: Médio C)")
            col_t1, col_t2 = st.columns(2)
            with col_t1: turno = st.selectbox("Turno", ["Manhã", "Tarde", "Noite"])
            with col_t2: aulas_dia = st.number_input("Aulas por Dia", min_value=1, max_value=6, value=5)
            if st.form_submit_button("Salvar Turma"):
                local_id = cursor.execute("SELECT id FROM locais WHERE nome = ?", (local_selecionado,)).fetchone()[0]
                cursor.execute("INSERT INTO turmas (local_id, nome, turno, aulas_por_dia) VALUES (?, ?, ?, ?)", (local_id, nome_turma, turno, aulas_dia))
                conn.commit()
                st.success("Turma salva!")

    with aba2:
        st.header("Matriz Curricular")
        local_disc = st.selectbox("Filtro: Unidade", locais, key="f_local_disc")
        turmas_do_local = [row[0] for row in cursor.execute("SELECT t.nome FROM turmas t JOIN locais l ON t.local_id = l.id WHERE l.nome = ?", (local_disc,)).fetchall()]
        if turmas_do_local:
            with st.form("form_disciplinas", clear_on_submit=True):
                turma_disc = st.selectbox("Turma", turmas_do_local)
                nome_disc = st.text_input("Disciplina")
                carga_sem = st.number_input("Aulas Semanais", 1, 20, 2)
                nivel = st.selectbox("Nível", ["Ensino Médio", "Fundamental"])
                if st.form_submit_button("Salvar Disciplina"):
                    turma_id = cursor.execute("SELECT id FROM turmas WHERE nome = ?", (turma_disc,)).fetchone()[0]
                    cursor.execute("INSERT INTO disciplinas (nome, carga_semanal, nivel, turma_id) VALUES (?, ?, ?, ?)", (nome_disc, carga_sem, nivel, turma_id))
                    conn.commit()
                    st.success("Disciplina salva!")

    with aba3:
        st.header("Gestão do Corpo Docente")
        with st.form("form_novo_prof", clear_on_submit=True):
            nome_novo_prof = st.text_input("Nome do Docente")
            if st.form_submit_button("Adicionar Professor"):
                cursor.execute("INSERT INTO professores (nome) VALUES (?)", (nome_novo_prof,))
                conn.commit()
                st.success("Salvo!")
        
        professores = [row[0] for row in cursor.execute("SELECT nome FROM professores ORDER BY nome").fetchall()]
        if professores:
            prof_selecionado = st.selectbox("Docente", professores)
            local_vinc = st.selectbox("Unidade", locais, key="f_local_vinc")
            turmas_vinc = [row[0] for row in cursor.execute("SELECT t.nome FROM turmas t JOIN locais l ON t.local_id = l.id WHERE l.nome = ?", (local_vinc,)).fetchall()]
            if turmas_vinc:
                turma_vinc = st.selectbox("Turma", turmas_vinc, key="f_turma_vinc")
                disciplinas_livres = cursor.execute('SELECT d.id, d.nome, d.carga_semanal FROM disciplinas d JOIN turmas t ON d.turma_id = t.id WHERE t.nome = ? AND d.id NOT IN (SELECT disc_id FROM prof_disciplina)', (turma_vinc,)).fetchall()
                if disciplinas_livres:
                    with st.form("form_vinculo"):
                        selecoes = {d_id: st.checkbox(f"{d_nome} ({d_carga} aulas)") for d_id, d_nome, d_carga in disciplinas_livres}
                        if st.form_submit_button("Vincular Aulas"):
                            prof_id = cursor.execute("SELECT id FROM professores WHERE nome = ?", (prof_selecionado,)).fetchone()[0]
                            for d_id, marcada in selecoes.items():
                                if marcada: cursor.execute("INSERT INTO prof_disciplina (prof_id, disc_id) VALUES (?, ?)", (prof_id, d_id))
                            conn.commit()
                            st.rerun()

    with aba4:
        st.header("Matriz de Restrições")
        professores_rest = [row[0] for row in cursor.execute("SELECT nome FROM professores ORDER BY nome").fetchall()]
        if professores_rest:
            prof_alvo = st.selectbox("Professor:", professores_rest, key="p_rest")
            num_aulas = 6 if "6" in st.radio("Perfil:", ["Escola Sede (6 Aulas)", "Sistema Prisional (5 Aulas)"], horizontal=True) else 5
            prof_id = cursor.execute("SELECT id FROM professores WHERE nome = ?", (prof_alvo,)).fetchone()[0]
            restricoes_banco = cursor.execute("SELECT dia_semana, aula_bloqueada FROM restricoes WHERE prof_id = ?", (prof_id,)).fetchall()
            df_rest = pd.DataFrame(columns=["Aula"] + ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"])
            df_rest["Aula"] = [f"{i}ª Aula" for i in range(1, num_aulas + 1)]
            for dia in ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]: df_rest[dia] = False
            for dia, aula in restricoes_banco:
                if aula <= num_aulas and dia in df_rest.columns: df_rest.at[aula - 1, dia] = True
            grade_editada = st.data_editor(df_rest, hide_index=True, use_container_width=True)
            if st.button("Salvar Restrições"):
                cursor.execute("DELETE FROM restricoes WHERE prof_id = ? AND aula_bloqueada <= ?", (prof_id, num_aulas))
                for i in range(num_aulas):
                    for dia in ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]:
                        if grade_editada.at[i, dia]: cursor.execute("INSERT INTO restricoes (prof_id, dia_semana, aula_bloqueada) VALUES (?, ?, ?)", (prof_id, dia, i+1))
                conn.commit()
                st.success("Restrições Salvas!")

    with aba5:
        st.header("Processamento Lógico")
        col_g1, col_g2 = st.columns([2, 1])
        with col_g1: unidade_gerar = st.selectbox("Selecione a Unidade para processar a grade:", locais)
        with col_g2:
            st.write("")
            st.write("")
            if st.button("⚙️ Gerar Grade Automática", use_container_width=True):
                with st.spinner("Analisando rotas e eliminando circulação desnecessária..."):
                    if processar_motor_ortools(unidade_gerar):
                        st.session_state["celula_selecionada"] = None
                        st.rerun()

        st.divider()

        if st.session_state["grade_gerada"]:
            col_t, col_e = st.columns([3, 1])
            with col_t: st.subheader(f"Grade Oficial - {unidade_gerar}")
            with col_e:
                st.session_state["modo_edicao"] = st.toggle("Ativar Modo Edição", value=st.session_state["modo_edicao"])
                if not st.session_state["modo_edicao"]: st.session_state["celula_selecionada"] = None

            turmas_nomes = sorted([t['nome'] for t in st.session_state["turmas_alvo"].values()])
            max_aulas = max([t['aulas'] for t in st.session_state["turmas_alvo"].values()])
            
            col_d1, col_d2, col_d3 = st.columns([1, 1, 2])
            csv_data = gerar_csv_grade(st.session_state["grade_gerada"], turmas_nomes, st.session_state["dias_semana"], max_aulas)
            with col_d1: st.download_button("📥 Baixar em CSV", data=csv_data, file_name=f"grade_{unidade_gerar}.csv", mime="text/csv")
            
            if FPDF is not None:
                pdf_data = gerar_pdf_grade(st.session_state["grade_gerada"], turmas_nomes, st.session_state["dias_semana"], max_aulas, unidade_gerar, obter_conexao())
                with col_d2: st.download_button("📥 Baixar em PDF", data=pdf_data, file_name=f"grade_{unidade_gerar}.pdf", mime="application/pdf")
            else:
                with col_d2: st.error("Instale o FPDF para baixar em PDF (pip install fpdf)")

            st.write("") 

            cols = st.columns([1] + [2]*len(turmas_nomes))
            cols[0].markdown("**Horário**")
            for i, t_nome in enumerate(turmas_nomes): cols[i+1].markdown(f"**{t_nome}**")

            for dia in st.session_state["dias_semana"]:
                st.markdown(f"#### {dia}")
                for h in range(1, max_aulas + 1):
                    cols_linha = st.columns([1] + [2]*len(turmas_nomes))
                    cols_linha[0].markdown(f"<div class='horario-texto'>{h}ª Aula</div>", unsafe_allow_html=True)
                    
                    for i, t_nome in enumerate(turmas_nomes):
                        chave = (t_nome, dia, h)
                        dados_aula = st.session_state["grade_gerada"].get(chave)
                        texto_original = f"{dados_aula['disc_nome']}\nProf. {dados_aula['prof_nome']}" if dados_aula else "--- Livre ---"
                        
                        if st.session_state["celula_selecionada"] == chave:
                            texto_btn = f"👉 SELECIONADO 👈\n{texto_original}"
                            st.markdown('<div class="btn-selecionado">', unsafe_allow_html=True)
                        else:
                            texto_btn = texto_original
                            
                        with cols_linha[i+1]:
                            if st.session_state["modo_edicao"]: st.button(texto_btn, key=f"btn_{t_nome}_{dia}_{h}", on_click=acionar_troca, args=(chave,), use_container_width=True)
                            else: st.info(texto_btn)
                                
                        if st.session_state["celula_selecionada"] == chave: st.markdown('</div>', unsafe_allow_html=True)

            st.divider()
            st.subheader("📋 Relatório de Conferência e Auditoria")
            renderizar_relatorio_auditoria(unidade_gerar)

    with aba6:
        st.header("Gerenciador de Banco de Dados")
        st.markdown("Visualize, audite e remova registros com segurança.")
        
        tipo_gestao = st.radio("O que você deseja gerenciar?", ["Professores", "Disciplinas", "Turmas"], horizontal=True)
        st.divider()

        if tipo_gestao == "Professores":
            profs_lista = cursor.execute("SELECT id, nome FROM professores ORDER BY nome").fetchall()
            if not profs_lista: st.info("Nenhum professor cadastrado.")
            else:
                st.dataframe(pd.DataFrame(profs_lista, columns=["ID", "Professor"]), hide_index=True, use_container_width=True)
                with st.expander("🗑️ Excluir Professor", expanded=False):
                    prof_del = st.selectbox("Selecione o professor para remover permanentemente:", [f"{p[0]} - {p[1]}" for p in profs_lista])
                    st.warning("Isso apagará o professor de todas as turmas e excluir suas restrições.")
                    c_del1, c_del2, _ = st.columns([1, 1, 2])
                    with c_del1:
                        if st.button("Confirmar Exclusão", type="primary"):
                            p_id = int(prof_del.split(" - ")[0])
                            cursor.execute("DELETE FROM restricoes WHERE prof_id = ?", (p_id,))
                            cursor.execute("DELETE FROM prof_disciplina WHERE prof_id = ?", (p_id,))
                            cursor.execute("DELETE FROM professores WHERE id = ?", (p_id,))
                            conn.commit()
                            st.rerun()
                    with c_del2:
                        if st.button("Cancelar", key="cancel_prof"): st.rerun()

        elif tipo_gestao == "Disciplinas":
            discs_lista = cursor.execute('''
                SELECT d.id, d.nome, d.carga_semanal, t.nome, l.nome 
                FROM disciplinas d JOIN turmas t ON d.turma_id = t.id JOIN locais l ON t.local_id = l.id ORDER BY l.nome, t.nome, d.nome
            ''').fetchall()
            if not discs_lista: st.info("Nenhuma disciplina cadastrada.")
            else:
                st.dataframe(pd.DataFrame(discs_lista, columns=["ID", "Disciplina", "Aulas/Sem", "Turma", "Unidade"]), hide_index=True, use_container_width=True)
                with st.expander("🗑️ Excluir Disciplina", expanded=False):
                    disc_del = st.selectbox("Selecione a disciplina para remover:", [f"{d[0]} - {d[1]} ({d[3]} - {d[4]})" for d in discs_lista])
                    st.warning("Isso removerá a matéria e desvinculará o professor.")
                    c_del1, c_del2, _ = st.columns([1, 1, 2])
                    with c_del1:
                        if st.button("Confirmar Exclusão", type="primary"):
                            d_id = int(disc_del.split(" - ")[0])
                            cursor.execute("DELETE FROM prof_disciplina WHERE disc_id = ?", (d_id,))
                            cursor.execute("DELETE FROM disciplinas WHERE id = ?", (d_id,))
                            conn.commit()
                            st.rerun()
                    with c_del2:
                        if st.button("Cancelar", key="cancel_disc"): st.rerun()

        elif tipo_gestao == "Turmas":
            turmas_lista = cursor.execute('''
                SELECT t.id, t.nome, t.turno, l.nome FROM turmas t JOIN locais l ON t.local_id = l.id ORDER BY l.nome, t.nome
            ''').fetchall()
            if not turmas_lista: st.info("Nenhuma turma cadastrada.")
            else:
                st.dataframe(pd.DataFrame(turmas_lista, columns=["ID", "Turma", "Turno", "Unidade"]), hide_index=True, use_container_width=True)
                with st.expander("🗑️ Excluir Turma", expanded=False):
                    turma_del = st.selectbox("Selecione a turma para remover:", [f"{t[0]} - {t[1]} ({t[3]})" for t in turmas_lista])
                    st.error("PERIGO: Excluir uma turma apagará TODAS as disciplinas e vínculos!")
                    c_del1, c_del2, _ = st.columns([1, 1, 2])
                    with c_del1:
                        if st.button("Confirmar Exclusão", type="primary"):
                            t_id = int(turma_del.split(" - ")[0])
                            disc_ids = cursor.execute("SELECT id FROM disciplinas WHERE turma_id = ?", (t_id,)).fetchall()
                            for (d_id,) in disc_ids: cursor.execute("DELETE FROM prof_disciplina WHERE disc_id = ?", (d_id,))
                            cursor.execute("DELETE FROM disciplinas WHERE turma_id = ?", (t_id,))
                            cursor.execute("DELETE FROM turmas WHERE id = ?", (t_id,))
                            conn.commit()
                            st.rerun()
                    with c_del2:
                        if st.button("Cancelar", key="cancel_turma"): st.rerun()

# 7. ROTEADOR
if not st.session_state["autenticado"]: tela_login()
else: aplicativo_principal()