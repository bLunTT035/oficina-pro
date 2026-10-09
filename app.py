import os
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, render_template_string, request, redirect, send_file
import sqlite3
from io import BytesIO
import re

app = Flask(__name__)
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = False
if DATABASE_URL:
    try:
        import psycopg2
        USE_POSTGRES = True
    except:
        USE_POSTGRES = False

def get_conn():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    else:
        conn = sqlite3.connect('oficina.db')
        conn.row_factory = sqlite3.Row
        return conn

def get_horario_brasilia():
    # CORREÇÃO FUSO: Força Brasília
    return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute('CREATE TABLE IF NOT EXISTS produtos (id SERIAL PRIMARY KEY, nome TEXT, preco REAL, estoque INTEGER)')
        cur.execute('CREATE TABLE IF NOT EXISTS servicos (id SERIAL PRIMARY KEY, cliente TEXT, carro TEXT, descricao TEXT, valor REAL, data TEXT, placa TEXT, veiculo TEXT, produtos_usados TEXT)')
    else:
        cur.execute('CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, estoque INTEGER)')
        cur.execute('CREATE TABLE IF NOT EXISTS servicos (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, placa TEXT, veiculo TEXT, carro TEXT, descricao TEXT, valor REAL, data TEXT, produtos_usados TEXT)')
    conn.commit()
    conn.close()

