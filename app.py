import os
import io, csv
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, g, Response
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

SQLITE_DB = 'oficina.db'

def get_conn():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    else:
        try:
            conn = getattr(g, '_database', None)
            if conn is None:
                conn = g._database = sqlite3.connect(SQLITE_DB)
                conn.row_factory = sqlite3.Row
            return conn
        except:
            conn = sqlite3.connect(SQLITE_DB)
            conn.row_factory = sqlite3.Row
            return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute('''CREATE TABLE IF NOT EXISTS produtos (id SERIAL PRIMARY KEY, nome TEXT, preco REAL, estoque INTEGER)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS clientes (id SERIAL PRIMARY KEY, nome TEXT, telefone TEXT, carro TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS servicos (id SERIAL PRIMARY KEY, cliente TEXT, descricao TEXT, valor REAL, data TEXT)''')
    else:
        cur.execute('''CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, estoque INTEGER)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT, carro TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS servicos (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, descricao TEXT, valor REAL, data TEXT)''')
    conn.commit()
    if not USE_POSTGRES:
        conn.close()

LAYOUT = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Oficina Pro</title><style>body{font-family:Arial;margin:0;background:#f4f4f4}nav{background:#111;color:#fff;padding:12px;display:flex;gap:15px}nav a{color:#fff;text-decoration:none;font-weight:bold}.container{padding:20px}table{width:100%;border-collapse:collapse;background:#fff}th,td{padding:10px;border:1px solid #ddd}th{background:#111;color:#fff}.btn{padding:6px 10px;border:none;border-radius:4px;cursor:pointer;text-decoration:none;color:#fff;display:inline-block}.btn-edit{background:#2196F3}.btn-del{background:#f44336}.btn-add{background:#4CAF50;padding:10px 15px;margin-bottom:10px}</style></head><body>
<nav><a href="/">Dashboard</a><a href="/produtos">Produtos</a><a href="/clientes">Clientes</a><a href="/servicos">Serviços</a></nav><div class="container">{{content|safe}}</div></body></html>
"""

@app.route('/')
def index():
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM produtos"); total_prod = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM clientes"); total_cli = cur.fetchone()[0]
    if not USE_POSTGRES: conn.close()
    html = f"<h2>Dashboard</h2><p>Total Produtos: {total_prod}</p><p>Total Clientes: {total_cli}</p>"
    return render_template_string(LAYOUT, content=html)

@app.route('/produtos', methods=['GET','POST'])
def produtos():
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    if request.method == 'POST':
        nome = request.form['nome']; preco = request.form['preco']; estoque = request.form['estoque']
        if USE_POSTGRES:
            cur.execute("INSERT INTO produtos (nome, preco, estoque) VALUES (%s,%s,%s)", (nome, preco, estoque))
        else:
            cur.execute("INSERT INTO produtos (nome, preco, estoque) VALUES (?,?,?)", (nome, preco, estoque))
        conn.commit()
        if not USE_POSTGRES: conn.close()
        return redirect('/produtos')
    cur.execute("SELECT * FROM produtos ORDER BY id DESC")
    rows = cur.fetchall()
    if not USE_POSTGRES: conn.close()
    lista = ""
    for r in rows:
        if USE_POSTGRES: id_, nome, preco, estoque = r[0], r[1], r[2], r[3]
        else: id_, nome, preco, estoque = r['id'], r['nome'], r['preco'], r['estoque']
        lista += f"<tr><td>{id_}</td><td>{nome}</td><td>{preco}</td><td>{estoque}</td><td><a class='btn btn-edit' href='/editar_produto/{id_}'>Editar</a> <a class='btn btn-del' href='/excluir_produto/{id_}' onclick=\"return confirm('Tem certeza que quer excluir?')\">Excluir</a></td></tr>"
    html = f"""
    <h2>Produtos</h2>
    <form method="POST" style="background:#fff;padding:15px;margin-bottom:15px"><input name="nome" placeholder="Nome" required> <input name="preco" placeholder="Preço" type="number" step="0.01" required> <input name="estoque" placeholder="Estoque" type="number" required> <button class="btn btn-add">Salvar</button></form>
    <table><tr><th>ID</th><th>Nome</th><th>Preço</th><th>Estoque</th><th>Ações</th></tr>{lista}</table>
    """
    return render_template_string(LAYOUT, content=html)

@app.route('/editar_produto/<int:id>', methods=['GET','POST'])
def editar_produto(id):
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    if request.method == 'POST':
        nome = request.form['nome']; preco = request.form['preco']; estoque = request.form['estoque']
        if USE_POSTGRES:
            cur.execute("UPDATE produtos SET nome=%s, preco=%s, estoque=%s WHERE id=%s", (nome, preco, estoque, id))
        else:
            cur.execute("UPDATE produtos SET nome=?, preco=?, estoque=? WHERE id=?", (nome, preco, estoque, id))
        conn.commit()
        if not USE_POSTGRES: conn.close()
        return redirect('/produtos')
    if USE_POSTGRES:
        cur.execute("SELECT * FROM produtos WHERE id=%s", (id,)); r = cur.fetchone()
        id_, nome, preco, estoque = r[0], r[1], r[2], r[3]
    else:
        cur.execute("SELECT * FROM produtos WHERE id=?", (id,)); r = cur.fetchone()
        id_, nome, preco, estoque = r['id'], r['nome'], r['preco'], r['estoque']
    if not USE_POSTGRES: conn.close()
    html = f"""
    <h2>Editar Produto</h2>
    <form method="POST" style="background:#fff;padding:15px"><input name="nome" value="{nome}" required> <input name="preco" value="{preco}" type="number" step="0.01" required> <input name="estoque" value="{estoque}" type="number" required> <button class="btn btn-add">Salvar</button> <a href="/produtos">Cancelar</a></form>
    """
    return render_template_string(LAYOUT, content=html)

@app.route('/excluir_produto/<int:id>')
def excluir_produto(id):
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("DELETE FROM produtos WHERE id=%s", (id,))
    else:
        cur.execute("DELETE FROM produtos WHERE id=?", (id,))
    conn.commit()
    if not USE_POSTGRES: conn.close()
    return redirect('/produtos')

@app.route('/clientes', methods=['GET','POST'])
def clientes():
    init_db()
    conn = get_conn(); cur = conn.cursor()
    if request.method == 'POST':
        if USE_POSTGRES:
            cur.execute("INSERT INTO clientes (nome, telefone, carro) VALUES (%s,%s,%s)", (request.form['nome'], request.form['telefone'], request.form['carro']))
        else:
            cur.execute("INSERT INTO clientes (nome, telefone, carro) VALUES (?,?,?)", (request.form['nome'], request.form['telefone'], request.form['carro']))
        conn.commit();
        if not USE_POSTGRES: conn.close()
        return redirect('/clientes')
    cur.execute("SELECT * FROM clientes"); rows = cur.fetchall()
    if not USE_POSTGRES: conn.close()
    lista = "".join([f"<tr><td>{r[0] if USE_POSTGRES else r['id']}</td><td>{r[1] if USE_POSTGRES else r['nome']}</td><td>{r[2] if USE_POSTGRES else r['telefone']}</td><td>{r[3] if USE_POSTGRES else r['carro']}</td></tr>" for r in rows])
    html = f"""<h2>Clientes</h2><form method="POST" style="background:#fff;padding:15px;margin-bottom:15px"><input name="nome" placeholder="Nome" required> <input name="telefone" placeholder="Telefone"> <input name="carro" placeholder="Carro"> <button class="btn btn-add">Salvar</button></form><table><tr><th>ID</th><th>Nome</th><th>Telefone</th><th>Carro</th></tr>{lista}</table>"""
    return render_template_string(LAYOUT, content=html)

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
        conn.commit()
        if not USE_POSTGRES: conn.close()
        return redirect('/servicos')
    cur.execute("SELECT * FROM servicos"); rows = cur.fetchall()
    if not USE_POSTGRES: conn.close()
    lista = "".join([f"<tr><td>{r[0] if USE_POSTGRES else r['id']}</td><td>{r[1] if USE_POSTGRES else r['cliente']}</td><td>{r[2] if USE_POSTGRES else r['descricao']}</td><td>{r[3] if USE_POSTGRES else r['valor']}</td><td>{r[4] if USE_POSTGRES else r['data']}</td></tr>" for r in rows])
    html = f"""<h2>Serviços</h2><form method="POST" style="background:#fff;padding:15px;margin-bottom:15px"><input name="cliente" placeholder="Cliente" required> <input name="descricao" placeholder="Serviço" required> <input name="valor" placeholder="Valor" type="number" step="0.01" required> <button class="btn btn-add">Salvar</button></form><table><tr><th>ID</th><th>Cliente</th><th>Descrição</th><th>Valor</th><th>Data</th></tr>{lista}</table>"""
    return render_template_string(LAYOUT, content=html)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
