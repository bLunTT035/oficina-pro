import os
from datetime import datetime
from flask import Flask, render_template_string, request, redirect
import sqlite3

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

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute('CREATE TABLE IF NOT EXISTS produtos (id SERIAL PRIMARY KEY, nome TEXT, preco REAL, estoque INTEGER)')
        cur.execute('CREATE TABLE IF NOT EXISTS servicos (id SERIAL PRIMARY KEY, cliente TEXT, carro TEXT, descricao TEXT, valor REAL, data TEXT, placa TEXT, veiculo TEXT, produtos_usados TEXT)')
        for col in ["cliente","carro","placa","veiculo","descricao","valor","data","produtos_usados"]:
            cur.execute(f'ALTER TABLE servicos ADD COLUMN IF NOT EXISTS {col} TEXT')
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
        # Corrige bagunça antiga
        if not data or "/" not in str(data):
            # Se data não parece data, troca
            data = str(carro or data or "")
            carro = ""
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
</style>
</head><body>
<nav class="navbar d-flex justify-content-between">
<div class="fw-bold">OFICINA PRO - NA NUVEM</div>
<div class="d-flex gap-2">
<a href="/" class="btn btn-dark2 btn-sm">Início</a>
<a href="/produtos" class="btn btn-dark2 btn-sm">Produtos</a>
<a href="/historico" class="btn btn-dark2 btn-sm">Histórico</a>
<a href="/nova_os" class="btn btn-yellow btn-sm">+ Nova OS</a>
</div>
</nav>
<div class="container py-4" style="max-width:950px">{{content|safe}}</div>
<script>
function toggleProd(el){el.classList.toggle('selected');const cb=el.querySelector('input[type=checkbox]');cb.checked=!cb.checked;}
</script>
</body></html>
"""

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
        linhas+=f"<tr><td>{s['data']}</td><td><b>{s['cliente']}</b><br><span class='small-label'>{s['veiculo']} {s['placa']}</span></td><td>{s['descricao']}<br><span class='small-label' style='color:#f7b500'>{s['prod']}</span></td><td><a href='/editar_servico/{s['id']}' class='btn btn-sm btn-dark2'>✏️</a> <a href='/excluir_servico/{s['id']}' class='btn btn-sm btn-danger'>🗑️</a></td></tr>"
    html = f"""
    <div class="row g-3">
      <div class="col-6"><div class="card-dark p-4"><div class="big-number">{total_serv}</div><div class="small-label mt-2">Serviços</div></div></div>
      <div class="col-6"><div class="card-dark p-4"><div class="big-number">R$ {float(faturado):.2f}</div><div class="small-label mt-2">Faturado</div></div></div>
      <div class="col-6"><div class="card-dark p-4"><div class="big-number">{total_prod}</div><div class="small-label mt-2">Produtos</div></div></div>
      <div class="col-6"><div class="card-dark p-4 d-flex align-items-center justify-content-center"><a href="/nova_os" class="btn btn-yellow w-100 py-3">+ REGISTRAR SERVIÇO</a></div></div>
    </div>
    <div class="card-dark p-4 mt-4">
      <h6 class="fw-bold mb-3">Últimos Serviços</h6>
      <table class="table"><thead><tr><th>Data</th><th>Cliente</th><th>Feito</th><th>Ações</th></tr></thead><tbody>{linhas if linhas else '<tr><td colspan=4 class=small-label>Nenhum serviço</td></tr>'}</tbody></table>
    </div>
    """
    return render_template_string(BASE, content=html)

@app.route('/produtos', methods=['GET','POST'])
def produtos():
    init_db()
    conn = get_conn(); cur = conn.cursor()
    if request.method == 'POST':
        if USE_POSTGRES: cur.execute("INSERT INTO produtos (nome, preco, estoque) VALUES (%s,%s,%s)", (request.form['nome'], request.form['preco'], request.form['estoque']))
        else: cur.execute("INSERT INTO produtos (nome, preco, estoque) VALUES (?,?,?)", (request.form['nome'], request.form['preco'], request.form['estoque']))
        conn.commit(); conn.close(); return redirect('/produtos')
    cur.execute("SELECT * FROM produtos ORDER BY id DESC"); rows = cur.fetchall(); conn.close()
    linhas=""
    for r in rows:
        id_, nome, preco, est = (r[0], r[1], r[2], r[3]) if USE_POSTGRES else (r['id'], r['nome'], r['preco'], r['estoque'])
        linhas+=f"<tr><td>{nome}</td><td>R$ {float(preco or 0):.2f}</td><td>{est}</td><td><a href='/excluir_produto/{id_}' class='btn btn-sm btn-danger'>X</a></td></tr>"
    html = f"""
    <div class="card-dark p-4">
    <h5 class="fw-bold mb-3">Produtos</h5>
    <form method="POST" class="row g-2 mb-4">
      <div class="col-md-5"><input name="nome" class="form-control bg-dark text-white border-secondary" placeholder="Nome" required></div>
      <div class="col-md-3"><input name="preco" type="number" step="0.01" class="form-control bg-dark text-white border-secondary" placeholder="Preço" required></div>
      <div class="col-md-2"><input name="estoque" type="number" class="form-control bg-dark text-white border-secondary" placeholder="Est" required></div>
      <div class="col-md-2"><button class="btn btn-yellow w-100">+ Add</button></div>
    </form>
    <table class="table"><thead><tr><th>Nome</th><th>Preço</th><th>Est</th><th></th></tr></thead><tbody>{linhas}</tbody></table>
    </div>
    """
    return render_template_string(BASE, content=html)

@app.route('/excluir_produto/<int:id>')
def excluir_produto(id):
    conn = get_conn(); cur = conn.cursor()
    if USE_POSTGRES: cur.execute("DELETE FROM produtos WHERE id=%s", (id,))
    else: cur.execute("DELETE FROM produtos WHERE id=?", (id,))
    conn.commit(); conn.close(); return redirect('/produtos')

@app.route('/excluir_servico/<int:id>')
def excluir_servico(id):
    conn = get_conn(); cur = conn.cursor()
    if USE_POSTGRES: cur.execute("DELETE FROM servicos WHERE id=%s", (id,))
    else: cur.execute("DELETE FROM servicos WHERE id=?", (id,))
    conn.commit(); conn.close(); return redirect(request.referrer or '/')

@app.route('/nova_os', methods=['GET','POST'])
def nova_os():
    init_db()
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM produtos WHERE estoque > 0 ORDER BY nome ASC"); produtos = cur.fetchall()
    if request.method == 'POST':
        cliente = request.form.get('cliente',''); placa = request.form.get('placa',''); veiculo = request.form.get('veiculo','')
        descricao = request.form.get('descricao',''); valor = request.form.get('valor','0') or 0
        selecionados = request.form.getlist('produtos')
        data = datetime.now().strftime("%d/%m/%Y %H:%M")
        nomes_usados=[]
        for pid in selecionados:
            try:
                if USE_POSTGRES: cur.execute("SELECT nome FROM produtos WHERE id=%s", (int(pid),))
                else: cur.execute("SELECT nome FROM produtos WHERE id=?", (int(pid),))
                prow = cur.fetchone()
                if prow:
                    nome_p = prow[0] if USE_POSTGRES else prow['nome']
                    nomes_usados.append(nome_p)
                    if USE_POSTGRES: cur.execute("UPDATE produtos SET estoque = estoque - 1 WHERE id=%s", (int(pid),))
                    else: cur.execute("UPDATE produtos SET estoque = estoque - 1 WHERE id=?", (int(pid),))
            except: pass
        prod_txt = ", ".join(nomes_usados)
        desc_final = f"{descricao} | Produtos: {prod_txt}" if prod_txt else descricao
        carro_full = f"{veiculo} - {placa}".strip(" -")
        if USE_POSTGRES: cur.execute("INSERT INTO servicos (cliente, carro, placa, veiculo, descricao, valor, data, produtos_usados) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (cliente, carro_full, placa, veiculo, desc_final, valor, data, prod_txt))
        else: cur.execute("INSERT INTO servicos (cliente, placa, veiculo, carro, descricao, valor, data, produtos_usados) VALUES (?,?,?,?,?,?,?,?)", (cliente, placa, veiculo, carro_full, desc_final, valor, data, prod_txt))
        conn.commit(); conn.close(); return redirect('/')
    lista_prod_html=""
    for r in produtos:
        id_, nome, preco, est = (r[0], r[1], r[2], r[3]) if USE_POSTGRES else (r['id'], r['nome'], r['preco'], r['estoque'])
        lista_prod_html += f"""<div class="produto-item" onclick="toggleProd(this)"><div><input type="checkbox" name="produtos" value="{id_}" style="display:none"><b>{nome}</b><br><span class="small-label">R$ {float(preco or 0):.2f} - Est: {est}</span></div><span class="small-label">✓</span></div>"""
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
        <div class="col-md-4"><label class="small-label">Valor R$</label><input name="valor" type="number" step="0.01" class="form-control bg-dark text-white border-secondary"></div>
      </div>
      <div class="mt-4"><label class="small-label fw-bold">Produtos usados</label><div class="mt-2" style="max-height:300px;overflow-y:auto">{lista_prod_html}</div></div>
      <button class="btn btn-yellow w-100 py-2 mt-4">SALVAR SERVIÇO</button>
    </form>
    </div>
    """
    return render_template_string(BASE, content=html)

