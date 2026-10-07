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
        # Cria se não existir
        cur.execute('CREATE TABLE IF NOT EXISTS produtos (id SERIAL PRIMARY KEY, nome TEXT, preco REAL, estoque INTEGER)')
        cur.execute('CREATE TABLE IF NOT EXISTS clientes (id SERIAL PRIMARY KEY, nome TEXT, telefone TEXT, carro TEXT)')
        cur.execute('CREATE TABLE IF NOT EXISTS servicos (id SERIAL PRIMARY KEY, cliente TEXT, descricao TEXT, valor REAL, data TEXT)')
        # ARRUMA colunas que faltam (esse é o conserto)
        cur.execute('ALTER TABLE produtos ADD COLUMN IF NOT EXISTS nome TEXT')
        cur.execute('ALTER TABLE produtos ADD COLUMN IF NOT EXISTS preco REAL')
        cur.execute('ALTER TABLE produtos ADD COLUMN IF NOT EXISTS estoque INTEGER')
        cur.execute('ALTER TABLE clientes ADD COLUMN IF NOT EXISTS nome TEXT')
        cur.execute('ALTER TABLE clientes ADD COLUMN IF NOT EXISTS telefone TEXT')
        cur.execute('ALTER TABLE clientes ADD COLUMN IF NOT EXISTS carro TEXT')
        cur.execute('ALTER TABLE servicos ADD COLUMN IF NOT EXISTS cliente TEXT')
        cur.execute('ALTER TABLE servicos ADD COLUMN IF NOT EXISTS descricao TEXT')
        cur.execute('ALTER TABLE servicos ADD COLUMN IF NOT EXISTS valor REAL')
        cur.execute('ALTER TABLE servicos ADD COLUMN IF NOT EXISTS data TEXT')
    else:
        cur.execute('CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, estoque INTEGER)')
        cur.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT, carro TEXT)')
        cur.execute('CREATE TABLE IF NOT EXISTS servicos (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, descricao TEXT, valor REAL, data TEXT)')
    conn.commit()
    conn.close()

