# 🦐 AquaMonitor — Guia de Configuração e Uso

Sistema IoT para monitoramento de tanque de camarão (carcinicultura).

---

## 📁 Estrutura de Arquivos

```
aqua-monitor/
├── app.py                     ← Dashboard web (Streamlit)
├── simulador_sensor.py        ← Gerador de dados fictícios
├── requirements.txt           ← Dependências Python
└── README.md
```

---

## 📦 Passo 1 — Instalar Dependências

```bash
pip install -r requirements.txt
```

Ou manualmente:

```bash
pip install streamlit firebase-admin pandas plotly
```

---

## ▶️ Passo 2 — Executar o Projeto

### Terminal 1 — Iniciar o Simulador

```bash
python simulador_sensor.py
```

O simulador começa a gravar medições no Firestore a cada **5 segundos**.
A cada ~60 ciclos (~5 min), ele simula um **evento crítico de baixo O₂**
para demonstrar o alerta vermelho no dashboard.

### Terminal 2 — Iniciar o Dashboard

```bash
streamlit run app.py
```

O dashboard abre automaticamente em `http://localhost:8501`.

---

## 📱 Acesso pelo Celular (Demonstração)

Para acessar o dashboard pelo celular durante a apresentação:

1. Certifique-se que o PC e o celular estão na **mesma rede Wi-Fi**
2. Descubra o IP do PC:
   - Windows: `ipconfig` no CMD
   - Linux/Mac: `ifconfig` ou `ip addr`
3. Acesse no celular: `http://<IP-DO-PC>:8501`

---

## 🔑 Estrutura do Documento no Firestore

Cada documento na coleção `medicoes` possui:

```json
{
  "timestamp":   "2025-06-02T14:30:00",
  "oxigenio":    6.42,
  "temperatura": 28.3,
  "ph":          7.98
}
```

---

## 🚨 Limites e Alertas

| Variável    | Faixa Ideal | Alerta Crítico |
|-------------|-------------|----------------|
| Oxigênio    | > 5.0 mg/L  | < 3.0 mg/L 🔴  |
| Temperatura | 26–32°C     | Fora da faixa  |
| pH          | 7.5–8.5     | Fora da faixa  |

---

## 🛠️ Troubleshooting

**Erro: `firebase-credentials.json not found`**
→ Verifique se o arquivo está na mesma pasta que os scripts.

**Erro: `PERMISSION_DENIED` no Firestore**
→ No Firebase Console, ajuste as regras do Firestore para permitir leitura/escrita.

**Dashboard não atualiza**
→ Certifique-se que o `simulador_sensor.py` está rodando em outro terminal.

**Celular não acessa o dashboard**
→ Verifique se o firewall do PC está bloqueando a porta 8501.
→ Tente: `streamlit run app.py --server.address 0.0.0.0`
