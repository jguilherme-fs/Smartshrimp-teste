"""
app.py
═══════════════════════════════════════════════════════════════════
Dashboard IoT — Monitoramento de Tanque de Camarão (Carcinicultura)
Design mobile-first | Dados em tempo real via Firebase Firestore
Auto-refresh a cada 5 segundos para acompanhar o simulador ao vivo.

COMO USAR:
  1. Coloque 'firebase-credentials.json' na mesma pasta deste arquivo.
  2. pip install streamlit firebase-admin pandas plotly
  3. streamlit run app.py
  4. Acesse pelo celular: http://<ip-da-maquina>:8501
═══════════════════════════════════════════════════════════════════
"""
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO DA PÁGINA — deve ser a primeira chamada Streamlit do script
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="SmartShrimp 🦐",
    page_icon="🦐",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIGURAÇÕES DE ALERTA POR E-MAIL (SMTP)
# ═══════════════════════════════════════════════════════════════════════════════
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # Porta padrão para conexões seguras SSL
EMAIL_REMETENTE = "gui27fs@gmail.com"
EMAIL_SENHA = "gfkx yxil dgtz rkca"  # Senha de aplicativo gerada no Google Accounts
EMAIL_DESTINATARIO = "brunasrbarbosa@gmail.com"

# Intervalo mínimo entre alertas para o mesmo parâmetro (300s = 5 minutos)
INTERVALO_ALERTA_SEGUNDOS = 300


@st.cache_resource
def obter_controle_alertas():
    """
    Mantém um dicionário global em memória (persistido entre os re-runs do Streamlit)
    para registrar o timestamp (time.time()) do último e-mail de alerta enviado por parâmetro.
    """
    return {"ultimos_alertas": {}}


def enviar_email_alerta(parametro, valor_atual, faixa_ideal, horario_medicao):
    """
    Monta e envia uma mensagem de e-mail formatada em HTML usando smtplib.
    """
    # Se ainda estiver com os valores padrão de exemplo, apenas registra no console sem tentar enviar
    if EMAIL_REMETENTE == "seu-email@gmail.com" or EMAIL_SENHA == "sua-senha-de-aplicativo":
        st.warning(f"⚠️ Alerta gerado para {parametro}: {valor_atual}, mas o e-mail não foi enviado porque as credenciais SMTP não foram configuradas no código.")
        print(f"[Aviso] Alerta para {parametro} ({valor_atual}) não enviado - credenciais não configuradas.")
        return True  # Retorna True para fingir sucesso na simulação sem travar o app
        
    msg = MIMEMultipart()
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = EMAIL_DESTINATARIO
    msg['Subject'] = f"🦐 [SmartShrimp] ALERTA: {parametro} Fora da Faixa Ideal!"

    corpo_html = f"""
    <html>
      <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #071525; color: #e2f3fb; padding: 20px; margin: 0;">
        <div style="max-width: 500px; margin: 0 auto; background: linear-gradient(145deg, #0a1c32 0%, #0c2037 100%); border: 1px solid rgba(255,255,255,0.05); border-left: 5px solid #ff3c3c; border-radius: 18px; padding: 25px; box-shadow: 0 8px 32px rgba(0,0,0,0.45);">
          <div style="text-align: center; margin-bottom: 20px;">
            <span style="font-size: 3rem;">🦐</span>
            <h2 style="font-family: 'Rajdhani', sans-serif; color: #e2f3fb; margin: 10px 0 0; letter-spacing: 2px;">SmartShrimp</h2>
            <p style="color: #3a8fb5; font-size: 0.8rem; letter-spacing: 2px; text-transform: uppercase; margin: 5px 0 0;">Alerta de Telemetria</p>
          </div>
          
          <div style="background: rgba(255,60,60,0.1); border: 1px solid rgba(255,60,60,0.3); border-radius: 12px; padding: 15px; margin-bottom: 20px; text-align: center;">
            <strong style="color: #ff7070; font-size: 1.1rem; display: block; margin-bottom: 5px;">⚠️ PARÂMETRO FORA DO LIMITE</strong>
            <span style="color: #ff9f9f; font-size: 0.9rem;">O sistema detectou uma variação crítica no Tanque 01.</span>
          </div>

          <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.95rem;">
            <tr>
              <td style="padding: 8px 0; color: #3a7fa0; font-weight: bold; width: 40%;">Parâmetro:</td>
              <td style="padding: 8px 0; color: #e2f3fb; font-weight: bold;">{parametro}</td>
            </tr>
            <tr>
              <td style="padding: 8px 0; color: #3a7fa0; font-weight: bold;">Valor Lido:</td>
              <td style="padding: 8px 0; color: #ff4f4f; font-weight: bold; font-size: 1.2rem;">{valor_atual}</td>
            </tr>
            <tr>
              <td style="padding: 8px 0; color: #3a7fa0; font-weight: bold;">Faixa Ideal:</td>
              <td style="padding: 8px 0; color: #00d4aa; font-weight: bold;">{faixa_ideal}</td>
            </tr>
            <tr>
              <td style="padding: 8px 0; color: #3a7fa0; font-weight: bold;">Horário:</td>
              <td style="padding: 8px 0; color: #e2f3fb;">{horario_medicao}</td>
            </tr>
          </table>

          <div style="border-top: 1px solid rgba(255,255,255,0.05); padding-top: 15px; text-align: center; font-size: 0.8rem; color: #1e5570;">
            Trava de segurança anti-flood ativa. Novos alertas para <b>{parametro}</b> serão ignorados pelos próximos {INTERVALO_ALERTA_SEGUNDOS // 60} minutos.
          </div>
        </div>
      </body>
    </html>
    """
    msg.attach(MIMEText(corpo_html, 'html'))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_REMETENTE, EMAIL_SENHA)
            server.sendmail(EMAIL_REMETENTE, [EMAIL_DESTINATARIO], msg.as_string())
        print(f"📧 [Sucesso] E-mail de alerta enviado para {parametro}: {valor_atual}")
        return True
    except Exception as e:
        print(f"❌ [Erro] Falha ao enviar e-mail de alerta: {e}")
        st.error(f"Erro ao disparar e-mail de alerta: {e}")
        return False