BASE = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Oficina Pro</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#f0f2f5}.navbar{background:#0d1b2a!important}.card{border:none;border-radius:15px;box-shadow:0 4px 15px rgba(0,0,0,.1)}.table thead{background:#0d1b2a;color:#fff}</style>
</head><body>
<nav class="navbar navbar-dark navbar-expand-lg px-3">
<a class="navbar-brand fw-bold" href="/">🔧 Oficina Pro</a>
<div class="navbar-nav flex-row gap-3 ms-3">
<a class="nav-link text-white" href="/">Dashboard</a>
<a class="nav-link text-white" href="/produtos">Produtos</a>
<a class="nav-link text-white" href="/clientes">Clientes</a>
<a class="nav-link text-white" href="/servicos">Serviços</a>
</div></nav>
<div class="container py-4">{{content|safe}}</div></body></html>
"""

@app.route('/')
def index():
    init_db()
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM produtos"); p = cur.fetchone()[0]
    except: p=0
    try:
        cur.execute("SELECT COUNT(*) FROM clientes"); c = cur.fetchone()[0]
    except: c=0
    try:
        cur.execute("SELECT COALESCE(SUM(valor),0) FROM servicos"); s = cur.fetchone()[0]
    except: s=0
    conn.close()
    html = f"""<div class="row g-3"><div class="col-md-4"><div class="card p-4"><h5>Total Produtos</h5><h2>{p}</h2></div></div><div class="col-md-4"><div class="card p-4"><h5>Total Clientes</h5><h2>{c}</h2></div></div><div class="col-md-4"><div class="card p-4"><h5>Total Serviços R$</h5><h2>{float(s or 0):.2f}</h2></div></div></div>"""
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
        linhas+=f"<tr><td>{id_}</td><td>{nome}</td><td>R$ {float(preco or 0):.2f}</td><td>{est}</td><td><a href='/editar_produto/{id_}' class='btn btn-sm btn-primary'>Editar</a> <a href='/excluir_produto/{id_}' class='btn btn-sm btn-danger' onclick=\"return confirm('Excluir?')\">Excluir</a></td></tr>"
    form='<form method="POST" class="row g-2"><div class="col-md-4"><input name="nome" class="form-control" placeholder="Nome do produto" required></div><div class="col-md-3"><input name="preco" type="number" step="0.01" class="form-control" placeholder="Preço" required></div><div class="col-md-3"><input name="estoque" type="number" class="form-control" placeholder="Estoque" required></div><div class="col-md-2"><button class="btn btn-primary w-100">+ Adicionar</button></div></form>'
    html = f"""<h3 class="mb-3">📦 Produtos</h3><div class="card p-3 mb-3">{form}</div><div class="card p-3"><table class="table table-hover"><thead><tr><th>ID</th><th>Nome</th><th>Preço</th><th>Estoque</th><th>Ações</th></tr></thead><tbody>{linhas}</tbody></table></div>"""
    return render_template_string(BASE, content=html)

@app.route('/editar_produto/<int:id>', methods=['GET','POST'])
def editar_produto(id):
    conn = get_conn(); cur = conn.cursor()
    if request.method == 'POST':
        if USE_POSTGRES:
            cur.execute("UPDATE produtos SET nome=%s, preco=%s, estoque=%s WHERE id=%s", (request.form['nome'], request.form['preco'], request.form['estoque'], id))
        else:
            cur.execute("UPDATE produtos SET nome=?, preco=?, estoque=? WHERE id=?", (request.form['nome'], request.form['preco'], request.form['estoque'], id))
        conn.commit(); conn.close(); return redirect('/produtos')
    if USE_POSTGRES:
        cur.execute("SELECT * FROM produtos WHERE id=%s", (id,)); r=cur.fetchone(); id_, nome, preco, est = r[0], r[1], r[2], r[3]
    else:
        cur.execute("SELECT * FROM produtos WHERE id=?", (id,)); r=cur.fetchone(); id_, nome, preco, est = r['id'], r['nome'], r['preco'], r['estoque']
    conn.close()
    html = f"""<h3>Editar Produto</h3><div class="card p-4"><form method="POST" class="row g-3"><div class="col-md-6"><label>Nome</label><input name="nome" value="{nome}" class="form-control" required></div><div class="col-md-3"><label>Preço</label><input name="preco" value="{preco}" type="number" step="0.01" class="form-control" required></div><div class="col-md-3"><label>Estoque</label><input name="estoque" value="{est}" type="number" class="form-control" required></div><div class="col-12"><button class="btn btn-primary">Salvar</button> <a href="/produtos" class="btn btn-secondary">Cancelar</a></div></form></div>"""
    return render_template_string(BASE, content=html)

@app.route('/excluir_produto/<int:id>')
def excluir_produto(id):
    conn = get_conn(); cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("DELETE FROM produtos WHERE id=%s", (id,))
    else:
        cur.execute("DELETE FROM produtos WHERE id=?", (id,))
    conn.commit(); conn.close(); return redirect('/produtos')

@app.route('/clientes', methods=['GET','POST'])
def clientes():
    init_db()
    conn = get_conn(); cur = conn.cursor()
    if request.method == 'POST':
        if USE_POSTGRES:
            cur.execute("INSERT INTO clientes (nome, telefone, carro) VALUES (%s,%s,%s)", (request.form['nome'], request.form['telefone'], request.form['carro']))
        else:
            cur.execute("INSERT INTO clientes (nome, telefone, carro) VALUES (?,?,?)", (request.form['nome'], request.form['telefone'], request.form['carro']))
        conn.commit(); conn.close(); return redirect('/clientes')
    cur.execute("SELECT * FROM clientes ORDER BY id DESC"); rows = cur.fetchall(); conn.close()
    linhas="";
    for r in rows:
        id_, n, t, ca = (r[0], r[1], r[2], r[3]) if USE_POSTGRES else (r['id'], r['nome'], r['telefone'], r['carro'])
        linhas+=f"<tr><td>{id_}</td><td>{n}</td><td>{t}</td><td>{ca}</td></tr>"
    form='<form method="POST" class="row g-2"><div class="col-md-4"><input name="nome" class="form-control" placeholder="Nome" required></div><div class="col-md-3"><input name="telefone" class="form-control" placeholder="Telefone"></div><div class="col-md-3"><input name="carro" class="form-control" placeholder="Carro"></div><div class="col-md-2"><button class="btn btn-primary w-100">+ Salvar</button></div></form>'
    html = f"""<h3 class="mb-3">👥 Clientes</h3><div class="card p-3 mb-3">{form}</div><div class="card p-3"><table class="table"><thead><tr><th>ID</th><th>Nome</th><th>Telefone</th><th>Carro</th></tr></thead><tbody>{linhas}</tbody></table></div>"""
    return render_template_string(BASE, content=html)

@app.route('/servicos', methods=['GET','POST'])
def servicos():
    init_db()
    conn = get_conn(); cur = conn.cursor()
    if request.method == 'POST':
        data = datetime.now().strftime("%d/%m/%Y")
        if USE_POSTGRES:
            cur.execute("INSERT INTO servicos (cliente, descricao, valor, data) VALUES (%s,%s,%s,%s)", (request.form['cliente'], request.form['descricao'], request.form['valor'], data))
        else:
            cur.execute("INSERT INTO servicos (cliente, descricao, valor, data) VALUES (?,?,?,?)", (request.form['cliente'], request.form['descricao'], request.form['valor'], data))
        conn.commit(); conn.close(); return redirect('/servicos')
    cur.execute("SELECT * FROM servicos ORDER BY id DESC"); rows = cur.fetchall(); conn.close()
    linhas="";
    for r in rows:
        id_, cli, desc, val, dat = (r[0], r[1], r[2], r[3], r[4]) if USE_POSTGRES else (r['id'], r['cliente'], r['descricao'], r['valor'], r['data'])
        linhas+=f"<tr><td>{id_}</td><td>{cli}</td><td>{desc}</td><td>R$ {float(val or 0):.2f}</td><td>{dat}</td></tr>"
    form='<form method="POST" class="row g-2"><div class="col-md-3"><input name="cliente" class="form-control" placeholder="Cliente" required></div><div class="col-md-4"><input name="descricao" class="form-control" placeholder="Serviço" required></div><div class="col-md-3"><input name="valor" type="number" step="0.01" class="form-control" placeholder="Valor" required></div><div class="col-md-2"><button class="btn btn-primary w-100">+ Lançar</button></div></form>'
    html = f"""<h3 class="mb-3">🛠️ Serviços</h3><div class="card p-3 mb-3">{form}</div><div class="card p-3"><table class="table"><thead><tr><th>ID</th><th>Cliente</th><th>Descrição</th><th>Valor</th><th>Data</th></tr></thead><tbody>{linhas}</tbody></table></div>"""
    return render_template_string(BASE, content=html)

if __name__ == '__main__':
    app.run(debug=True)
