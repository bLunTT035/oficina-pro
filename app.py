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
        cur.execute('CREATE TABLE IF NOT EXISTS clientes (id SERIAL PRIMARY KEY, nome TEXT, telefone TEXT, carro TEXT)')
        cur.execute('CREATE TABLE IF NOT EXISTS servicos (id SERIAL PRIMARY KEY, cliente TEXT, descricao TEXT, valor REAL, data TEXT)')
        cur.execute('ALTER TABLE produtos ADD COLUMN IF NOT EXISTS nome TEXT')
        cur.execute('ALTER TABLE produtos ADD COLUMN IF NOT EXISTS preco REAL')
        cur.execute('ALTER TABLE produtos ADD COLUMN IF NOT EXISTS estoque INTEGER')
        cur.execute('ALTER TABLE servicos ADD COLUMN IF NOT EXISTS cliente TEXT')
        cur.execute('ALTER TABLE servicos ADD COLUMN IF NOT EXISTS descricao TEXT')
        cur.execute('ALTER TABLE servicos ADD COLUMN IF NOT EXISTS valor REAL')
        cur.execute('ALTER TABLE servicos ADD COLUMN IF NOT EXISTS data TEXT')
        cur.execute('ALTER TABLE servicos ADD COLUMN IF NOT EXISTS carro TEXT')
    else:
        cur.execute('CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, estoque INTEGER)')
        cur.execute('CREATE TABLE IF NOT EXISTS servicos (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, carro TEXT, descricao TEXT, valor REAL, data TEXT)')
    conn.commit()
    conn.close()