def verificar_e_enviar_alertas(ultima_leitura):
    """
    Verifica se a última leitura está fora das faixas ideais e dispara o e-mail de alerta
    caso o intervalo do anti-flood já tenha se passado para o parâmetro em questão.
    """
    o2 = float(ultima_leitura["oxigenio"])
    temp = float(ultima_leitura["temperatura"])
    ph = float(ultima_leitura["ph"])
    ts_medicao = ultima_leitura["timestamp"]
    
    ts_str = ts_medicao.strftime("%d/%m/%Y %H:%M:%S") if isinstance(ts_medicao, datetime) else str(ts_medicao)
    
    # Obtém o dicionário persistente do st.cache_resource
    controle = obter_controle_alertas()
    ultimos_alertas = controle["ultimos_alertas"]
    agora = time.time()

    # Definição das regras de limite requeridas pelo usuário:
    # Oxigênio: < 4.0 mg/L
    # Temperatura: < 26.0°C ou > 32.0°C
    # pH: < 7.2 ou > 8.5
    parametros_teste = [
        {
            "nome": "Oxigênio Dissolvido",
            "valor_atual": o2,
            "valor_str": f"{o2:.2f} mg/L",
            "fora_da_faixa": o2 < 4.0,
            "faixa_ideal": ">= 4.0 mg/L"
        },
        {
            "nome": "Temperatura",
            "valor_atual": temp,
            "valor_str": f"{temp:.1f} °C",
            "fora_da_faixa": temp < 26.0 or temp > 32.0,
            "faixa_ideal": "26.0 °C a 32.0 °C"
        },
        {
            "nome": "pH da Água",
            "valor_atual": ph,
            "valor_str": f"{ph:.2f}",
            "fora_da_faixa": ph < 7.2 or ph > 8.5,
            "faixa_ideal": "7.2 a 8.5"
        }
    ]

    for item in parametros_teste:
        if item["fora_da_faixa"]:
            nome = item["nome"]
            ultimo_envio = ultimos_alertas.get(nome, 0)
            
            # Verifica se já se passou o intervalo do anti-flood
            if agora - ultimo_envio >= INTERVALO_ALERTA_SEGUNDOS:
                enviou = enviar_email_alerta(
                    parametro=nome,
                    valor_atual=item["valor_str"],
                    faixa_ideal=item["faixa_ideal"],
                    horario_medicao=ts_str
                )
                if enviou:
                    # Registra a hora atual em segundos
                    ultimos_alertas[nome] = agora