@app.route('/editar_servico/<int:id>', methods=['GET','POST'])
def editar_servico(id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, cliente, placa, veiculo, carro, descricao, valor, data, produtos_usados FROM servicos WHERE id=%s" % id if USE_POSTGRES and False else "SELECT id, cliente, placa, veiculo, carro, descricao, valor, data, produtos_usados FROM servicos WHERE id=%s" if USE_POSTGRES else "SELECT id, cliente, placa, veiculo, carro, descricao, valor, data, produtos_usados FROM servicos WHERE id=?", (id,) if USE_POSTGRES else (id,))
    if USE_POSTGRES: cur.execute("SELECT id, cliente, placa, veiculo, carro, descricao, valor, data, produtos_usados FROM servicos WHERE id=%s", (id,))
    else: cur.execute("SELECT id, cliente, placa, veiculo, carro, descricao, valor, data, produtos_usados FROM servicos WHERE id=?", (id,))
    r = cur.fetchone()
    if not r: conn.close(); return redirect('/')
    s = {"id":r[0] if USE_POSTGRES else r['id'], "cliente":r[1] if USE_POSTGRES else r['cliente'], "placa":r[2] if USE_POSTGRES else r['placa'], "veiculo":r[3] if USE_POSTGRES else r['veiculo'], "descricao":r[5] if USE_POSTGRES else r['descricao'], "valor":r[6] if USE_POSTGRES else r['valor']}
    if request.method == 'POST':
        if USE_POSTGRES: cur.execute("UPDATE servicos SET cliente=%s, placa=%s, veiculo=%s, descricao=%s, valor=%s WHERE id=%s", (request.form['cliente'], request.form['placa'], request.form['veiculo'], request.form['descricao'], request.form['valor'], id))
        else: cur.execute("UPDATE servicos SET cliente=?, placa=?, veiculo=?, descricao=?, valor=? WHERE id=?", (request.form['cliente'], request.form['placa'], request.form['veiculo'], request.form['descricao'], request.form['valor'], id))
        conn.commit(); conn.close(); return redirect('/historico')
    conn.close()
    html = f"""
    <div class="card-dark p-4">
    <h5 class="fw-bold mb-3">Editar OS #{s['id']}</h5>
    <form method="POST" class="row g-3">
      <div class="col-md-6"><label class="small-label">Cliente</label><input name="cliente" value="{s['cliente']}" class="form-control bg-dark text-white border-secondary" required></div>
      <div class="col-md-3"><label class="small-label">Placa</label><input name="placa" value="{s['placa']}" class="form-control bg-dark text-white border-secondary"></div>
      <div class="col-md-3"><label class="small-label">Veículo</label><input name="veiculo" value="{s['veiculo']}" class="form-control bg-dark text-white border-secondary"></div>
      <div class="col-12"><label class="small-label">O que foi feito</label><textarea name="descricao" rows="3" class="form-control bg-dark text-white border-secondary" required>{s['descricao']}</textarea></div>
      <div class="col-md-4"><label class="small-label">Valor</label><input name="valor" type="number" step="0.01" value="{s['valor']}" class="form-control bg-dark text-white border-secondary"></div>
      <div class="col-12"><button class="btn btn-yellow w-100">SALVAR EDIÇÃO</button></div>
    </form>
    </div>
    """
    return render_template_string(BASE, content=html)

@app.route('/historico')
def historico():
    init_db()
    q = request.args.get('q','')
    servicos = buscar_servicos(q)
    linhas=""
    for s in servicos:
        linhas+=f"<tr><td>{s['data']}</td><td><b>{s['cliente']}</b><br><span class='small-label'>{s['veiculo']} {s['placa']}</span></td><td>{s['descricao']}<br><span class='small-label' style='color:#f7b500'>{s['prod']}</span></td><td>R$ {float(s['valor'] or 0):.2f}</td><td><a href='/editar_servico/{s['id']}' class='btn btn-sm btn-dark2'>✏️</a> <a href='/excluir_servico/{s['id']}' class='btn btn-sm btn-danger'>🗑️</a></td></tr>"
    html = f"""
    <div class="card-dark p-4">
    <h5 class="fw-bold mb-3">Histórico Completo</h5>
    <form method="GET" class="mb-3">
      <div class="input-group"><input name="q" value="{q}" class="form-control bg-dark text-white border-secondary" placeholder="Pesquisar por cliente, placa, veículo ou serviço..."><button class="btn btn-yellow">Buscar</button></div>
    </form>
    <table class="table"><thead><tr><th>Data</th><th>Cliente / Veículo</th><th>Feito / Produtos</th><th>Valor</th><th>Ações</th></tr></thead><tbody>{linhas if linhas else '<tr><td colspan=5 class=small-label>Nenhum resultado</td></tr>'}</tbody></table>
    </div>
    """
    return render_template_string(BASE, content=html)

if __name__ == '__main__':
    app.run(debug=True)
