# Genera actividad.svg con datos vivos de GitHub. Lo corre la Action cada día.
import json
import os
import urllib.request

USUARIO = "Brunich"
SEMANAS = 26
TOKEN = os.environ["GH_TOKEN"]

CONSULTA = """
query($u: String!) {
  user(login: $u) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes { languages(first: 10) { edges { size node { name } } } }
    }
  }
}
"""

# Colores propios: los de linguist se pierden sobre fondo oscuro
COLORES = ["#58a6ff", "#3fb950", "#d29922", "#bc8cff", "#f778ba"]
GRIS = "#8b949e"


def consultar():
    cuerpo = json.dumps({"query": CONSULTA, "variables": {"u": USUARIO}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=cuerpo,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)["data"]["user"]


def curva(puntos):
    # Catmull-Rom a Bézier para que la línea no se vea en picos
    d = f"M{puntos[0][0]:.1f},{puntos[0][1]:.1f}"
    for i in range(len(puntos) - 1):
        p0 = puntos[max(i - 1, 0)]
        p1, p2 = puntos[i], puntos[i + 1]
        p3 = puntos[min(i + 2, len(puntos) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def main():
    u = consultar()
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]

    semanas = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]][-SEMANAS:]
    inicio = cal["weeks"][-SEMANAS]["contributionDays"][0]["date"]
    tope = max(max(semanas), 1)
    x0, x1, y0, y1 = 24, 396, 180, 70
    paso = (x1 - x0) / (len(semanas) - 1)
    pts = [(x0 + i * paso, y0 - (v / tope) * (y0 - y1)) for i, v in enumerate(semanas)]
    linea = curva(pts)
    area = f"{linea} L{x1},{y0} L{x0},{y0} Z"
    ultimo = pts[-1]

    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    etiquetas = []
    for i, w in enumerate(cal["weeks"][-SEMANAS:]):
        dia = w["contributionDays"][0]["date"]
        if i == 0 or dia[5:7] != cal["weeks"][-SEMANAS + i - 1]["contributionDays"][0]["date"][5:7]:
            if i < len(semanas) - 2:
                etiquetas.append(f'<text x="{x0 + i * paso:.1f}" y="204">{meses[int(dia[5:7]) - 1]}</text>')

    lenguajes = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            lenguajes[e["node"]["name"]] = lenguajes.get(e["node"]["name"], 0) + e["size"]
    total = sum(lenguajes.values()) or 1
    orden = sorted(lenguajes.items(), key=lambda kv: -kv[1])
    top = orden[:5]
    otros = total - sum(v for _, v in top)
    filas = [(n, v, COLORES[i]) for i, (n, v) in enumerate(top)] + [("Otros", otros, GRIS)]

    barra, x = [], 440.0
    for _, v, c in filas:
        ancho = 360 * v / total
        barra.append(f'<rect x="{x:.1f}" y="70" width="{ancho:.1f}" height="10" fill="{c}"/>')
        x += ancho
    leyenda = []
    for i, (n, v, c) in enumerate(filas):
        lx = 446 + (i // 3) * 180
        ly = 112 + (i % 3) * 30
        pct = f"{100 * v / total:.1f}".replace(".", ",")
        leyenda.append(
            f'<circle cx="{lx}" cy="{ly - 4}" r="5" fill="{c}"/>'
            f'<text x="{lx + 12}" y="{ly}" class="s">{n} <tspan class="v">{pct} %</tspan></text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="820" height="220" viewBox="0 0 820 220" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif">
  <style>
    .t {{ fill: #1f2328; font-size: 14px; font-weight: 600; }}
    .s {{ fill: #59636e; font-size: 12px; }}
    .v {{ fill: #818b98; }}
    .ln {{ stroke: #d1d9e0; }}
    @media (prefers-color-scheme: dark) {{
      .t {{ fill: #f0f6fc; }}
      .s {{ fill: #9198a1; }}
      .v {{ fill: #6e7681; }}
      .ln {{ stroke: #3d444d; }}
    }}
  </style>
  <defs>
    <linearGradient id="relleno" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#3fb950" stop-opacity=".35"/>
      <stop offset="1" stop-color="#3fb950" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="barra"><rect x="440" y="70" width="360" height="10" rx="5"/></clipPath>
  </defs>

  <text x="20" y="28" class="t">Actividad semanal</text>
  <text x="20" y="46" class="s">{cal["totalContributions"]} contribuciones en el último año · {cc["totalCommitContributions"]} commits · {cc["totalPullRequestContributions"]} PR · {cc["totalIssueContributions"]} issues</text>
  <line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" class="ln"/>
  <path d="{area}" fill="url(#relleno)"/>
  <path d="{linea}" fill="none" stroke="#3fb950" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="{ultimo[0]:.1f}" cy="{ultimo[1]:.1f}" r="4" fill="#3fb950"/>
  <g class="s" text-anchor="start">{"".join(etiquetas)}</g>

  <text x="440" y="28" class="t">Lenguajes</text>
  <text x="440" y="46" class="s">por volumen de código en mis repos</text>
  <g clip-path="url(#barra)">{"".join(barra)}</g>
  {"".join(leyenda)}
</svg>
"""
    ruta = os.path.join(os.path.dirname(__file__), "..", "actividad.svg")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"actividad.svg desde {inicio}: {sum(semanas)} contribuciones, {len(lenguajes)} lenguajes")


if __name__ == "__main__":
    main()