# ═══════════════════════════════════════════════════════════════════════════════
#  CSS GLOBAL — Tema "oceano profundo" otimizado para mobile
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&family=DM+Sans:ital,wght@0,300;0,500;0,700;1,300&display=swap');

/* ─── Base & Background ──────────────────────────────────────── */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse 80% 60% at 20% -10%, rgba(0,160,200,.12) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 80% 110%, rgba(0,212,170,.07) 0%, transparent 55%),
        linear-gradient(175deg, #050d1a 0%, #071525 40%, #060f1e 100%);
    min-height: 100vh;
}
[data-testid="stHeader"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
#MainMenu, footer { display:none !important; visibility:hidden !important; }

.block-container {
    padding: 1.4rem 1rem 4rem;
    max-width: 500px;
    margin: 0 auto;
}

/* ─── Tipografia Base ────────────────────────────────────────── */
* { box-sizing: border-box; }

/* ─── Header do App ──────────────────────────────────────────── */
.app-header {
    text-align: center;
    margin-bottom: 1.6rem;
    padding-top: .4rem;
}
.app-logo {
    font-size: 2.2rem;
    margin-bottom: .1rem;
    filter: drop-shadow(0 0 12px rgba(0,212,170,.6));
}
.app-title {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 1.9rem;
    color: #e2f3fb;
    letter-spacing: 2px;
    line-height: 1;
    margin: 0;
    text-shadow: 0 0 30px rgba(0,212,170,.3);
}
.app-sub {
    font-family: 'DM Sans', sans-serif;
    color: #3a8fb5;
    font-size: .72rem;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    margin-top: .3rem;
}

/* ─── Banner de Alerta Crítico ────────────────────────────────── */
.banner-alerta {
    background: linear-gradient(90deg, rgba(255,60,60,.22) 0%, rgba(255,60,60,.05) 100%);
    border: 1px solid rgba(255,80,80,.5);
    border-left: 4px solid #ff3c3c;
    border-radius: 14px;
    padding: .9rem 1rem;
    margin-bottom: 1.2rem;
    font-family: 'DM Sans', sans-serif;
    font-weight: 700;
    font-size: .88rem;
    color: #ff7070;
    animation: alerta-pulse 1.1s ease-in-out infinite alternate;
    text-align: center;
    line-height: 1.5;
}
@keyframes alerta-pulse {
    from { box-shadow: 0 0 0   rgba(255,60,60,.0);  border-color: rgba(255,80,80,.5); }
    to   { box-shadow: 0 0 28px rgba(255,60,60,.45); border-color: rgba(255,80,80,1); }
}

/* ─── Seção / Rótulo ─────────────────────────────────────────── */
.secao-label {
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    color: #2d7fa8;
    font-size: .68rem;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    margin: 1.5rem 0 .65rem;
}

/* ─── Cards dos Sensores ─────────────────────────────────────── */
.card {
    background: linear-gradient(145deg,
        rgba(10,28,50,.9)  0%,
        rgba(12,32,55,.85) 100%);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,.05);
    border-left: 5px solid;
    border-radius: 18px;
    padding: 1.1rem 1.2rem 1rem;
    margin-bottom: .8rem;
    box-shadow: 0 8px 32px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.04);
    font-family: 'DM Sans', sans-serif;
}

