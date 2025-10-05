from flask import Flask, render_template, request, jsonify, redirect, session
import mysql.connector
from datetime import datetime, timedelta
import logging

# ---------------- CONFIGURAÇÕES ----------------

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
app.secret_key = "chave-super-secreta"  # troque por algo seguro

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "pequenaflor1",
    "database": "assistentefinanceiro"
}

db = None


def get_db():
    """Cria ou reaproveita a conexão com o banco."""
    global db
    try:
        if db is None or not db.is_connected():
            db = mysql.connector.connect(**DB_CONFIG)
        else:
            db.ping(reconnect=True, attempts=1, delay=0)
    except Exception:
        db = mysql.connector.connect(**DB_CONFIG)
    return db


# ---------------- LOGIN / REGISTRO ----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Tela de login do sistema"""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')

        cursor.execute("SELECT * FROM usuarios WHERE email = %s AND senha = %s", (email, senha))
        user = cursor.fetchone()
        cursor.close()

        if user:
            session['user_id'] = user['id']
            session['nome'] = user['nome']
            return redirect('/')
        else:
            return render_template('login.html', erro="E-mail ou senha incorretos.")

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def registrar():
    """Cria novo usuário"""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')

        # Verifica se já existe usuário com o mesmo e-mail
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        existente = cursor.fetchone()

        if existente:
            return render_template('register.html', erro="E-mail já cadastrado.")

        cursor.execute("INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)", (nome, email, senha))
        conn.commit()
        cursor.close()

        return redirect('/login')

    return render_template('register.html')


@app.route('/logout')
def logout():
    """Finaliza a sessão"""
    session.clear()
    return redirect('/login')


# ---------------- ÁREA LOGADA ----------------

@app.route('/')
def index():
    """Página principal (gráfico e formulário)."""
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('index.html', nome=session.get('nome'))


@app.route('/adicionar', methods=['POST'])
def adicionar():
    """Adiciona novo gasto vinculado ao usuário logado."""
    if 'user_id' not in session:
        return redirect('/login')

    categoria = request.form.get('categoria')
    valor = request.form.get('valor')
    descricao = request.form.get('descricao')

    if not categoria or not valor or not descricao:
        return "Campos incompletos", 400

    try:
        valor_float = float(valor)
    except ValueError:
        return "Valor inválido", 400

    categoria = categoria.strip().lower()
    if categoria in ["uber", "99", "cabify"]:
        categoria = "transporte"
    elif categoria in ["ifood", "delivery"]:
        categoria = "alimentacao"
    elif categoria in ["cinema", "show", "viagem"]:
        categoria = "lazer"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO gastos (user_id, categoria, valor, descricao, data) VALUES (%s, %s, %s, %s, NOW())",
        (session['user_id'], categoria, valor_float, descricao)
    )
    conn.commit()
    cursor.close()

    return redirect('/')


@app.route('/api/gastos-mensais')
def gastos_mensais():
    """Retorna total por categoria dos últimos X meses do usuário logado."""
    if 'user_id' not in session:
        return jsonify({"erro": "Usuário não autenticado"}), 401

    try:
        meses = int(request.args.get('meses', 1))
    except Exception:
        meses = 1

    data_limite = datetime.now() - timedelta(days=meses * 30)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT categoria, SUM(valor) AS total
        FROM gastos
        WHERE user_id = %s AND data >= %s
        GROUP BY categoria
    """, (session['user_id'], data_limite))
    resultados = cursor.fetchall()
    cursor.close()

    total_geral = sum(r["total"] or 0 for r in resultados)
    return jsonify({"categorias": resultados, "total_geral": total_geral})


@app.route('/detalhes')
def detalhes():
    """Página de detalhes com filtros por mês e categoria."""
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    mes = request.args.get("mes", "todos")
    categoria = request.args.get("categoria", "todas")

    meses_portugues = [
        {"mes": 1, "nome_mes": "Janeiro"},
        {"mes": 2, "nome_mes": "Fevereiro"},
        {"mes": 3, "nome_mes": "Março"},
        {"mes": 4, "nome_mes": "Abril"},
        {"mes": 5, "nome_mes": "Maio"},
        {"mes": 6, "nome_mes": "Junho"},
        {"mes": 7, "nome_mes": "Julho"},
        {"mes": 8, "nome_mes": "Agosto"},
        {"mes": 9, "nome_mes": "Setembro"},
        {"mes": 10, "nome_mes": "Outubro"},
        {"mes": 11, "nome_mes": "Novembro"},
        {"mes": 12, "nome_mes": "Dezembro"},
    ]

    cursor.execute("SELECT DISTINCT categoria FROM gastos WHERE user_id = %s ORDER BY categoria", (session['user_id'],))
    categorias = [row["categoria"] for row in cursor.fetchall()]

    query = """
        SELECT descricao, categoria, valor, DATE_FORMAT(data, '%d/%m/%Y') AS data
        FROM gastos
        WHERE user_id = %s
    """
    params = [session['user_id']]

    if mes != "todos":
        query += " AND MONTH(data) = %s"
        params.append(mes)

    if categoria != "todas":
        query += " AND categoria = %s"
        params.append(categoria)

    query += " ORDER BY data DESC"
    cursor.execute(query, tuple(params))
    gastos = cursor.fetchall()
    total = sum(item["valor"] for item in gastos) if gastos else 0

    cursor.close()
    return render_template(
        'detalhes.html',
        gastos=gastos,
        meses=meses_portugues,
        categorias=categorias,
        mes_selecionado=mes,
        categoria_selecionada=categoria,
        total=total
    )


# ---------------- MAIN ----------------

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
