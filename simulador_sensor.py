"""
simulador_sensor.py
═══════════════════════════════════════════════════════════════════
Simulador de sensores IoT para tanque de camarão (carcinicultura).
Gera dados fictícios coerentes e os envia ao Firestore a cada 5s.

COMO USAR:
  1. Coloque 'firebase-credentials.json' na mesma pasta deste arquivo.
  2. pip install firebase-admin
  3. python simulador_sensor.py
═══════════════════════════════════════════════════════════════════
"""

import time
import math
import random
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore


# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURAÇÃO DO FIREBASE
#  Baixe o JSON em: Firebase Console → Configurações do Projeto
#  → Contas de Serviço → Gerar Nova Chave Privada
# ─────────────────────────────────────────────────────────────────────────────
cred = credentials.Certificate("firebase-credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
colecao = db.collection("medicoes")


# ─────────────────────────────────────────────────────────────────────────────
#  ESTADO INICIAL — valores típicos de um tanque saudável
# ─────────────────────────────────────────────────────────────────────────────
estado = {
    "oxigenio":    6.5,   # mg/L  — ideal: > 5.0
    "temperatura": 28.5,  # °C    — ideal: 26–32°C
    "ph":          7.95,  # adim. — ideal: 7.5–8.5
}


def proxima_leitura(atual: dict, ciclo: int) -> dict:
    """
    Calcula a próxima leitura simulando oscilações realistas:
      - Random walk com derive suave entre chamadas
      - Ciclo diurno: fotossíntese/respiração elevaoxigênio ao meio-dia
      - Evento crítico de baixo O₂ a cada 60 ciclos (~5 min)
        para demonstrar o ALERTA no dashboard durante a apresentação
    """
    hora = datetime.now().hour

    # Variação natural (random walk)
    delta_o2   = random.uniform(-0.25, 0.25)
    delta_temp = random.uniform(-0.10, 0.10)
    delta_ph   = random.uniform(-0.03, 0.03)

    # Efeito do ciclo diurno sobre o O₂ (fotossíntese de microalgas)
    fator_diurno = math.sin(math.pi * hora / 12.0) * 0.35
    delta_o2 += fator_diurno

    o2   = atual["oxigenio"]    + delta_o2
    temp = atual["temperatura"] + delta_temp
    ph   = atual["ph"]          + delta_ph

    # ── EVENTO CRÍTICO DE DEMONSTRAÇÃO ──────────────────────────────────────
    # A cada 60 ciclos (≈5 min) o O₂ cai abaixo do limite crítico de 3.0 mg/L
    # para você mostrar o ALERTA VERMELHO ao professor durante a apresentação.
    if ciclo > 0 and ciclo % 60 == 0:
        print("\n" + "─" * 55)
        print("  ⚠️  [DEMO] Disparando evento crítico de baixo O₂...")
        print("─" * 55 + "\n")
        o2 = random.uniform(1.8, 2.9)

    # Limites físicos realistas do ambiente aquático
    return {
        "oxigenio":    round(max(0.5,  min(12.0, o2)),   2),
        "temperatura": round(max(24.0, min(34.0, temp)),  2),
        "ph":          round(max(7.0,  min(9.0,  ph)),    2),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  LOOP PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
ciclo = 0

print("╔══════════════════════════════════════════════════════╗")
print("║   🦐  AquaMonitor — Simulador de Sensores            ║")
print("║   Gravando no Firestore a cada 5 segundos            ║")
print("║   Pressione Ctrl+C para encerrar                     ║")
print("╚══════════════════════════════════════════════════════╝\n")

while True:
    try:
        leitura = proxima_leitura(estado, ciclo)

        # Documento enviado ao Firestore
        documento = {
            "timestamp":   datetime.now(),          # hora local (para o demo)
            "oxigenio":    leitura["oxigenio"],
            "temperatura": leitura["temperatura"],
            "ph":          leitura["ph"],
        }
        colecao.add(documento)

        estado = leitura
        ciclo += 1

        # Console output
        status  = "🚨 CRÍTICO" if leitura["oxigenio"] < 3.0 else "✅ Normal "
        ts_str  = documento["timestamp"].strftime("%H:%M:%S")
        print(
            f"  [{ts_str}] {status}  |  "
            f"O₂: {leitura['oxigenio']:5.2f} mg/L  |  "
            f"Temp: {leitura['temperatura']:5.2f}°C  |  "
            f"pH: {leitura['ph']:4.2f}"
        )

        time.sleep(5)

    except KeyboardInterrupt:
        print("\n\n  Simulador encerrado pelo usuário. Até logo! 🦐\n")
        break
    except Exception as e:
        print(f"\n  ❌ Erro: {e}\n  Tentando novamente em 5 segundos...")
        time.sleep(5)