/* Cores de borda por sensor */
.card-o2-ok   { border-left-color: #00d4aa; }
.card-o2-warn {
    border-left-color: #ff3c3c;
    animation: card-danger 1.1s ease-in-out infinite alternate;
}
.card-temp { border-left-color: #f4a322; }
.card-ph   { border-left-color: #9d71ea; }

@keyframes card-danger {
    from { box-shadow: 0 8px 32px rgba(0,0,0,.45),  0 0 0   rgba(255,60,60,0); }
    to   { box-shadow: 0 8px 40px rgba(255,60,60,.2), 0 0 24px rgba(255,60,60,.3); }
}

.card-icon {
    font-size: 1.3rem;
    margin-bottom: .25rem;
    display: block;
}
.card-label {
    font-size: .65rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #3a7fa0;
    margin-bottom: .15rem;
}
.card-value {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 2.6rem;
    line-height: 1;
    margin: .05rem 0 .35rem;
}
.card-unit {
    font-family: 'DM Sans', sans-serif;
    font-weight: 300;
    font-size: 1rem;
    opacity: .6;
}

/* Cores dos valores */
.val-o2-ok   { color: #00d4aa; text-shadow: 0 0 18px rgba(0,212,170,.4); }
.val-o2-warn { color: #ff4f4f; text-shadow: 0 0 18px rgba(255,60,60,.5); }
.val-temp    { color: #f4a322; text-shadow: 0 0 18px rgba(244,163,34,.3); }
.val-ph      { color: #b39deb; text-shadow: 0 0 18px rgba(157,113,234,.3); }

/* Badges de status */
.badge {
    display: inline-block;
    border-radius: 20px;
    padding: .2rem .75rem;
    font-size: .7rem;
    font-weight: 700;
    letter-spacing: .5px;
}
.badge-ok   { background: rgba(0,212,170,.12);  color: #00d4aa; border: 1px solid rgba(0,212,170,.3); }
.badge-warn { background: rgba(255,75,75,.15);  color: #ff6b6b; border: 1px solid rgba(255,75,75,.4);  }
.badge-attn { background: rgba(244,163,34,.12); color: #f4a322; border: 1px solid rgba(244,163,34,.3); }

/* ─── Rodapé de Status ───────────────────────────────────────── */
.rodape {
    text-align: center;
    font-family: 'DM Sans', sans-serif;
    color: #1e5570;
    font-size: .69rem;
    padding: .7rem 0 .3rem;
    border-top: 1px solid rgba(255,255,255,.04);
    margin-top: .8rem;
    letter-spacing: .3px;
}
.rodape b { color: #2d7fa8; }
.live-dot {
    display: inline-block;
    width: 7px; height: 7px;
    background: #00d4aa;
    border-radius: 50%;
    margin-right: 5px;
    vertical-align: middle;
    box-shadow: 0 0 6px #00d4aa;
    animation: blink 1.5s ease-in-out infinite;
}
@keyframes blink {
    0%, 100% { opacity:1; box-shadow:0 0 8px #00d4aa; }
    50%       { opacity:.15; box-shadow:0 0 2px #00d4aa; }
}

/* ─── Plotly chart container ─────────────────────────────────── */
[data-testid="stPlotlyChart"] {
    border-radius: 16px;
    overflow: hidden;
    background: rgba(8,22,40,.7) !important;
    border: 1px solid rgba(255,255,255,.05);
    box-shadow: 0 8px 32px rgba(0,0,0,.4);
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  FIREBASE — inicialização única via @st.cache_resource
#  O decorator garante que a conexão é aberta apenas uma vez,
#  mesmo com os re-runs automáticos do Streamlit.
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def init_firebase():
    """Abre a conexão com o Firebase (executa apenas na primeira vez)."""
    try:
        app = firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate("firebase-credentials.json")
        app = firebase_admin.initialize_app(cred)
    return firestore.client(app=app)

db = init_firebase()


# ═══════════════════════════════════════════════════════════════════════════════
#  DADOS — cache com TTL=4s (< 5s do refresh) para buscar novos dados a cada ciclo
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=4)
def buscar_medicoes(n: int = 60) -> pd.DataFrame:
    """
    Retorna as últimas *n* medições do Firestore em ordem cronológica.
    O cache de 4s garante dados frescos a cada re-run de 5s.
    """
    docs = (
        db.collection("medicoes")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(n)
        .stream()
    )

    registros = []
    for doc in docs:
        d = doc.to_dict()
        ts = d.get("timestamp")
        # Firestore retorna DatetimeWithNanoseconds (timezone-aware, UTC)
        # Removemos o tz para compatibilidade com Plotly e exibição local
        if ts is not None and hasattr(ts, "tzinfo") and ts.tzinfo is not None:
            d["timestamp"] = ts.replace(tzinfo=None)
        registros.append(d)

    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.dropna(subset=["timestamp", "oxigenio", "temperatura", "ph"])
    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


# ═══════════════════════════════════════════════════════════════════════════════
#  LAYOUT PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <div class="app-logo">🦐</div>
    <div class="app-title">SmartShrimp</div>
    <div class="app-sub">Tanque 01 &nbsp;·&nbsp; Tempo Real</div>
</div>
""", unsafe_allow_html=True)


# ── Busca de dados ─────────────────────────────────────────────────────────────
df = buscar_medicoes()

if df.empty:
    st.markdown("""
    <div style="text-align:center;padding:2rem;color:#2d7fa8;font-family:'DM Sans',sans-serif;">
        <div style="font-size:2rem;margin-bottom:.5rem">⚙️</div>
        <div style="font-weight:700;margin-bottom:.3rem">Aguardando dados...</div>
        <div style="font-size:.8rem;opacity:.7">Inicie o <code>simulador_sensor.py</code></div>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(5)
    st.rerun()


# ── Última medição ─────────────────────────────────────────────────────────────
ultima = df.iloc[-1]
o2     = float(ultima["oxigenio"])
temp   = float(ultima["temperatura"])
ph     = float(ultima["ph"])
ts_ult = ultima["timestamp"]

# ── Verificação de Alertas por E-mail (com anti-flood) ─────────────────────────
verificar_e_enviar_alertas(ultima)

# Regras de status
alerta_o2    = o2 < 3.0
atencao_temp = not (26.0 <= temp <= 32.0)
atencao_ph   = not (7.5  <= ph  <= 8.5)


# ── Banner de Alerta Crítico ───────────────────────────────────────────────────
if alerta_o2:
    st.markdown(
        '<div class="banner-alerta">'
        '🚨 ALERTA CRÍTICO — Oxigênio Dissolvido Abaixo de 3.0 mg/L!<br>'
        '<span style="font-weight:300;font-size:.82rem">'
        'Verifique o sistema de aeração imediatamente.</span>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── Cards de Leituras Atuais ───────────────────────────────────────────────────
st.markdown('<div class="secao-label">📡 &nbsp; Leituras Atuais</div>', unsafe_allow_html=True)

# --- Oxigênio Dissolvido ---
card_o2  = "card-o2-warn" if alerta_o2 else "card-o2-ok"
val_o2   = "val-o2-warn"  if alerta_o2 else "val-o2-ok"
badge_o2 = (
    '<span class="badge badge-warn">⚠ CRÍTICO</span>'
    if alerta_o2 else
    '<span class="badge badge-ok">✓ Normal</span>'
)
st.markdown(f"""
<div class="card {card_o2}">
  <span class="card-icon">💧</span>
  <div class="card-label">Oxigênio Dissolvido</div>
  <div class="card-value {val_o2}">{o2:.2f}<span class="card-unit"> mg/L</span></div>
  {badge_o2}
</div>
""", unsafe_allow_html=True)

# --- Temperatura ---
badge_temp = (
    '<span class="badge badge-attn">⚠ Fora do Ideal</span>'
    if atencao_temp else
    '<span class="badge badge-ok">✓ Ideal  (26–32°C)</span>'
)
st.markdown(f"""
<div class="card card-temp">
  <span class="card-icon">🌡️</span>
  <div class="card-label">Temperatura da Água</div>
  <div class="card-value val-temp">{temp:.1f}<span class="card-unit"> °C</span></div>
  {badge_temp}
</div>
""", unsafe_allow_html=True)

# --- pH ---
badge_ph = (
    '<span class="badge badge-attn">⚠ Fora do Ideal</span>'
    if atencao_ph else
    '<span class="badge badge-ok">✓ Ideal  (7.5–8.5)</span>'
)
st.markdown(f"""
<div class="card card-ph">
  <span class="card-icon">⚗️</span>
  <div class="card-label">pH da Água</div>
  <div class="card-value val-ph">{ph:.2f}</div>
  {badge_ph}
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  GRÁFICO HISTÓRICO — Plotly com 3 subplots e zonas de referência
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="secao-label">📊 &nbsp; Histórico de Medições</div>', unsafe_allow_html=True)

fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    subplot_titles=("Oxigênio Dissolvido (mg/L)", "Temperatura (°C)", "pH"),
    vertical_spacing=0.09,
    row_heights=[0.36, 0.33, 0.31],
)

_marker = dict(size=3.5, opacity=.9)

# ── Subplot 1: Oxigênio ────────────────────────────────────────────────────────
fig.add_trace(go.Scatter(
    x=df["timestamp"], y=df["oxigenio"],
    name="O₂",
    mode="lines+markers",
    line=dict(color="#00d4aa", width=2.2, shape="spline", smoothing=0.8),
    marker=dict(color="#00d4aa", **_marker),
    fill="tozeroy",
    fillcolor="rgba(0,212,170,.06)",
), row=1, col=1)

# Zona crítica (abaixo de 3.0 mg/L) em vermelho suave
fig.add_hrect(
    y0=0, y1=3.0,
    fillcolor="rgba(255,60,60,.07)",
    line_width=0,
    row=1, col=1,
)
# Linha de limite crítico
fig.add_shape(
    type="line", xref="x domain", x0=0, x1=1,
    yref="y1", y0=3.0, y1=3.0,
    line=dict(color="rgba(255,80,80,.55)", width=1.2, dash="dot"),
    row=1, col=1,
)

# ── Subplot 2: Temperatura ─────────────────────────────────────────────────────
fig.add_trace(go.Scatter(
    x=df["timestamp"], y=df["temperatura"],
    name="Temp",
    mode="lines+markers",
    line=dict(color="#f4a322", width=2.2, shape="spline", smoothing=0.8),
    marker=dict(color="#f4a322", **_marker),
    fill="tozeroy",
    fillcolor="rgba(244,163,34,.05)",
), row=2, col=1)

# Faixa ideal (26–32°C) em amarelo suave
fig.add_hrect(
    y0=26, y1=32,
    fillcolor="rgba(244,163,34,.09)",
    line_width=0,
    row=2, col=1,
)

# ── Subplot 3: pH ──────────────────────────────────────────────────────────────
fig.add_trace(go.Scatter(
    x=df["timestamp"], y=df["ph"],
    name="pH",
    mode="lines+markers",
    line=dict(color="#9d71ea", width=2.2, shape="spline", smoothing=0.8),
    marker=dict(color="#9d71ea", **_marker),
    fill="tozeroy",
    fillcolor="rgba(157,113,234,.06)",
), row=3, col=1)

# Faixa ideal pH (7.5–8.5) em roxo suave
fig.add_hrect(
    y0=7.5, y1=8.5,
    fillcolor="rgba(157,113,234,.1)",
    line_width=0,
    row=3, col=1,
)

# ── Estilização do layout Plotly ───────────────────────────────────────────────
fig.update_layout(
    height=490,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#2d7fa8", size=11),
    showlegend=False,
    margin=dict(l=0, r=8, t=32, b=0),
)

# Títulos dos subplots (são anotações do Plotly)
fig.update_annotations(
    font=dict(color="#3a7fa0", size=10.5, family="DM Sans, sans-serif")
)

# Eixos X e Y — estilo consistente
axis_style = dict(
    showgrid=True,
    gridcolor="rgba(255,255,255,.04)",
    zeroline=False,
    showline=False,
    tickfont=dict(size=9, color="#1e5570"),
)
for row in range(1, 4):
    fig.update_xaxes(**axis_style, row=row, col=1)
    fig.update_yaxes(**axis_style, row=row, col=1)

# Formato de hora no eixo X do subplot inferior
fig.update_xaxes(tickformat="%H:%M", row=3, col=1)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ═══════════════════════════════════════════════════════════════════════════════
#  RODAPÉ COM STATUS AO VIVO E CONTADOR REGRESSIVO
# ═══════════════════════════════════════════════════════════════════════════════
ts_fmt   = ts_ult.strftime("%d/%m/%Y %H:%M:%S") if isinstance(ts_ult, datetime) else str(ts_ult)
n_reg    = len(df)
contador = st.empty()

for seg in range(5, 0, -1):
    contador.markdown(f"""
    <div class="rodape">
        <span class="live-dot"></span>
        Ao vivo &nbsp;·&nbsp;
        Última leitura: <b>{ts_fmt}</b> &nbsp;·&nbsp;
        {n_reg} registros &nbsp;·&nbsp;
        Atualizando em <b>{seg}s</b>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(1)

# ── Re-run automático ──────────────────────────────────────────────────────────
st.rerun()
