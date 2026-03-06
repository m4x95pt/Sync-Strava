import os
import requests
from datetime import datetime

# ─── Config ──────────────────────────────────────────────────────────────────
STRAVA_CLIENT_ID     = os.environ["STRAVA_CLIENT_ID"]
STRAVA_CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
STRAVA_REFRESH_TOKEN = os.environ["STRAVA_REFRESH_TOKEN"]
NOTION_TOKEN         = os.environ["NOTION_TOKEN"]
STRAVA_DB_ID         = "a7aecc46c1454d9494d7cfb2d87ba57e"  # nova database

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

TIPO_MAP = {
    "Run": "Corrida", "TrailRun": "Corrida",
    "Ride": "Ciclismo", "VirtualRide": "Ciclismo",
    "Walk": "Caminhada", "Hike": "Caminhada",
    "Swim": "Natação",
}


# ─── Strava ───────────────────────────────────────────────────────────────────

def get_access_token():
    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id":     STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "refresh_token": STRAVA_REFRESH_TOKEN,
            "grant_type":    "refresh_token",
        },
    )
    resp.raise_for_status()
    print("✅ Strava: token obtido")
    return resp.json()["access_token"]


def get_strava_activities(token, per_page=30):
    resp = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {token}"},
        params={"per_page": per_page, "page": 1},
    )
    resp.raise_for_status()
    activities = resp.json()
    print(f"✅ Strava: {len(activities)} actividade(s) encontradas")
    return activities


def get_activity_detail(token, activity_id):
    """Busca detalhes completos de uma actividade (inclui calorias)."""
    resp = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    return resp.json()


# ─── Formatters ──────────────────────────────────────────────────────────────

def format_tempo(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    return f"{m}m {s:02d}s"


def format_pace(speed_ms, tipo):
    if not speed_ms:
        return "—"
    if tipo in ("Corrida", "Caminhada"):
        pace_s = 1000 / speed_ms
        return f"{int(pace_s // 60)}:{int(pace_s % 60):02d} /km"
    return f"{speed_ms * 3.6:.1f} km/h"


# ─── Notion ───────────────────────────────────────────────────────────────────

def get_existing_strava_ids():
    existing = set()
    cursor = None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        resp = requests.post(
            f"https://api.notion.com/v1/databases/{STRAVA_DB_ID}/query",
            headers=NOTION_HEADERS, json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        for page in data.get("results", []):
            url = page.get("properties", {}).get("Link Strava", {}).get("url", "")
            if url:
                existing.add(url.rstrip("/").split("/")[-1])
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    print(f"✅ Notion: {len(existing)} actividade(s) já registada(s)")
    return existing


def create_notion_entry(activity):
    tipo_strava = activity.get("sport_type") or activity.get("type", "")
    tipo        = TIPO_MAP.get(tipo_strava, "Outro")
    distancia   = round(activity.get("distance", 0) / 1000, 2)
    tempo_s     = activity.get("moving_time", 0)
    velocidade  = activity.get("average_speed", 0)
    bpm_medio   = activity.get("average_heartrate")
    bpm_max     = activity.get("max_heartrate")
    elevacao    = activity.get("total_elevation_gain")
    calorias    = activity.get("calories")  # só existe no detalhe
    titulo      = activity.get("name", "Treino")
    activity_id = activity.get("id")
    data_iso    = activity.get("start_date_local", "")[:10]

    try:
        data_fmt = datetime.strptime(data_iso, "%Y-%m-%d").strftime("%-d %b")
    except Exception:
        data_fmt = data_iso

    nome = f"{tipo} · {data_fmt}"
    pace = format_pace(velocidade, tipo)
    tempo_fmt = format_tempo(tempo_s)

    body = {
        "parent": {"database_id": STRAVA_DB_ID},
        "properties": {
            "Name":                    {"title": [{"text": {"content": nome}}]},
            "Data":                    {"date": {"start": data_iso}},
            "Tipo":                    {"select": {"name": tipo}},
            "Título Strava":           {"rich_text": [{"text": {"content": titulo}}]},
            "Distância (km)":          {"number": distancia},
            "Tempo":                   {"rich_text": [{"text": {"content": tempo_fmt}}]},
            "Pace Médio":              {"rich_text": [{"text": {"content": pace}}]},
            "Velocidade Média (km/h)": {"number": round(velocidade * 3.6, 1)},
            "Link Strava":             {"url": f"https://www.strava.com/activities/{activity_id}"},
        },
    }

    if bpm_medio:
        body["properties"]["BPM Médio"]   = {"number": round(bpm_medio)}
    if bpm_max:
        body["properties"]["BPM Máximo"]  = {"number": round(bpm_max)}
    if elevacao is not None:
        body["properties"]["Elevação (m)"] = {"number": round(elevacao)}
    if calorias:
        body["properties"]["Calorias"]    = {"number": round(calorias)}

    resp = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS, json=body)
    resp.raise_for_status()
    cal_str = f" · {round(calorias)} kcal" if calorias else ""
    print(f"  ✅ {nome} — {distancia} km · {tempo_fmt} · {pace}{cal_str}")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔑 A obter token do Strava...")
    token = get_access_token()

    print("\n🏃 A buscar actividades do Strava...")
    activities = get_strava_activities(token, per_page=30)

    print("\n📋 A verificar o que já está no Notion...")
    existing_ids = get_existing_strava_ids()

    novas = [a for a in activities if str(a.get("id", "")) not in existing_ids]
    print(f"\n🔄 {len(novas)} actividade(s) nova(s) para sincronizar...")

    criadas = 0
    for a in novas:
        activity_id = str(a.get("id", ""))
        try:
            # Buscar detalhe completo para ter calorias
            print(f"  → A buscar detalhe de: {a.get('name', '?')}...")
            detail = get_activity_detail(token, activity_id)
            create_notion_entry(detail)
            criadas += 1
        except Exception as e:
            print(f"  ⚠️  Erro em {a.get('name', '?')}: {e}")

    print(f"\n✅ Sync concluído!")
    print(f"   → {criadas} actividade(s) adicionada(s)")
    print(f"   → {len(activities) - len(novas)} já existiam")