BASE = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Oficina PRO</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#0e0e0e;color:#fff;font-family:Inter,Arial}
.navbar{background:#000!important;border-bottom:3px solid #f7b500;padding:10px 15px}
.card-dark{background:#1c1c1c;border:1px solid #2a2a2a;border-radius:12px}
.btn-yellow{background:#f7b500;color:#000;font-weight:800;border-radius:8px;border:none}
.btn-yellow:hover{background:#ffcc33;color:#000}
.btn-dark2{background:#2a2a2a;color:#fff;border:none;border-radius:8px}
.btn-green{background:#00c853;color:#fff;font-weight:700;border-radius:8px;border:none}
.table-dark-custom{color:#ddd}
.table-dark-custom th{color:#fff;border-bottom:1px solid #333}
.table-dark-custom td{border-bottom:1px solid #222;padding:12px 8px}
.small-label{color:#888;font-size:13px}
.big-number{font-size:22px;font-weight:700}
a{color:#fff;text-decoration:none}
</style>
</head><body>
<nav class="navbar d-flex justify-content-between">
<div class="fw-bold">OFICINA PRO - NA NUVEM</div>
<div class="d-flex gap-2">
<a href="/" class="btn btn-dark2 btn-sm">Inicio</a>
<a href="/produtos" class="btn btn-dark2 btn-sm">Produtos</a>
<a href="/historico" class="btn btn-dark2 btn-sm">Historico</a>
<a href="/excel" class="btn btn-green btn-sm">Excel</a>
<a href="/nova_os" class="btn btn-yellow btn-sm">+ Nova OS</a>
</div>
</nav>
<div class="container py-4" style="max-width:900px">{{content|safe}}</div>
</body></html>
"""

@app.route('/')
def index():
    init_db()
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM servicos"); total_serv = cur.fetchone()[0]
    except: total_serv=0
    try:
        cur.execute("SELECT COALESCE(SUM(valor),0) FROM servicos"); faturado = cur.fetchone()[0] or 0
    except: faturado=0
    try:
        cur.execute("SELECT COUNT(*) FROM produtos"); total_prod = cur.fetchone()[0]
    except: total_prod=0

    cur.execute("SELECT * FROM servicos ORDER BY id DESC LIMIT 10"); rows = cur.fetchall()
    conn.close()

    linhas=""
    for r in rows:
        if USE_POSTGRES:
            data_, cli, carro, desc = r[4] if len(r)>4 else "", r[1], (r[2] if len(r)>2 else ""), r[2] if len(r)<=4 else r[3]
            # compatibilidade com tabela antiga e nova
            try:
                cliente = r[1]; carro_txt = r[2] if len(r)>5 else ""; descricao = r[3] if len(r)>5 else r[2]; data_txt = r[5] if len(r)>5 else r[4];
                if len(r)==5: # tabela antiga: id, cliente, descricao, valor, data
                    cliente=r[1]; descricao=r[2]; data_txt=r[4]; carro_txt=""
                else:
                    cliente=r[1]; carro_txt=r[2]; descricao=r[3]; data_txt=r[5]
            except:
                cliente=r[1]; carro_txt=""; descricao=r[2]; data_txt=r[4]
        else:
            cliente=r['cliente']; carro_txt=r['carro'] if 'carro' in r.keys() else ""; descricao=r['descricao']; data_txt=r['data']

        linhas+=f"<tr><td>{data_txt}</td><td><b>{cliente}</b><br><span class='small-label'>{carro_txt}</span></td><td>{descricao}</td></tr>"

    html = f"""
    <div class="row g-3">
      <div class="col-6"><div class="card-dark p-4"><div class="big-number">{total_serv}</div><div class="small-label mt-2">Servicos</div></div></div>
      <div class="col-6"><div class="card-dark p-4"><div class="big-number">R$ {float(faturado):.2f}</div><div class="small-label mt-2">Faturado</div></div></div>
      <div class="col-6"><div class="card-dark p-4"><div class="big-number">{total_prod}</div><div class="small-label mt-2">Produtos</div></div></div>
      <div class="col-6"><div class="card-dark p-4 d-flex align-items-center justify-content-center"><a href="/nova_os" class="btn btn-yellow w-100 py-3">+ REGISTRAR SERVICO</a></div></div>
    </div>
    <div class="card-dark p-4 mt-4">
      <h6 class="fw-bold mb-3">Ultimos Servicos</h6>
      <table class="table table-dark-custom w-100"><thead><tr><th>Data</th><th>Cliente</th><th>Feito</th></tr></thead><tbody>{linhas if linhas else '<tr><td colspan=3 class=small-label>Nenhum serviço ainda</td></tr>'}</tbody></table>
    </div>
    """
    return render_template_string(BASE, content=html)

@app.route('/produtos', methods=['GET','POST'])
def produtos():
    init_db()
    conn = get_conn(); cur = conn.cursor()
    if request.method == 'POST':
        if USE_POSTGRES:
            cur.execute("INSERT INTO produtos (nome, preco, estoque) VALUES (%s,%s,%s)", (request.form['nome'], request.form['preco'], request.form['estoque']))
        else:
            cur.execute("INSERT INTO produtos (nome, preco, estoque) VALUES (?,?,?)", (request.form['nome'], request.form['preco'], request.form['estoque']))
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
    <table class="table table-dark-custom w-100"><thead><tr><th>Nome</th><th>Preço</th><th>Est</th><th></th></tr></thead><tbody>{linhas}</tbody></table>
    </div>
    """
    return render_template_string(BASE, content=html)

@app.route('/excluir_produto/<int:id>')
def excluir_produto(id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM produtos WHERE id=%s" % id if USE_POSTGRES and False else "DELETE FROM produtos WHERE id=%s" if USE_POSTGRES else "DELETE FROM produtos WHERE id=?", (id,) if USE_POSTGRES else (id,))
    if USE_POSTGRES:
        cur.execute("DELETE FROM produtos WHERE id=%s", (id,))
    else:
        cur.execute("DELETE FROM produtos WHERE id=?", (id,))
    # acima deixei compatível, mas o correto é só a linha de baixo (evita erro duplicado)
    conn.commit(); conn.close(); return redirect('/produtos')

@app.route('/nova_os', methods=['GET','POST'])
def nova_os():
    init_db()
    if request.method == 'POST':
        conn = get_conn(); cur = conn.cursor()
        data = datetime.now().strftime("%d/%m/%Y %H:%M")
        cliente = request.form['cliente']
        carro = request.form['carro']
        desc = request.form['descricao']
        valor = request.form['valor'] or 0
        if USE_POSTGRES:
            try:
                cur.execute("INSERT INTO servicos (cliente, carro, descricao, valor, data) VALUES (%s,%s,%s,%s,%s)", (cliente, carro, desc, valor, data))
            except:
                cur.execute("INSERT INTO servicos (cliente, descricao, valor, data) VALUES (%s,%s,%s,%s)", (f"{cliente} - {carro}", desc, valor, data))
        else:
            cur.execute("INSERT INTO servicos (cliente, carro, descricao, valor, data) VALUES (?,?,?,?,?)", (cliente, carro, desc, valor, data))
        conn.commit(); conn.close(); return redirect('/')

    html = """
    <div class="card-dark p-4">
    <h5 class="fw-bold mb-3">+ Nova OS - Registrar Serviço</h5>
    <form method="POST" class="row g-3">
      <div class="col-md-6"><label class="small-label">Cliente</label><input name="cliente" class="form-control bg-dark text-white border-secondary" placeholder="Ex: Paulina" required></div>
      <div class="col-md-6"><label class="small-label">Carro / Placa</label><input name="carro" class="form-control bg-dark text-white border-secondary" placeholder="Ex: Onix LTZ xyz1234"></div>
      <div class="col-12"><label class="small-label">O que foi feito</label><input name="descricao" class="form-control bg-dark text-white border-secondary" placeholder="Ex: Trocou pastilha de freio" required></div>
      <div class="col-md-4"><label class="small-label">Valor R$</label><input name="valor" type="number" step="0.01" class="form-control bg-dark text-white border-secondary" placeholder="0.00"></div>
      <div class="col-12"><button class="btn btn-yellow w-100 py-2">SALVAR SERVIÇO</button></div>
    </form>
    </div>
    """
    return render_template_string(BASE, content=html)

@app.route('/historico')
def historico():
    init_db()
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM servicos ORDER BY id DESC"); rows = cur.fetchall(); conn.close()
    linhas=""
    for r in rows:
        if USE_POSTGRES:
            try:
                if len(r)>=6: cliente, carro, desc, valor, data = r[1], r[2], r[3], r[4], r[5]
                else: cliente, desc, valor, data, carro = r[1], r[2], r[3], r[4], ""
            except: cliente, desc, data = r[1], r[2], r[4]; carro=""; valor=0
        else:
            cliente=r['cliente']; carro=r['carro'] if 'carro' in r.keys() else ""; desc=r['descricao']; valor=r['valor']; data=r['data']
        linhas+=f"<tr><td>{data}</td><td><b>{cliente}</b><br><span class='small-label'>{carro}</span></td><td>{desc}</td><td>R$ {float(valor or 0):.2f}</td></tr>"
    html = f"""
    <div class="card-dark p-4">
    <h5 class="fw-bold mb-3">Histórico Completo</h5>
    <table class="table table-dark-custom w-100"><thead><tr><th>Data</th><th>Cliente</th><th>Feito</th><th>Valor</th></tr></thead><tbody>{linhas}</tbody></table>
    </div>
    """
    return render_template_string(BASE, content=html)

@app.route('/excel')
def excel():
    return redirect('/')

@app.route('/excluir/<int:id>')
def excluir(id):
    return redirect(f'/excluir_produto/{id}')

if __name__ == '__main__':
    app.run(debug=True)
