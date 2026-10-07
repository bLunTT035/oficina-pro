from flask import Flask, render_template_string, request, redirect
import os
from datetime import datetime

app = Flask(__name__)

produtos_db = [
    {"id": 1, "nome": "BATERIA MOURA 5AH", "preco": 260.00, "estoque": 5},
    {"id": 2, "nome": "MONTAGEM RAIOS 4MM XRE300", "preco": 300.00, "estoque": 9},
    {"id": 3, "nome": "FILTRO DE AR XRE 300", "preco": 60.00, "estoque": 0},
    {"id": 4, "nome": "FILTRO COMBUSTIVEL XRE300", "preco": 90.00, "estoque": 2},
    {"id": 5, "nome": "CALCO AJUSTE VARIOS", "preco": 60.00, "estoque": 19},
    {"id": 6, "nome": "COXINS TP CABEÇOTE", "preco": 18.00, "estoque": 9},
    {"id": 7, "nome": "JUNTA TP CABEÇOTE XRE300", "preco": 135.00, "estoque": 5},
]
ordens_db = []

def next_id(lista):
    return max([x["id"] for x in lista], default=0) + 1

HTML_BASE = """
<!DOCTYPE html>
<html>
<head>
<title>OFICINA PRO - NA NUVEM</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
    body { margin:0; background:#0f0f0f; color:#fff; font-family: Arial, sans-serif; }
   .header { background:#1a1a1a; border-bottom:3px solid #facc15; padding:12px 20px; display:flex; justify-content:space-between; align-items:center; position:sticky; top:0; z-index:99; }
   .nav a { text-decoration:none; color:#aaa; background:#2a2a2a; padding:6px 12px; border-radius:20px; font-size:12px; margin-left:5px; }
   .nav a.active { background:#facc15; color:#000; font-weight:900; }
   .nav a.cta { background:#facc15; color:#000; font-weight:900; }
   .container { max-width:800px; margin:24px auto; padding:0 16px; }
   .card { background:#1e1e1e; border-radius:12px; padding:22px; border:1px solid #2a2a2a; margin-bottom:16px; }
    input, textarea, select { background:#2a2a2a; border:1px solid #333; color:#fff; padding:11px; border-radius:8px; width:100%; box-sizing:border-box; }
   .btn { background:#facc15; color:#000; border:none; padding:13px; border-radius:10px; font-weight:900; cursor:pointer; width:100%; }
   .btn-x { background:#ef4444; color:white; border:none; padding:6px 10px; border-radius:6px; cursor:pointer; font-weight:900; }
   .btn-edit { background:#3b82f6; color:white; border:none; padding:6px 10px; border-radius:6px; cursor:pointer; font-weight:900; }
   .prod-item { background:#2a2a2a; border:2px solid #333; padding:12px; border-radius:10px; margin-bottom:8px; cursor:pointer; display:flex; justify-content:space-between; align-items:center; }
   .prod-item.selected { border-color:#facc15; background:#332e00; }
   .qty-box { display:none; align-items:center; gap:6px; margin-left:10px; }
   .qty-box input { width:60px; text-align:center; background:#000; border:1px solid #facc15; color:#facc15; font-weight:900; }
    th { text-align:left; color:#aaa; font-size:12px; padding:10px 6px; border-bottom:1px solid #333; }
    td { padding:12px 6px; border-bottom:1px solid #222; font-size:13px; }
</style>
</head>
<body>
<div class="header">
  <b>OFICINA PRO - NA NUVEM</b>
  <div class="nav">
    <a href="/" class="{{'active' if active=='inicio' else ''}}">Início</a>
    <a href="/produtos" class="{{'active' if active=='prod' else ''}}">Produtos</a>
    <a href="/historico" class="{{'active' if active=='hist' else ''}}">Histórico</a>
    <a href="/nova_os" class="cta">+ Nova OS</a>
  </div>
</div>
<div class="container">
{{content}}
</div>
<script>
let selected = {};
function toggleProd(id){
  const el = document.getElementById('p-'+id);
  const qtyBox = document.getElementById('qty-'+id);
  if(selected[id]){
    delete selected[id];
    el.classList.remove('selected');
    qtyBox.style.display='none';
  } else {
    selected[id]=1;
    el.classList.add('selected');
    qtyBox.style.display='flex';
    document.getElementById('q-'+id).value=1;
  }
  updateHidden(); calcTotal();
}
function changeQty(id, delta){
  let v = parseInt(document.getElementById('q-'+id).value)||1;
  v+=delta;
  if(v<1) v=1;
  document.getElementById('q-'+id).value=v;
  selected[id]=v;
  updateHidden(); calcTotal();
}
function onQtyInput(id){
  let v = parseInt(document.getElementById('q-'+id).value)||1;
  if(v<1) v=1;
  selected[id]=v;
  updateHidden(); calcTotal();
}
function updateHidden(){
  let arr=[];
  for(let id in selected){ arr.push(id+':'+selected[id]); }
  document.getElementById('produtos_input').value = arr.join(',');
}
function calcTotal(){
  const mao = parseFloat(document.getElementById('mao').value)||0;
  let totalProd=0;
  for(let id in selected){
    const precoEl = document.getElementById('preco-'+id);
    if(precoEl){ totalProd += parseFloat(precoEl.value)*selected[id]; }
  }
  const total = mao+totalProd;
  document.getElementById('total_auto').value = total.toFixed(2);
  document.getElementById('total_view').innerText = 'R$ '+total.toFixed(2);
  document.getElementById('btn_total').innerText = 'SALVAR SERVICO - R$ '+total.toFixed(2);
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    content = f"""
    <div class="card"><h3>Oficina Pro</h3><p style="color:#aaa;">{len(produtos_db)} produtos • {len(ordens_db)} OS</p>
    <a href="/nova_os"><button class="btn" style="margin-top:12px;">+ NOVA OS - CALCULO AUTOMATICO</button></a></div>
    """
    return render_template_string(HTML_BASE.replace("{{content}}", content), active="inicio")

@app.route("/produtos", methods=["GET","POST"])
def produtos():
    global produtos_db
    if request.method=="POST":
        acao=request.form.get("acao"); pid=request.form.get("id")
        if acao=="add":
            produtos_db.append({"id": next_id(produtos_db),"nome": request.form.get("nome").upper(),"preco": float(request.form.get("preco") or 0),"estoque": int(request.form.get("estoque") or 0)})
        elif acao=="delete" and pid:
            produtos_db=[p for p in produtos_db if str(p["id"])!=str(pid)]
        elif acao=="edit" and pid:
            p=next((x for x in produtos_db if str(x["id"])==str(pid)),None)
            if p: p["nome"]=request.form.get("nome").upper(); p["preco"]=float(request.form.get("preco") or 0); p["estoque"]=int(request.form.get("estoque") or 0)
        return redirect("/produtos")
    edit_id=request.args.get("edit", type=int); rows=""
    for p in produtos_db:
        if edit_id==p["id"]:
            rows+=f"""<tr style="background:#2a2a2a;"><td colspan="4"><form method="POST" style="display:grid; grid-template-columns:2fr 1fr 1fr 1fr; gap:8px;"><input type="hidden" name="acao" value="edit"><input type="hidden" name="id" value="{p['id']}"><input name="nome" value="{p['nome']}" required><input name="preco" type="number" step="0.01" value="{p['preco']}" required><input name="estoque" type="number" value="{p['estoque']}" required><div style="display:flex; gap:4px;"><button class="btn" style="padding:8px;">Salvar</button><a href="/produtos" style="background:#444; color:#fff; padding:8px 12px; border-radius:8px; text-decoration:none;">X</a></div></form></td></tr>"""
        else:
            rows+=f"""<tr><td>{p['nome']}</td><td>R$ {p['preco']:.2f}</td><td>{p['estoque']}</td><td style="text-align:right;"><a href="/produtos?edit={p['id']}" style="text-decoration:none;"><button class="btn-edit">✏️</button></a><form method="POST" style="display:inline;" onsubmit="return confirm('Excluir?')"><input type="hidden" name="acao" value="delete"><input type="hidden" name="id" value="{p['id']}"><button class="btn-x">X</button></form></td></tr>"""
    content=f"""
    <div class="card"><h3>Produtos</h3>
      <form method="POST" style="display:grid; grid-template-columns:2fr 1fr 1fr 1fr; gap:8px; margin-bottom:12px;"><input type="hidden" name="acao" value="add"><input name="nome" placeholder="NOME" required><input name="preco" type="number" step="0.01" placeholder="Preço" required><input name="estoque" type="number" placeholder="Qtd" required><button class="btn">+ Add</button></form>
      <table><tr><th>Nome</th><th>Preço</th><th>Est</th><th></th></tr>{rows}</table>
      <p style="color:#666; font-size:11px; margin-top:10px;">Clique no ✏️ para editar preço e estoque</p>
    </div>"""
    return render_template_string(HTML_BASE.replace("{{content}}", content), active="prod")

@app.route("/nova_os", methods=["GET","POST"])
def nova_os():
    global produtos_db, ordens_db
    if request.method=="POST":
        cliente=request.form.get("cliente"); placa=request.form.get("placa"); veiculo=request.form.get("veiculo"); feito=request.form.get("feito")
        mao=float(request.form.get("mao") or 0); produtos_str=request.form.get("produtos") or ""; total=float(request.form.get("total_auto") or 0)
        itens=[]; texto_produtos=[]
        if produtos_str:
            for item in produtos_str.split(","):
                if ":" in item:
                    pid, qty = item.split(":")
                    if pid.isdigit():
                        p=next((x for x in produtos_db if str(x["id"])==pid), None)
                        if p:
                            q=int(qty)
                            itens.append({"nome": p["nome"], "preco": p["preco"], "qtd": q, "subtotal": p["preco"]*q})
                            texto_produtos.append(f"{q}x {p['nome']}")
                            # baixa estoque
                            p["estoque"] = max(0, p["estoque"]-q)
        ordens_db.append({"id": len(ordens_db)+1, "cliente": cliente, "placa": placa, "veiculo": veiculo, "feito": feito, "mao": mao, "itens": itens, "texto": ", ".join(texto_produtos), "total": total, "data": datetime.now().strftime("%d/%m/%Y %H:%M")})
        return redirect("/historico")

    lista=""
    for p in produtos_db:
        lista+=f"""
        <div class="prod-item" id="p-{p['id']}" onclick="toggleProd({p['id']})">
          <div><b>{p['nome']}</b><br><small style="color:#aaa;">R$ {p['preco']:.2f} - Est: {p['estoque']}</small></div>
          <div style="display:flex; align-items:center;">
            <div class="qty-box" id="qty-{p['id']}" onclick="event.stopPropagation();">
              <button type="button" onclick="changeQty({p['id']},-1)" style="background:#444; color:#fff; border:none; width:28px; height:28px; border-radius:6px; font-weight:900;">-</button>
              <input id="q-{p['id']}" type="number" value="1" min="1" oninput="onQtyInput({p['id']})" onclick="event.stopPropagation();">
              <button type="button" onclick="changeQty({p['id']},1)" style="background:#facc15; color:#000; border:none; width:28px; height:28px; border-radius:6px; font-weight:900;">+</button>
            </div>
            <span style="margin-left:8px; color:#666;">✓</span>
          </div>
          <input type="hidden" id="preco-{p['id']}" value="{p['preco']}">
        </div>
        """
    content=f"""
    <div class="card">
      <h3>+ Nova OS - Cálculo Automático</h3>
      <form method="POST">
        <div style="display:grid; grid-template-columns:2fr 1fr 1fr; gap:10px;">
          <div><label style="font-size:11px; color:#aaa;">Cliente *</label><input name="cliente" required></div>
          <div><label style="font-size:11px; color:#aaa;">Placa</label><input name="placa"></div>
          <div><label style="font-size:11px; color:#aaa;">Veículo</label><input name="veiculo"></div>
        </div>
        <div style="margin-top:12px;"><label style="font-size:11px; color:#aaa;">O que foi feito *</label><textarea name="feito" rows="3" required></textarea></div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:12px;">
          <div><label style="font-size:11px; color:#aaa;">Mão de Obra R$</label><input id="mao" name="mao" type="number" value="0" oninput="calcTotal()"></div>
          <div><label style="font-size:11px; color:#aaa;">Total Automático</label><input id="total_auto" name="total_auto" readonly style="border-color:#facc15; background:#000; color:#facc15; font-weight:900;"><small id="total_view" style="color:#facc15; font-weight:900;">R$ 0.00</small></div>
        </div>
        <div style="margin-top:18px;"><label style="font-size:11px; color:#aaa;">Produtos usados (clique que soma no total automaticamente)</label><input type="hidden" name="produtos" id="produtos_input"><div style="max-height:380px; overflow:auto; margin-top:8px;">{lista}</div></div>
        <button class="btn" type="submit" id="btn_total" style="margin-top:16px;">SALVAR SERVIÇO - R$ 0.00</button>
      </form>
      <p style="color:#666; font-size:11px; margin-top:10px;">NOVO: Agora clique no produto e escolha a quantidade com + e -. Ex: 2x filtro, 4x calço</p>
    </div>
    """
    return render_template_string(HTML_BASE.replace("{{content}}", content), active="nova")

@app.route("/historico")
def historico():
    rows=""
    for o in reversed(ordens_db):
        rows+=f"<tr><td style='padding:10px; border-bottom:1px solid #222;'>{o['data']}</td><td style='padding:10px; border-bottom:1px solid #222; font-weight:800;'>{o['cliente']}<br><small style='color:#aaa;'>{o['placa']} {o['veiculo']}</small></td><td style='padding:10px; border-bottom:1px solid #222;'>{o['feito']}<br><small style='color:#facc15;'>{o['texto']}</small></td><td style='padding:10px; border-bottom:1px solid #222; font-weight:900; color:#facc15;'>R$ {o['total']:.2f}</td></tr>"
    if not rows: rows="<tr><td colspan=4 style='padding:24px; text-align:center; color:#666;'>Nenhuma OS ainda</td></tr>"
    content=f"<div class='card'><h3>Histórico</h3><table style='width:100%; border-collapse:collapse;'><tr><th>Data</th><th>Cliente</th><th>Serviço</th><th>Total</th></tr>{rows}</table></div>"
    return render_template_string(HTML_BASE.replace("{{content}}", content), active="hist")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
