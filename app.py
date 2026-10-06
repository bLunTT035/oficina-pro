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
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    else:
        conn = sqlite3.connect(SQLITE_DB)
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("CREATE TABLE IF NOT EXISTS produtos (id SERIAL PRIMARY KEY, nome TEXT, preco REAL, estoque INT)")
        cur.execute("CREATE TABLE IF NOT EXISTS servicos (id SERIAL PRIMARY KEY, data TEXT, cliente TEXT, telefone TEXT, moto TEXT, placa TEXT, km TEXT, mecanico TEXT, descricao_servico TEXT, pecas_usadas TEXT, valor_total REAL, forma_pagamento TEXT)")
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY, nome TEXT, preco REAL, estoque INTEGER)")
        cur.execute("CREATE TABLE IF NOT EXISTS servicos (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, cliente TEXT, telefone TEXT, moto TEXT, placa TEXT, km TEXT, mecanico TEXT, descricao_servico TEXT, pecas_usadas TEXT, valor_total REAL, forma_pagamento TEXT)")
    conn.commit()
    cur.close()
    conn.close()

TEMPLATE = """<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Oficina PRO</title><style>body{font-family:Arial;background:#0f0f0f;color:#eee;margin:0}header{background:#111;padding:15px;display:flex;justify-content:space-between;flex-wrap:wrap;border-bottom:3px solid #f5b400}header a{color:#fff;text-decoration:none;margin:4px;background:#222;padding:8px 12px;border-radius:6px}.container{padding:15px;max-width:1100px;margin:auto}.card{background:#1e1e1e;padding:20px;border-radius:12px;margin-bottom:20px;border:1px solid #333}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #333;text-align:left}.btn{background:#f5b400;color:#000;padding:10px 15px;border:none;border-radius:8px;font-weight:bold;cursor:pointer;text-decoration:none;display:inline-block}.btn-green{background:#27ae60;color:#fff}.btn-blue{background:#2980b9;color:#fff}input,textarea,select{width:100%;padding:11px;margin:6px 0 14px 0;border:1px solid #444;border-radius:8px;background:#111;color:#fff;box-sizing:border-box}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style></head><body><header><div><b>OFICINA PRO - NA NUVEM</b></div><div><a href='/'>Inicio</a><a href='/produtos'>Produtos</a><a href='/historico'>Historico</a><a href='/exportar' style='background:#27ae60'>Excel</a><a href='/nova_os' style='background:#f5b400;color:#000'>+ Nova OS</a></div></header><div class='container'>{{content|safe}}</div></body></html>"""

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def fetch_all(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute(query.replace('?', '%s'), params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        result = [dict(zip(cols, r)) for r in rows]
        cur.close()
        conn.close()
        return result
    else:
        cur.execute(query, params)
        rows = cur.fetchall()
        return rows

def fetch_one(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute(query.replace('?', '%s'), params)
        r = cur.fetchone()
        if not r:
            cur.close(); conn.close(); return None
        cols = [d[0] for d in cur.description]
        cur.close(); conn.close()
        return dict(zip(cols, r))
    else:
        cur.execute(query, params)
        return cur.fetchone()

def exec_query(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute(query.replace('?', '%s'), params)
        conn.commit()
        cur.close()
        conn.close()
    else:
        cur.execute(query, params)
        conn.commit()

@app.route('/')
def index():
    total_os = fetch_one('SELECT COUNT(*) as c FROM servicos')
    total_os = total_os['c'] if isinstance(total_os, dict) else (total_os[0] if total_os else 0)
    total_prod = fetch_one('SELECT COUNT(*) as c FROM produtos')
    total_prod = total_prod['c'] if isinstance(total_prod, dict) else (total_prod[0] if total_prod else 0)
    total_valor_row = fetch_one('SELECT SUM(valor_total) as s FROM servicos')
    if isinstance(total_valor_row, dict):
        total_valor = total_valor_row['s'] or 0
    else:
        total_valor = total_valor_row[0] if total_valor_row and total_valor_row[0] else 0
    ultimos = fetch_all('SELECT * FROM servicos ORDER BY id DESC LIMIT 5')
    html = f"<div class='grid'><div class='card'><h2>{total_os}</h2>Servicos</div><div class='card'><h2>R$ {float(total_valor):.2f}</h2>Faturado</div><div class='card'><h2>{total_prod}</h2>Produtos</div><div class='card'><a href='/nova_os' class='btn' style='width:100%;text-align:center;padding:18px'>+ REGISTRAR SERVICO</a></div></div><div class='card'><h3>Ultimos Servicos</h3><table><tr><th>Data</th><th>Cliente</th><th>Feito</th></tr>"
    for s in ultimos:
        if isinstance(s, dict):
            html += f"<tr><td>{s['data']}</td><td><b>{s['cliente']}</b><br>{s['moto']} {s.get('placa','')}</td><td>{s['descricao_servico'][:70]}</td></tr>"
        else:
            html += f"<tr><td>{s['data']}</td><td><b>{s['cliente']}</b><br>{s['moto']} {s['placa'] or ''}</td><td>{s['descricao_servico'][:70]}</td></tr>"
    html += "</table></div>"
    return render_template_string(TEMPLATE, content=html)

@app.route('/produtos', methods=['GET','POST'])
def produtos():
    if request.method == 'POST':
        exec_query('INSERT INTO produtos (nome, preco, estoque) VALUES (?,?,?)', (request.form['nome'], float(request.form['preco']), int(request.form['estoque'])))
        return redirect('/produtos')
    prods = fetch_all('SELECT * FROM produtos ORDER BY nome')
    html = "<div class='card'><h2>Nova Peca</h2><form method='post' class='grid'><div><input name='nome' placeholder='Nome' required></div><div><input name='preco' type='number' step='0.01' placeholder='Preco' required></div><div><input name='estoque' type='number' placeholder='Estoque' required></div><div><button class='btn'>Salvar</button></div></form></div><div class='card'><h2>Estoque</h2><table><tr><th>Peca</th><th>Preco</th><th>Est</th></tr>"
    for p in prods:
        if isinstance(p, dict):
            html += f"<tr><td>{p['nome']}</td><td>R$ {float(p['preco']):.2f}</td><td>{p['estoque']}</td></tr>"
        else:
            html += f"<tr><td>{p['nome']}</td><td>R$ {p['preco']:.2f}</td><td>{p['estoque']}</td></tr>"
    html += "</table></div>"
    return render_template_string(TEMPLATE, content=html)

@app.route('/nova_os', methods=['GET','POST'])
def nova_os():
    produtos = fetch_all('SELECT * FROM produtos')
    if request.method == 'POST':
        pecas = ", ".join(request.form.getlist('pecas'))
        exec_query('INSERT INTO servicos (data, cliente, telefone, moto, placa, km, mecanico, descricao_servico, pecas_usadas, valor_total, forma_pagamento) VALUES (?,?,?,?,?,?,?,?,?,?,?)', (datetime.now().strftime('%d/%m/%Y %H:%M'), request.form['cliente'], request.form['telefone'], request.form['moto'], request.form['placa'], request.form['km'], request.form['mecanico'], request.form['descricao'], pecas, float(request.form['valor'] or 0), request.form['pagamento']))
        return redirect('/historico')
    opts = ""
    for p in produtos:
        nome = p['nome'] if isinstance(p, dict) else p['nome']
        preco = p['preco'] if isinstance(p, dict) else p['preco']
        opts += f"<label style='display:flex;gap:8px;background:#111;padding:10px;border-radius:8px;border:1px solid #333;margin-bottom:6px'><input type='checkbox' name='pecas' value='{nome}' style='width:18px'> {nome} R${float(preco):.2f}</label>"
    html = f"<div class='card'><h2>Registrar Servico</h2><form method='post'><div class='grid'><div><label>Cliente*</label><input name='cliente' required></div><div><label>Telefone</label><input name='telefone'></div><div><label>Moto / Cor*</label><input name='moto' required></div><div><label>Placa</label><input name='placa'></div><div><label>KM</label><input name='km'></div><div><label>Mecanico</label><input name='mecanico'></div></div><label>Descricao*</label><textarea name='descricao' rows='4' required></textarea><label>Pecas</label><div style='max-height:180px;overflow-y:auto;margin-bottom:12px'>{opts if opts else 'Nenhuma peca'}</div><div class='grid'><div><label>Valor R$</label><input name='valor' type='number' step='0.01'></div><div><label>Pagamento</label><select name='pagamento'><option>Dinheiro</option><option>Pix</option><option>Cartao</option><option>Prazo</option></select></div></div><button class='btn btn-green' style='width:100%;font-size:18px;padding:14px'>SALVAR NO HISTORICO</button></form></div>"
    return render_template_string(TEMPLATE, content=html)

@app.route('/historico')
def historico():
    q = request.args.get('q','')
    if q:
        servs = fetch_all("SELECT * FROM servicos WHERE cliente LIKE? OR placa LIKE? OR moto LIKE? ORDER BY id DESC", (f'%{q}%',f'%{q}%',f'%{q}%'))
    else:
        servs = fetch_all('SELECT * FROM servicos ORDER BY id DESC')
    html = f"<div class='card'><h2>Historico</h2><form method='get' style='display:flex;gap:8px'><input name='q' value='{q}' placeholder='Buscar Rafael, placa...' style='flex:1'><button class='btn btn-blue'>Buscar</button></form></div><div class='card'><table><tr><th>Data</th><th>Cliente</th><th>Servico</th><th>Valor</th></tr>"
    for s in servs:
        if isinstance(s, dict):
            html += f"<tr><td>{s['data']}</td><td><b>{s['cliente']}</b><br>{s['moto']} <b style='color:#f5b400'>{s.get('placa','')}</b></td><td>{s['descricao_servico']}<br><small>Pecas: {s.get('pecas_usadas','')}</small></td><td>R$ {float(s.get('valor_total') or 0):.2f}</td></tr>"
        else:
            html += f"<tr><td>{s['data']}</td><td><b>{s['cliente']}</b><br>{s['moto']} <b style='color:#f5b400'>{s['placa'] or ''}</b></td><td>{s['descricao_servico']}</td><td>R$ {s['valor_total'] or 0:.2f}</td></tr>"
    html += "</table></div>"
    return render_template_string(TEMPLATE, content=html)

@app.route('/exportar')
def exportar():
    servs = fetch_all('SELECT * FROM servicos ORDER BY id DESC')
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Data','Cliente','Telefone','Moto','Placa','KM','Mecanico','Servico','Pecas','Valor','Pagamento'])
    for s in servs:
        if isinstance(s, dict):
            cw.writerow([s['data'],s['cliente'],s['telefone'],s['moto'],s['placa'],s['km'],s['mecanico'],s['descricao_servico'],s['pecas_usadas'],s['valor_total'],s['forma_pagamento']])
        else:
            cw.writerow([s['data'],s['cliente'],s['telefone'],s['moto'],s['placa'],s['km'],s['mecanico'],s['descricao_servico'],s['pecas_usadas'],s['valor_total'],s['forma_pagamento']])
    return Response(si.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=historico.csv"})

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