def buscar_servicos(filtro=""):
    conn = get_conn()
    cur = conn.cursor()
    if filtro:
        if USE_POSTGRES:
            cur.execute("SELECT id, cliente, placa, veiculo, carro, descricao, valor, data, produtos_usados FROM servicos WHERE cliente ILIKE %s OR placa ILIKE %s OR veiculo ILIKE %s OR descricao ILIKE %s ORDER BY id DESC", (f"%{filtro}%",f"%{filtro}%",f"%{filtro}%",f"%{filtro}%"))
        else:
            cur.execute("SELECT id, cliente, placa, veiculo, carro, descricao, valor, data, produtos_usados FROM servicos WHERE cliente LIKE? OR placa LIKE? OR veiculo LIKE? OR descricao LIKE? ORDER BY id DESC", (f"%{filtro}%",f"%{filtro}%",f"%{filtro}%",f"%{filtro}%"))
    else:
        cur.execute("SELECT id, cliente, placa, veiculo, carro, descricao, valor, data, produtos_usados FROM servicos ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    lista=[]
    for r in rows:
        if USE_POSTGRES:
            id_, cliente, placa, veiculo, carro, descricao, valor, data, prod = r
        else:
            id_=r['id']; cliente=r['cliente']; placa=r['placa']; veiculo=r['veiculo']; carro=r['carro']; descricao=r['descricao']; valor=r['valor']; data=r['data']; prod=r['produtos_usados']
        lista.append({"id":id_, "cliente":cliente or "", "placa":placa or "", "veiculo":veiculo or carro or "", "descricao":descricao or "", "valor":valor or 0, "data":data or "", "prod":prod or ""})
    return lista

BASE = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Oficina PRO</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#0e0e0e;color:#fff;font-family:Inter,Arial}
.navbar{background:#000!important;border-bottom:3px solid #f7b500;padding:12px 15px}
.card-dark{background:#1c1c1c;border:1px solid #2a2a2a;border-radius:12px}
.btn-yellow{background:#f7b500;color:#000;font-weight:800;border-radius:8px;border:none}
.btn-dark2{background:#2a2a2a;color:#fff;border:none;border-radius:8px}
.table{--bs-table-bg:#1c1c1c!important;--bs-table-color:#e0e0e0!important;background:#1c1c1c!important;margin:0}
.table > :not(caption) > * > *{background-color:#1c1c1c!important;color:#ddd!important;box-shadow:none!important;border-color:#222!important}
.table thead th{background:#1c1c1c!important;color:#fff!important;border-bottom:1px solid #333!important}
.table tbody td{background:#1c1c1c!important;color:#ddd!important;border-bottom:1px solid #222!important}
.small-label{color:#888;font-size:13px}
.big-number{font-size:22px;font-weight:700}
.produto-item{background:#252525;border:1px solid #333;border-radius:8px;padding:10px 12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;cursor:pointer}
.produto-item.selected{background:#2e2a15;border-color:#f7b500}
.qty-box{display:none; align-items:center; gap:6px;}
.qty-box input{width:55px; text-align:center; background:#000; border:1px solid #f7b500; color:#f7b500; font-weight:900; border-radius:6px; padding:4px;}
.qty-btn{background:#f7b500; color:#000; border:none; width:28px; height:28px; border-radius:6px; font-weight:900;}
</style>
</head><body>
<nav class="navbar d-flex justify-content-between">
<div class="fw-bold">OFICINA PRO - NA NUVEM</div>
<div class="d-flex gap-2 flex-wrap">
<a href="/" class="btn btn-dark2 btn-sm">Início</a>
<a href="/produtos" class="btn btn-dark2 btn-sm">Produtos</a>
<a href="/historico" class="btn btn-dark2 btn-sm">Histórico</a>
<a href="/exportar_excel" class="btn btn-dark2 btn-sm">Excel OS</a>
<a href="/exportar_produtos" class="btn btn-dark2 btn-sm">Excel Produtos</a>
<a href="/nova_os" class="btn btn-yellow btn-sm">+ Nova OS</a>
</div>
</nav>
<div class="container py-4" style="max-width:950px">{{content|safe}}</div>
</body></html>
"""

# --- ROTAS NORMAIS (index, produtos, etc) continuam iguais ---
@app.route('/')
def index():
    init_db()
    conn = get_conn(); cur = conn.cursor()
    try: cur.execute("SELECT COUNT(*) FROM servicos"); total_serv = cur.fetchone()[0]
    except: total_serv=0
    try: cur.execute("SELECT COALESCE(SUM(valor),0) FROM servicos"); faturado = cur.fetchone()[0] or 0
    except: faturado=0
    try: cur.execute("SELECT COUNT(*) FROM produtos"); total_prod = cur.fetchone()[0]
    except: total_prod=0
    conn.close()
    servicos = buscar_servicos()[:8]
    linhas=""
    for s in servicos:
        linhas+=f"<tr><td>{s['data']}</td><td><b>{s['cliente']}</b><br><span class='small-label'>{s['veiculo']} {s['placa']}</span></td><td>{s['descricao']}<br><span class='small-label' style='color:#f7b500'>{s['prod']}</span></td><td style='white-space:nowrap'>R$ {float(s['valor']):.2f}</td><td><a href='/imprimir/{s['id']}' target='_blank' class='btn btn-sm btn-dark2'>🖨️</a> <a href='/editar_servico/{s['id']}' class='btn btn-sm btn-dark2'>✏️</a> <a href='/excluir_servico/{s['id']}' class='btn btn-sm btn-danger'>🗑️</a></td></tr>"
    html = f"""<div class="row g-3"><div class="col-6"><div class="card-dark p-4"><div class="big-number">{total_serv}</div><div class="small-label mt-2">Serviços</div></div></div><div class="col-6"><div class="card-dark p-4"><div class="big-number">R$ {float(faturado):.2f}</div><div class="small-label mt-2">Faturado</div></div></div></div><div class="card-dark p-4 mt-4"><h6 class="fw-bold mb-3">Últimos Serviços</h6><table class="table"><thead><tr><th>Data</th><th>Cliente</th><th>Feito</th><th>Valor</th><th>Ações</th></tr></thead><tbody>{linhas}</tbody></table></div>"""
    return render_template_string(BASE, content=html)

@app.route('/nova_os', methods=['GET','POST'])
def nova_os():
    init_db()
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM produtos WHERE estoque > 0 ORDER BY nome ASC"); produtos = cur.fetchall()
    if request.method == 'POST':
        cliente = request.form.get('cliente',''); placa = request.form.get('placa',''); veiculo = request.form.get('veiculo','')
        descricao = request.form.get('descricao',''); valor = request.form.get('valor_total','0') or 0
        selecionados = request.form.getlist('produtos')
        data = get_horario_brasilia()
        nomes_usados=[]
        for pid in selecionados:
            try:
                qty = int(request.form.get(f'qty_{pid}', '1') or 1)
                if USE_POSTGRES: cur.execute("SELECT nome FROM produtos WHERE id=%s", (int(pid),))
                else: cur.execute("SELECT nome FROM produtos WHERE id=?", (int(pid),))
                prow = cur.fetchone()
                if prow:
                    nome_p = prow[0] if USE_POSTGRES else prow['nome']
                    nomes_usados.append(f"{qty}x {nome_p}" if qty>1 else nome_p)
                    if USE_POSTGRES: cur.execute("UPDATE produtos SET estoque = estoque - %s WHERE id=%s", (qty, int(pid),))
                    else: cur.execute("UPDATE produtos SET estoque = estoque -? WHERE id=?", (qty, int(pid),))
            except: pass
        prod_txt = ", ".join(nomes_usados)
        carro_full = f"{veiculo} - {placa}".strip(" -")
        if USE_POSTGRES: cur.execute("INSERT INTO servicos (cliente, carro, placa, veiculo, descricao, valor, data, produtos_usados) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (cliente, carro_full, placa, veiculo, descricao, valor, data, prod_txt))
        else: cur.execute("INSERT INTO servicos (cliente, placa, veiculo, carro, descricao, valor, data, produtos_usados) VALUES (?,?,?,?,?,?,?,?)", (cliente, placa, veiculo, carro_full, descricao, valor, data, prod_txt))
        conn.commit(); conn.close(); return redirect('/')
    lista_prod_html=""
    for r in produtos:
        id_, nome, preco, est = (r[0], r[1], r[2], r[3]) if USE_POSTGRES else (r['id'], r['nome'], r['preco'], r['estoque'])
        lista_prod_html += f"""<div class="produto-item" id="item-{id_}" data-preco="{float(preco or 0)}" onclick="toggleProd({id_})"><div><input type="checkbox" name="produtos" value="{id_}" id="chk-{id_}" style="display:none"><b>{nome}</b><br><span class="small-label">R$ {float(preco or 0):.2f} - Est: {est}</span></div><div style="display:flex; align-items:center; gap:8px;"><div class="qty-box" id="qtybox-{id_}" onclick="event.stopPropagation()"><button type="button" class="qty-btn" onclick="changeQty({id_},-1)">-</button><input type="number" id="qty-{id_}" name="qty_{id_}" value="1" min="1" oninput="calcTotal()" onclick="event.stopPropagation()"><button type="button" class="qty-btn" onclick="changeQty({id_},1)">+</button></div><span class="small-label">✓</span></div></div>"""
    if not lista_prod_html: lista_prod_html = "<div class='small-label'>Nenhum produto em estoque.</div>"
    conn.close()
    html = f"""
    <div class="card-dark p-4">
    <h5 class="fw-bold mb-3">+ Nova OS</h5>
    <form method="POST">
      <div class="row g-3">
        <div class="col-md-6"><label class="small-label">Cliente *</label><input name="cliente" class="form-control bg-dark text-white border-secondary" required></div>
        <div class="col-md-3"><label class="small-label">Placa</label><input name="placa" class="form-control bg-dark text-white border-secondary"></div>
        <div class="col-md-3"><label class="small-label">Veículo</label><input name="veiculo" class="form-control bg-dark text-white border-secondary"></div>
        <div class="col-12"><label class="small-label">O que foi feito *</label><textarea name="descricao" rows="3" class="form-control bg-dark text-white border-secondary" required></textarea></div>
        <div class="col-md-3"><label class="small-label">Mão de Obra R$</label><input id="valor_mao" type="number" step="0.01" class="form-control bg-dark text-white border-secondary" placeholder="0.00" oninput="calcTotal()"></div>
        <div class="col-md-5">
          <div class="d-flex justify-content-between align-items-center"><label class="small-label">Total</label><button type="button" id="btnEditar" onclick="toggleEditar()" class="btn btn-sm" style="background:#f7b500;color:#000;font-weight:800;font-size:11px;padding:2px 8px">✏️ Editar</button></div>
          <input id="valor_total" name="valor_total" type="number" step="0.01" class="form-control bg-dark text-white border-secondary" style="border-color:#f7b500!important;font-weight:bold" readonly>
          <div id="valor_display" class="small-label mt-1" style="color:#f7b500">R$ 0.00 - Automático</div>
        </div>
      </div>
      <div class="mt-4"><label class="small-label fw-bold">Produtos usados</label><div class="mt-2" style="max-height:380px;overflow-y:auto">{lista_prod_html}</div></div>
      <button class="btn btn-yellow w-100 py-3 mt-4">SALVAR SERVIÇO - <span id="valor_display2">R$ 0.00</span></button>
    </form>
    </div>
    <script>
    let modoManual = false;
    function toggleEditar(){{
      modoManual =!modoManual;
      const input = document.getElementById('valor_total');
      const btn = document.getElementById('btnEditar');
      const disp = document.getElementById('valor_display');
      if(modoManual){{
        input.removeAttribute('readonly'); input.style.background='#000'; input.style.borderColor='#22c55e'; input.style.color='#22c55e'; input.focus();
        btn.innerText='🔒 Auto'; btn.style.background='#22c55e';
        disp.innerText='✏️ Editando manualmente - digite o valor'; disp.style.color='#22c55e';
      }} else {{
        input.setAttribute('readonly','readonly'); input.style.borderColor='#f7b500'; input.style.color='#fff';
        btn.innerText='✏️ Editar'; btn.style.background='#f7b500';
        calcTotal();
      }}
    }}
    function toggleProd(id){{const el=document.getElementById('item-'+id);const chk=document.getElementById('chk-'+id);const qtybox=document.getElementById('qtybox-'+id);el.classList.toggle('selected');chk.checked=el.classList.contains('selected');qtybox.style.display=chk.checked?'flex':'none';if(!chk.checked){{document.getElementById('qty-'+id).value=1;}}calcTotal();}}
    function changeQty(id, delta){{const inp=document.getElementById('qty-'+id);let v=parseInt(inp.value)||1;v+=delta;if(v<1)v=1;inp.value=v;calcTotal();}}
    function calcTotal(){{if(modoManual)return;let t=parseFloat(document.getElementById('valor_mao').value)||0;document.querySelectorAll('.produto-item.selected').forEach(item=>{{const id=item.id.replace('item-','');const preco=parseFloat(item.dataset.preco)||0;const qty=parseInt(document.getElementById('qty-'+id).value)||1;t+=preco*qty;}});document.getElementById('valor_total').value=t.toFixed(2);document.getElementById('valor_display').innerText='R$ '+t.toFixed(2)+' - Automático';const d2=document.getElementById('valor_display2');if(d2)d2.innerText='R$ '+t.toFixed(2);}}
    </script>
    """
    return render_template_string(BASE, content=html)

@app.route('/editar_servico/<int:id>', methods=['GET','POST'])
def editar_servico(id):
    init_db()
    conn = get_conn(); cur = conn.cursor()
    if USE_POSTGRES: cur.execute("SELECT id, cliente, placa, veiculo, carro, descricao, valor, data, produtos_usados FROM servicos WHERE id=%s", (id,))
    else: cur.execute("SELECT id, cliente, placa, veiculo, carro, descricao, valor, data, produtos_usados FROM servicos WHERE id=?", (id,))
    r = cur.fetchone()
    if not r: conn.close(); return redirect('/')
    if USE_POSTGRES: s_id, s_cliente, s_placa, s_veiculo, s_carro, s_desc, s_valor, s_data, s_prod = r
    else: s_id=r['id']; s_cliente=r['cliente']; s_placa=r['placa']; s_veiculo=r['veiculo']; s_carro=r['carro']; s_desc=r['descricao']; s_valor=r['valor']; s_data=r['data']; s_prod=r['produtos_usados']
    produtos_existentes = {}
    if s_prod:
        for part in s_prod.split(','):
            part=part.strip()
            if not part: continue
            m = re.match(r'(\d+)x\s+(.+)', part, re.I)
            if m: produtos_existentes[m.group(2).strip().upper()] = int(m.group(1))
            else: produtos_existentes[part.strip().upper()] = 1
    if request.method == 'POST':
        cliente = request.form.get('cliente',''); placa = request.form.get('placa',''); veiculo = request.form.get('veiculo','')
        descricao = request.form.get('descricao',''); valor = request.form.get('valor_total') or 0
        selecionados = request.form.getlist('produtos')
        nomes_usados=[]
        for pid in selecionados:
            try:
                qty = int(request.form.get(f'qty_{pid}', '1') or 1)
                if USE_POSTGRES: cur.execute("SELECT nome FROM produtos WHERE id=%s", (int(pid),))
                else: cur.execute("SELECT nome FROM produtos WHERE id=?", (int(pid),))
                prow = cur.fetchone()
                if prow:
                    nome_p = prow[0] if USE_POSTGRES else prow['nome']
                    nomes_usados.append(f"{qty}x {nome_p}" if qty>1 else nome_p)
            except: pass
        prod_txt = ", ".join(nomes_usados)
        if USE_POSTGRES: cur.execute("UPDATE servicos SET cliente=%s, placa=%s, veiculo=%s, descricao=%s, valor=%s, produtos_usados=%s WHERE id=%s", (cliente, placa, veiculo, descricao, valor, prod_txt, id))
        else: cur.execute("UPDATE servicos SET cliente=?, placa=?, veiculo=?, descricao=?, valor=?, produtos_usados=? WHERE id=?", (cliente, placa, veiculo, descricao, valor, prod_txt, id))
        conn.commit(); conn.close(); return redirect('/historico')
    cur.execute("SELECT * FROM produtos ORDER BY nome ASC")
    produtos_all = cur.fetchall()
    conn.close()
    lista_prod_html=""
    for prod_r in produtos_all:
        pid, nome, preco, est = (prod_r[0], prod_r[1], prod_r[2], prod_r[3]) if USE_POSTGRES else (prod_r['id'], prod_r['nome'], prod_r['preco'], prod_r['estoque'])
        nome_up = nome.strip().upper()
        ja_usado = nome_up in produtos_existentes
        qty_atual = produtos_existentes.get(nome_up, 1)
        selected_class = "selected" if ja_usado else ""
        checked_attr = "checked" if ja_usado else ""
        display_qty = "flex" if ja_usado else "none"
        lista_prod_html += f"""<div class="produto-item {selected_class}" id="item-{pid}" data-preco="{float(preco or 0)}" onclick="toggleProd({pid})"><div><input type="checkbox" name="produtos" value="{pid}" id="chk-{pid}" style="display:none" {checked_attr}><b>{nome}</b><br><span class="small-label">R$ {float(preco or 0):.2f} - Est: {est}</span></div><div style="display:flex; align-items:center; gap:8px;"><div class="qty-box" id="qtybox-{pid}" style="display:{display_qty}" onclick="event.stopPropagation()"><button type="button" class="qty-btn" onclick="changeQty({pid},-1)">-</button><input type="number" id="qty-{pid}" name="qty_{pid}" value="{qty_atual}" min="1" oninput="calcTotal()" onclick="event.stopPropagation()"><button type="button" class="qty-btn" onclick="changeQty({pid},1)">+</button></div><span class="small-label">✓</span></div></div>"""
    html = f"""
    <div class="card-dark p-4">
    <h5 class="fw-bold mb-3">Editar OS #{s_id}</h5>
    <form method="POST">
      <div class="row g-3">
        <div class="col-md-6"><label class="small-label">Cliente</label><input name="cliente" value="{s_cliente}" class="form-control bg-dark text-white border-secondary" required></div>
        <div class="col-md-3"><label class="small-label">Placa</label><input name="placa" value="{s_placa}" class="form-control bg-dark text-white border-secondary"></div>
        <div class="col-md-3"><label class="small-label">Veículo</label><input name="veiculo" value="{s_veiculo or s_carro or ''}" class="form-control bg-dark text-white border-secondary"></div>
        <div class="col-12"><label class="small-label">O que foi feito</label><textarea name="descricao" rows="3" class="form-control bg-dark text-white border-secondary" required>{s_desc}</textarea></div>

        <div class="col-md-6">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <label class="small-label m-0">Total</label>
            <button type="button" id="btnEditar" onclick="toggleEditar()" class="btn btn-sm" style="background:#f7b500;color:#000;font-weight:800;font-size:11px;padding:2px 10px">✏️ Editar</button>
          </div>
          <input id="valor_total" name="valor_total" type="number" step="0.01" value="{s_valor}" class="form-control bg-dark text-white border-secondary" readonly style="border-color:#f7b500!important;font-weight:bold">
          <div id="valor_display" class="small-label mt-1" style="color:#f7b500">R$ {float(s_valor or 0):.2f} - Automático</div>
        </div>

      </div>
      <div class="mt-4"><label class="small-label fw-bold">Produtos usados</label><div class="mt-2" style="max-height:380px;overflow-y:auto">{lista_prod_html}</div></div>
      <button class="btn btn-yellow w-100 py-3 mt-4">SALVAR EDIÇÃO - <span id="valor_display2">R$ {float(s_valor or 0):.2f}</span></button>
      <a href="/historico" class="btn btn-dark2 w-100 mt-2">Cancelar</a>
    </form>
    </div>
    <script>
    let modoManual = false;
    function toggleEditar(){{
      modoManual =!modoManual;
      const input = document.getElementById('valor_total');
      const btn = document.getElementById('btnEditar');
      const disp = document.getElementById('valor_display');
      if(modoManual){{
        input.removeAttribute('readonly');
        input.style.background='#000';
        input.style.borderColor='#22c55e';
        input.style.color='#22c55e';
        input.focus();
        btn.innerText='🔒 Auto';
        btn.style.background='#22c55e';
        disp.innerText='✏️ Editando manualmente - digite o valor que quiser';
        disp.style.color='#22c55e';
      }} else {{
        input.setAttribute('readonly','readonly');
        input.style.borderColor='#f7b500';
        input.style.color='#fff';
        btn.innerText='✏️ Editar';
        btn.style.background='#f7b500';
        calcTotal();
      }}
    }}
    function toggleProd(id){{
      const el=document.getElementById('item-'+id);
      const chk=document.getElementById('chk-'+id);
      const qtybox=document.getElementById('qtybox-'+id);
      el.classList.toggle('selected');
      chk.checked = el.classList.contains('selected');
      qtybox.style.display = chk.checked? 'flex' : 'none';
      calcTotal();
    }}
    function changeQty(id, delta){{
      const inp=document.getElementById('qty-'+id);
      let v=parseInt(inp.value)||1; v+=delta; if(v<1) v=1; inp.value=v; calcTotal();
    }}
    function calcTotal(){{
      if(modoManual) return;
      let t=0;
      document.querySelectorAll('.produto-item.selected').forEach(item=>{{
        const id=item.id.replace('item-','');
        const preco=parseFloat(item.dataset.preco)||0;
        const qty=parseInt(document.getElementById('qty-'+id).value)||1;
        t+=preco*qty;
      }});
      document.getElementById('valor_total').value=t.toFixed(2);
      const vd=document.getElementById('valor_display');
      if(vd) vd.innerText='R$ '+t.toFixed(2)+' - Automático';
      const vd2=document.getElementById('valor_display2');
      if(vd2) vd2.innerText='R$ '+t.toFixed(2);
    }}
    </script>
    """
    return render_template_string(BASE, content=html)

# mantenha suas rotas de produtos, historico, excluir etc iguais
@app.route('/produtos', methods=['GET','POST'])
def produtos():
    init_db()
    conn = get_conn(); cur = conn.cursor()
    if request.method == 'POST' and 'nome' in request.form:
        if USE_POSTGRES: cur.execute("INSERT INTO produtos (nome, preco, estoque) VALUES (%s,%s,%s)", (request.form['nome'], request.form['preco'], request.form['estoque']))
        else: cur.execute("INSERT INTO produtos (nome, preco, estoque) VALUES (?,?,?)", (request.form['nome'], request.form['preco'], request.form['estoque']))
        conn.commit(); conn.close(); return redirect('/produtos')
    cur.execute("SELECT * FROM produtos ORDER BY id DESC"); rows = cur.fetchall(); conn.close()
    linhas="".join([f"<tr><td>{(r[1] if USE_POSTGRES else r['nome'])}</td><td>R$ {float((r[2] if USE_POSTGRES else r['preco']) or 0):.2f}</td><td>{(r[3] if USE_POSTGRES else r['estoque'])}</td><td><a href='/excluir_produto/{(r[0] if USE_POSTGRES else r['id'])}' class='btn btn-sm btn-danger'>X</a></td></tr>" for r in rows])
    html=f"""<div class="card-dark p-4"><h5>Produtos ({len(rows)})</h5><form method="POST" class="row g-2 mb-4"><div class="col-md-5"><input name="nome" class="form-control bg-dark text-white border-secondary" placeholder="Nome" required></div><div class="col-md-3"><input name="preco" type="number" step="0.01" class="form-control bg-dark text-white border-secondary" placeholder="Preço" required></div><div class="col-md-2"><input name="estoque" type="number" class="form-control bg-dark text-white border-secondary" placeholder="Est" required></div><div class="col-md-2"><button class="btn btn-yellow w-100">+ Add</button></div></form><table class="table"><thead><tr><th>Nome</th><th>Preço</th><th>Est</th><th>Ações</th></tr></thead><tbody>{linhas}</tbody></table></div>"""
    return render_template_string(BASE, content=html)

@app.route('/excluir_produto/<int:id>')
def excluir_produto(id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM produtos WHERE id=%s" % ("%s" if USE_POSTGRES else "?"), (id,))
    conn.commit(); conn.close(); return redirect('/produtos')
@app.route('/excluir_servico/<int:id>')
def excluir_servico(id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM servicos WHERE id=%s" % ("%s" if USE_POSTGRES else "?"), (id,))
    conn.commit(); conn.close(); return redirect(request.referrer or '/')
@app.route('/historico')
def historico():
    init_db()
    q = request.args.get('q','')
    servicos = buscar_servicos(q)
    linhas="".join([f"<tr><td>{s['data']}</td><td><b>{s['cliente']}</b></td><td>{s['descricao']}</td><td>R$ {float(s['valor'] or 0):.2f}</td><td><a href='/editar_servico/{s['id']}' class='btn btn-sm btn-dark2'>✏️</a></td></tr>" for s in servicos])
    html=f"""<div class="card-dark p-4"><h5>Histórico</h5><table class="table"><thead><tr><th>Data</th><th>Cliente</th><th>Feito</th><th>Valor</th><th>Ações</th></tr></thead><tbody>{linhas}</tbody></table></div>"""
    return render_template_string(BASE, content=html)
@app.route('/imprimir/<int:id>')
def imprimir(id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM servicos WHERE id=%s" % ("%s" if USE_POSTGRES else "?"), (id,))
    r = cur.fetchone(); conn.close()
    if not r: return "OS não encontrada"
    s = {"id":r[0] if USE_POSTGRES else r['id'], "cliente":r[1] if USE_POSTGRES else r['cliente'], "data":r[7] if USE_POSTGRES else r['data'], "valor":r[6] if USE_POSTGRES else r['valor']}
    return f"<h1>OS #{s['id']} - {s['cliente']} - R$ {s['valor']} - {s['data']}</h1>"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
